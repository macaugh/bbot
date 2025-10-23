from baddns.base import get_all_modules
from baddns.lib.loader import load_signatures
from .base import BaseModule

import asyncio
import logging


class baddns(BaseModule):
    watched_events = ["DNS_NAME", "DNS_NAME_UNRESOLVED"]
    produced_events = ["FINDING", "VULNERABILITY"]
    flags = ["active", "safe", "web-basic", "baddns", "cloud-enum", "subdomain-hijack"]
    meta = {
        "description": "Check hosts for domain/subdomain takeovers",
        "created_date": "2024-01-18",
        "author": "@liquidsec",
    }
    options = {
        "custom_nameservers": [],
        "only_high_confidence": False,
        "enabled_submodules": [],
        "filter_non_vulnerable": True,
    }
    options_desc = {
        "custom_nameservers": "Force BadDNS to use a list of custom nameservers",
        "only_high_confidence": "Do not emit low-confidence or generic detections",
        "enabled_submodules": "A list of submodules to enable. Empty list (default) enables CNAME, TXT and MX Only",
        "filter_non_vulnerable": "Filter out known non-vulnerable/parking services to reduce false positives",
    }

    # Services known to NOT be vulnerable to subdomain takeover
    # Based on research from https://github.com/EdOverflow/can-i-take-over-xyz
    NON_VULNERABLE_SERVICES = {
        # Service name patterns (case-insensitive)
        "signatures": [
            "AWS_ELB",  # AWS Elastic Load Balancer
            "AWS_ELB_TAKEOVER",
            "CLOUDFRONT",  # AWS CloudFront
            "CLOUDFRONT_TAKEOVER",
            "ACQUIA",
            "AKAMAI",
            "DESK",
            "DREAMHOST",
            "FASTLY",
            "FEEDPRESS",
            "FIREBASE",
            "FLY_IO",
            "FLYIO",
            "FRESHDESK",
            "FRESHSERVICE",
            "GOOGLE_CLOUD_STORAGE",
            "GCS",
            "GOOGLE_SITES",
            "KINSTA",
            "MAILCHIMP",
            "SENDGRID",
            "SQUARESPACE",
            "STATUSPAGE",
            "UNBOUNCE",
            "USERVOICE",
            "WPENGINE",
            "WP_ENGINE",
            "ZENDESK",
        ],
        # CNAME target domain patterns (case-insensitive substring match)
        "cname_patterns": [
            "elb.amazonaws.com",
            "cloudfront.net",
            "fastly.net",
            "fastlylb.net",
            "firebase.com",
            "firebaseapp.com",
            "fly.io",
            "fly.dev",
            "freshdesk.com",
            "freshservice.com",
            "kinsta.com",
            "kinsta.cloud",
            "mailchimp.com",
            "sendgrid.net",
            "squarespace.com",
            "statuspage.io",
            "unbounce.com",
            "uservoice.com",
            "wpengine.com",
            "zendesk.com",
        ],
        # Fingerprint patterns that indicate parking/non-vulnerable services
        "fingerprint_keywords": [
            "ViewerCertificateException",
            "Fastly error: unknown domain",
            "No Site For Domain",
            "DNS verification",
            "domain verification required",
        ],
    }
    module_threads = 8
    deps_pip = ["baddns~=1.10.185"]

    def select_modules(self):
        selected_submodules = []
        for m in get_all_modules():
            if m.name in self.enabled_submodules:
                selected_submodules.append(m)
        return selected_submodules

    def set_modules(self):
        self.enabled_submodules = self.config.get("enabled_submodules", [])
        if self.enabled_submodules == []:
            self.enabled_submodules = ["CNAME", "MX", "TXT"]

    async def setup(self):
        self.preset.core.logger.include_logger(logging.getLogger("baddns"))
        self.custom_nameservers = self.config.get("custom_nameservers", []) or None
        if self.custom_nameservers:
            self.custom_nameservers = self.helpers.chain_lists(self.custom_nameservers)
        self.only_high_confidence = self.config.get("only_high_confidence", False)
        self.filter_non_vulnerable = self.config.get("filter_non_vulnerable", True)
        self.signatures = load_signatures()
        self.set_modules()
        all_submodules_list = [m.name for m in get_all_modules()]
        for m in self.enabled_submodules:
            if m not in all_submodules_list:
                self.hugewarning(
                    f"Selected BadDNS submodule [{m}] does not exist. Available submodules: [{','.join(all_submodules_list)}]"
                )
                return False
        self.debug(f"Enabled BadDNS Submodules: [{','.join(self.enabled_submodules)}]")
        if self.filter_non_vulnerable:
            self.info(
                f"Filtering enabled for {len(self.NON_VULNERABLE_SERVICES['signatures'])} known non-vulnerable services"
            )
        return True

    def is_non_vulnerable(self, result_dict):
        """
        Check if a baddns result matches known non-vulnerable services.

        Args:
            result_dict: Dictionary with keys like 'signature', 'indicator', 'trigger'

        Returns:
            tuple: (is_filtered, reason) where is_filtered is bool and reason is str
        """
        if not self.filter_non_vulnerable:
            return False, None

        signature = result_dict.get("signature", "").upper()
        indicator = str(result_dict.get("indicator", "")).lower()
        trigger = str(result_dict.get("trigger", "")).lower()
        description = str(result_dict.get("description", "")).lower()

        # Check signature name against known non-vulnerable services
        for non_vuln_sig in self.NON_VULNERABLE_SERVICES["signatures"]:
            if non_vuln_sig.upper() in signature:
                return True, f"Signature '{signature}' matches non-vulnerable service '{non_vuln_sig}'"

        # Check CNAME/indicator against known non-vulnerable domain patterns
        for pattern in self.NON_VULNERABLE_SERVICES["cname_patterns"]:
            if pattern.lower() in indicator or pattern.lower() in trigger:
                return True, f"CNAME pattern '{pattern}' detected in indicator/trigger"

        # Check for fingerprint keywords indicating parking services
        for keyword in self.NON_VULNERABLE_SERVICES["fingerprint_keywords"]:
            if keyword.lower() in description or keyword.lower() in trigger:
                return True, f"Parking service keyword '{keyword}' detected"

        return False, None

    async def handle_event(self, event):
        tasks = []
        for ModuleClass in self.select_modules():
            kwargs = {
                "http_client_class": self.scan.helpers.web.AsyncClient,
                "dns_client": self.scan.helpers.dns.resolver,
                "custom_nameservers": self.custom_nameservers,
                "signatures": self.signatures,
            }

            if ModuleClass.name == "NS":
                kwargs["raw_query_max_retries"] = 1
                kwargs["raw_query_timeout"] = 5.0
                kwargs["raw_query_retry_wait"] = 0

            module_instance = ModuleClass(event.data, **kwargs)
            task = asyncio.create_task(module_instance.dispatch())
            tasks.append((module_instance, task))

        async for completed_task in self.helpers.as_completed([task for _, task in tasks]):
            module_instance = next((m for m, t in tasks if t == completed_task), None)
            try:
                task_result = await completed_task
            except Exception as e:
                self.warning(f"Task for {module_instance} raised an error: {e}")
                task_result = None

            if task_result:
                results = module_instance.analyze()
                if results and len(results) > 0:
                    for r in results:
                        r_dict = r.to_dict()

                        # Check if this result matches a known non-vulnerable service
                        is_filtered, filter_reason = self.is_non_vulnerable(r_dict)
                        if is_filtered:
                            self.debug(
                                f"Filtered non-vulnerable result for {event.host}: {filter_reason}. "
                                f"Signature: {r_dict.get('signature')}, Indicator: {r_dict.get('indicator')}"
                            )
                            continue

                        confidence = r_dict["confidence"]

                        if confidence in ["CONFIRMED", "PROBABLE"]:
                            data = {
                                "severity": "MEDIUM",
                                "description": f"{r_dict['description']}. Confidence: [{confidence}] Signature: [{r_dict['signature']}] Indicator: [{r_dict['indicator']}] Trigger: [{r_dict['trigger']}] baddns Module: [{r_dict['module']}]",
                                "host": str(event.host),
                            }
                            await self.emit_event(
                                data,
                                "VULNERABILITY",
                                event,
                                tags=[f"baddns-{module_instance.name.lower()}"],
                                context=f'{{module}}\'s "{r_dict["module"]}" module found {{event.type}}: {r_dict["description"]}',
                            )

                        elif confidence in ["UNLIKELY", "POSSIBLE"]:
                            if not self.only_high_confidence:
                                data = {
                                    "description": f"{r_dict['description']} Confidence: [{confidence}] Signature: [{r_dict['signature']}] Indicator: [{r_dict['indicator']}] Trigger: [{r_dict['trigger']}] baddns Module: [{r_dict['module']}]",
                                    "host": str(event.host),
                                }
                                await self.emit_event(
                                    data,
                                    "FINDING",
                                    event,
                                    tags=[f"baddns-{module_instance.name.lower()}"],
                                    context=f'{{module}}\'s "{r_dict["module"]}" module found {{event.type}}: {r_dict["description"]}',
                                )
                            else:
                                self.debug(
                                    f"Skipping low-confidence result due to only_high_confidence setting: {confidence}"
                                )

                        else:
                            self.warning(f"Got unrecognized confidence level: {confidence}")

                        found_domains = r_dict.get("found_domains", None)
                        if found_domains:
                            for found_domain in found_domains:
                                await self.emit_event(
                                    found_domain,
                                    "DNS_NAME",
                                    event,
                                    tags=[f"baddns-{module_instance.name.lower()}"],
                                    context=f'{{module}}\'s "{r_dict["module"]}" module found {{event.type}}: {{event.data}}',
                                )
                await module_instance.cleanup()
