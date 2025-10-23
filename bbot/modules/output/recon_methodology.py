"""
Recon Methodology output module for BBOT
Generates technology-based penetration testing checklists from templates
"""

import re
import yaml
import asyncio
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from contextlib import suppress

from bbot.modules.output.base import BaseOutputModule


class ReconMethodology(BaseOutputModule):
    watched_events = ["*"]
    meta = {
        "description": "Generate technology-based methodology checklists from templates",
        "created_date": "2025-10-14",
        "author": "@mcaughman",
    }
    options = {
        "template_repo_url": "https://github.com/yourusername/bbot-recon-templates.git",
        "template_repo_branch": "main",
        "template_cache_dir": "",
        "output_dir": "",
        "upload_to_drive": False,
        "group_by": "host",
        "include_technologies": [],
        "exclude_technologies": [],
    }
    options_desc = {
        "template_repo_url": "Git URL for template repository",
        "template_repo_branch": "Branch to use (default: main)",
        "template_cache_dir": "Local directory to cache templates (default: ~/.bbot/templates)",
        "output_dir": "Directory for generated markdown files (default: scan output dir/methodology)",
        "upload_to_drive": "Upload methodology files to Google Drive",
        "group_by": "Group checklists by 'host' or 'technology'",
        "include_technologies": "Whitelist of technologies to generate checklists for (empty = all)",
        "exclude_technologies": "Blacklist of technologies to skip",
    }

    deps_pip = ["gitpython~=3.1.37", "jinja2~=3.1.2", "pyyaml~=6.0"]

    async def setup(self):
        """Initialize template system and storage"""
        self.template_repo_url = self.config.get("template_repo_url", "")
        self.template_repo_branch = self.config.get("template_repo_branch", "main")
        self.template_cache_dir = self.config.get("template_cache_dir", "")
        self.output_dir = self.config.get("output_dir", "")
        self.upload_to_drive = self.config.get("upload_to_drive", False)
        self.group_by = self.config.get("group_by", "host")
        self.include_technologies = self.config.get("include_technologies", [])
        self.exclude_technologies = self.config.get("exclude_technologies", [])

        # Ensure lists
        if isinstance(self.include_technologies, str):
            self.include_technologies = [t.strip() for t in self.include_technologies.split(",")]
        if isinstance(self.exclude_technologies, str):
            self.exclude_technologies = [t.strip() for t in self.exclude_technologies.split(",")]

        # Set default cache directory
        if not self.template_cache_dir:
            self.template_cache_dir = str(Path.home() / ".bbot" / "templates")

        # Set output directory
        if not self.output_dir:
            self.output_dir = str(self.scan.home / "methodology")

        self.template_cache_dir = Path(self.template_cache_dir).expanduser()
        self.output_dir = Path(self.output_dir).expanduser()

        # Create output directory
        self.helpers.mkdir(self.output_dir)

        # Storage for events during scan
        self.event_storage = defaultdict(lambda: {
            "urls": [],
            "technologies": {},
            "vulnerabilities": [],
            "findings": [],
            "ports": set(),
            "ip_addresses": set(),
            "headers": {},
        })

        # Initialize template loader
        try:
            self.template_loader = TemplateLoader(
                self.template_repo_url,
                self.template_repo_branch,
                self.template_cache_dir,
                self.helpers
            )
            await self.template_loader.initialize()
        except Exception as e:
            self.warning(f"Failed to initialize template loader: {e}")
            self.info("Continuing without template repository - no methodology files will be generated")
            return True  # Soft fail - don't abort scan

        self.info(f"Recon methodology module enabled. Grouping by: {self.group_by}")
        return True

    async def handle_event(self, event):
        """Collect events for later aggregation"""
        if event.type == "FINISHED":
            return

        host = str(event.host)

        # Store URLs
        if event.type == "URL":
            self.event_storage[host]["urls"].append({
                "data": str(event.data),
                "event_type": event.type
            })

        # Store TECHNOLOGY events
        elif event.type == "TECHNOLOGY":
            tech_data = event.data if isinstance(event.data, dict) else {"technology": str(event.data)}
            tech_name = tech_data.get("technology", str(event.data))
            tech_version = tech_data.get("version", "")

            self.event_storage[host]["technologies"][tech_name] = {
                "name": tech_name,
                "version": tech_version
            }

        # Store VULNERABILITY events
        elif event.type == "VULNERABILITY":
            vuln_data = event.data if isinstance(event.data, dict) else {"description": str(event.data)}
            self.event_storage[host]["vulnerabilities"].append(vuln_data)

        # Store FINDING events
        elif event.type == "FINDING":
            finding_data = event.data if isinstance(event.data, dict) else {"description": str(event.data)}
            self.event_storage[host]["findings"].append(finding_data)

        # Store OPEN_TCP_PORT events
        elif event.type == "OPEN_TCP_PORT":
            port = event.data.get("port") if isinstance(event.data, dict) else event.data
            self.event_storage[host]["ports"].add(port)

        # Store IP_ADDRESS events
        elif event.type == "IP_ADDRESS":
            self.event_storage[host]["ip_addresses"].add(str(event.data))

        # Store HTTP_RESPONSE headers
        elif event.type == "HTTP_RESPONSE":
            if isinstance(event.data, dict) and "header" in event.data:
                self.event_storage[host]["headers"] = event.data.get("header", {})

    async def report(self):
        """Generate all methodology files after scan completion"""
        if not hasattr(self, "template_loader"):
            self.debug("Template loader not initialized, skipping methodology generation")
            return

        if not self.event_storage:
            self.info("No events collected, skipping methodology generation")
            return

        self.info(f"Generating methodology checklists for {len(self.event_storage)} hosts...")

        generated_files = []

        if self.group_by == "host":
            # Generate one checklist per host with all its technologies
            for host, data in self.event_storage.items():
                files = await self._generate_host_methodologies(host, data)
                generated_files.extend(files)

        elif self.group_by == "technology":
            # Generate one checklist per technology across all hosts
            tech_hosts = self._group_by_technology()
            for tech, hosts_data in tech_hosts.items():
                file_path = await self._generate_technology_methodology(tech, hosts_data)
                if file_path:
                    generated_files.append(file_path)

        if generated_files:
            self.info(f"Generated {len(generated_files)} methodology files in {self.output_dir}")

            # Upload to Google Drive if requested
            if self.upload_to_drive:
                await self._upload_to_drive(generated_files)
        else:
            self.info("No methodology files generated (no matching technologies found)")

    async def _generate_host_methodologies(self, host, data):
        """Generate methodology files for a single host"""
        generated_files = []
        technologies = data.get("technologies", {})

        if not technologies:
            self.debug(f"No technologies detected for {host}, skipping")
            return generated_files

        for tech_name, tech_info in technologies.items():
            # Check include/exclude filters
            if not self._should_generate_for_technology(tech_name):
                continue

            try:
                # Load template for this technology
                template = await self.template_loader.get_template(tech_name)
                if not template:
                    self.debug(f"No template found for {tech_name}, skipping")
                    continue

                # Build context for template rendering
                context = self._build_template_context(host, data, tech_name, tech_info)

                # Render template
                rendered = self._render_template(template, context)

                # Write to file
                safe_host = host.replace(":", "_").replace("/", "_")
                safe_tech = tech_name.replace(" ", "_").replace("/", "_")
                filename = f"{safe_host}_{safe_tech}.md"
                file_path = self.output_dir / filename

                file_path.write_text(rendered)
                generated_files.append(file_path)

                self.debug(f"Generated methodology: {filename}")

            except Exception as e:
                self.warning(f"Failed to generate methodology for {host}/{tech_name}: {e}")

        return generated_files

    async def _generate_technology_methodology(self, tech_name, hosts_data):
        """Generate a single methodology file for a technology across multiple hosts"""
        if not self._should_generate_for_technology(tech_name):
            return None

        try:
            template = await self.template_loader.get_template(tech_name)
            if not template:
                return None

            # Aggregate data from all hosts
            aggregated_context = {
                "technology": tech_name,
                "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bbot_version": self.scan.version,
                "hosts": [],
                "total_vulnerabilities": 0,
                "total_findings": 0,
            }

            for host, data in hosts_data.items():
                host_info = {
                    "host": host,
                    "urls": data.get("urls", []),
                    "vulnerabilities": data.get("vulnerabilities", []),
                    "findings": data.get("findings", []),
                    "ports": sorted(data.get("ports", set())),
                    "ip_addresses": list(data.get("ip_addresses", set())),
                }
                aggregated_context["hosts"].append(host_info)
                aggregated_context["total_vulnerabilities"] += len(host_info["vulnerabilities"])
                aggregated_context["total_findings"] += len(host_info["findings"])

            # Use first host's data as primary context
            if aggregated_context["hosts"]:
                first_host = aggregated_context["hosts"][0]
                aggregated_context.update({
                    "host": first_host["host"],
                    "url": first_host["urls"][0]["data"] if first_host["urls"] else "",
                    "ip_address": first_host["ip_addresses"][0] if first_host["ip_addresses"] else "",
                    "ports": first_host["ports"],
                    "vulnerabilities": first_host["vulnerabilities"],
                    "findings": first_host["findings"],
                })

            rendered = self._render_template(template, aggregated_context)

            safe_tech = tech_name.replace(" ", "_").replace("/", "_")
            filename = f"{safe_tech}_methodology.md"
            file_path = self.output_dir / filename

            file_path.write_text(rendered)
            self.debug(f"Generated technology methodology: {filename}")

            return file_path

        except Exception as e:
            self.warning(f"Failed to generate methodology for {tech_name}: {e}")
            return None

    def _group_by_technology(self):
        """Group hosts by technology"""
        tech_hosts = defaultdict(dict)

        for host, data in self.event_storage.items():
            for tech_name in data.get("technologies", {}).keys():
                tech_hosts[tech_name][host] = data

        return tech_hosts

    def _build_template_context(self, host, data, tech_name, tech_info):
        """Build context dictionary for template rendering"""
        urls = data.get("urls", [])
        primary_url = urls[0]["data"] if urls else f"http://{host}"

        context = {
            "host": host,
            "technology": tech_name,
            "version": tech_info.get("version", ""),
            "url": primary_url,
            "ip_address": list(data.get("ip_addresses", set()))[0] if data.get("ip_addresses") else "",
            "ports": sorted(list(data.get("ports", set()))),
            "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bbot_version": self.scan.version,
            "vulnerabilities": data.get("vulnerabilities", []),
            "findings": data.get("findings", []),
            "headers": data.get("headers", {}),
            "scan": {
                "name": self.scan.name,
                "id": self.scan.id,
            }
        }

        return context

    def _render_template(self, template_content, context):
        """Render Jinja2 template with context"""
        from jinja2 import Template, TemplateError

        try:
            template = Template(template_content)
            return template.render(**context)
        except TemplateError as e:
            raise Exception(f"Template rendering error: {e}")

    def _should_generate_for_technology(self, tech_name):
        """Check if we should generate methodology for this technology"""
        # Check include list
        if self.include_technologies:
            if not any(inc.lower() in tech_name.lower() for inc in self.include_technologies):
                return False

        # Check exclude list
        if self.exclude_technologies:
            if any(exc.lower() in tech_name.lower() for exc in self.exclude_technologies):
                return False

        return True

    async def _upload_to_drive(self, file_paths):
        """Upload methodology files to Google Drive"""
        # Check if Google Drive module is available and has uploaded
        if "google_drive_folder_link" not in self.scan.context:
            self.debug("Google Drive not configured, skipping upload")
            return

        self.info(f"Uploading {len(file_paths)} methodology files to Google Drive...")

        # Files are already uploaded by google_drive module if upload_methodology=True
        # This is just for logging
        methodology_links = self.scan.context.get("google_drive_methodology_links", [])
        if methodology_links:
            self.info(f"Methodology files available in Google Drive: {len(methodology_links)} files")


class TemplateLoader:
    """Handles loading and caching of templates from git repository"""

    def __init__(self, repo_url, branch, cache_dir, helpers):
        self.repo_url = repo_url
        self.branch = branch
        self.cache_dir = Path(cache_dir)
        self.helpers = helpers
        self.templates = {}
        self.config = {}
        self.repo = None

    async def initialize(self):
        """Clone or update template repository"""
        if not self.repo_url:
            raise Exception("No template repository URL configured")

        # Handle file:// URLs for local repositories
        if self.repo_url.startswith("file://"):
            local_path = self.repo_url.replace("file://", "")
            self.cache_dir = Path(local_path)
            if not self.cache_dir.exists():
                raise Exception(f"Local template repository not found: {local_path}")
        else:
            # Clone or update git repository
            if not self.cache_dir.exists():
                await self._clone_repo()
            else:
                await self._update_repo()

        # Load configuration
        await self._load_config()

    async def _clone_repo(self):
        """Clone template repository"""
        import git

        def _clone():
            self.helpers.mkdir(self.cache_dir.parent)
            git.Repo.clone_from(
                self.repo_url,
                self.cache_dir,
                branch=self.branch,
                depth=1
            )

        await asyncio.to_thread(_clone)

    async def _update_repo(self):
        """Update existing repository"""
        import git

        def _update():
            repo = git.Repo(self.cache_dir)
            origin = repo.remotes.origin
            origin.fetch()
            repo.git.checkout(self.branch)
            origin.pull()

        try:
            await asyncio.to_thread(_update)
        except Exception:
            # Ignore update failures, use existing cache
            pass

    async def _load_config(self):
        """Load template configuration"""
        config_file = self.cache_dir / "config.yml"
        if not config_file.exists():
            raise Exception(f"Template config.yml not found in {self.cache_dir}")

        with open(config_file) as f:
            self.config = yaml.safe_load(f)

    async def get_template(self, technology):
        """Get template for a technology, with fallback"""
        # Check cache
        if technology in self.templates:
            return self.templates[technology]

        # Match technology to template via patterns
        template_path = self._match_technology(technology)

        if not template_path:
            # Use fallback template
            category = self._guess_category(technology)
            fallbacks = self.config.get("templates", {}).get("fallbacks", {})
            template_path = fallbacks.get(category, fallbacks.get("default", "web/default.md"))

        # Load template file
        template_content = await self._load_template_file(template_path)

        if template_content:
            # Cache template
            self.templates[technology] = template_content
            return template_content

        return None

    def _match_technology(self, technology):
        """Match technology name to template using patterns"""
        mappings = self.config.get("templates", {}).get("mapping", [])

        for mapping in mappings:
            pattern = mapping.get("pattern", "")
            if re.search(pattern, technology, re.IGNORECASE):
                return mapping.get("template")

        return None

    def _guess_category(self, technology):
        """Guess category based on technology name"""
        tech_lower = technology.lower()

        if any(word in tech_lower for word in ["api", "rest", "graphql", "soap"]):
            return "api"
        elif any(word in tech_lower for word in ["django", "flask", "rails", "spring", "laravel"]):
            return "framework"
        elif any(word in tech_lower for word in ["mysql", "postgres", "mongo", "redis"]):
            return "database"
        elif any(word in tech_lower for word in ["aws", "azure", "gcp", "s3", "blob"]):
            return "cloud"
        else:
            return "web"

    async def _load_template_file(self, template_path):
        """Load template file content"""
        file_path = self.cache_dir / "templates" / template_path

        if not file_path.exists():
            return None

        try:
            return file_path.read_text()
        except Exception:
            return None
