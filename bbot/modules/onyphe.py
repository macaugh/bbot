from bbot.modules.templates.subdomain_enum import subdomain_enum_apikey


class onyphe(subdomain_enum_apikey):
    watched_events = ["DNS_NAME"]
    produced_events = ["DNS_NAME"]
    flags = ["subdomain-enum", "passive", "safe"]
    meta = {
        "description": "Query ONYPHE API for subdomains from passive DNS data",
        "created_date": "2025-10-12",
        "author": "@blacklanternsecurity",
        "auth_required": True,
    }
    options = {"api_key": ""}
    options_desc = {"api_key": "ONYPHE API Key"}

    base_url = "https://www.onyphe.io/api/v2"

    async def setup(self):
        return await super().setup()

    def prepare_api_request(self, url, kwargs):
        kwargs["headers"]["Authorization"] = f"apikey {self.api_key}"
        return url, kwargs

    async def ping(self):
        # Check API key validity
        url = f"{self.base_url}/user"
        j = (await self.api_request(url, retry_on_http_429=False)).json()
        assert j.get("status") == "ok", "API key validation failed"

    async def request_url(self, query):
        # Use the summary endpoint which includes passive DNS data
        url = f"{self.base_url}/summary/domain/{self.helpers.quote(query)}"
        response = await self.api_request(url)
        return response

    async def parse_results(self, r, query):
        results = set()
        j = r.json()

        if isinstance(j, dict) and j.get("status") == "ok":
            # Parse results from resolver (passive DNS) category
            for result_category in j.get("results", []):
                if result_category.get("@category") == "resolver":
                    for entry in result_category.get("results", []):
                        # Extract domain/hostname from the entry
                        domain = entry.get("domain", "")
                        if domain and domain.endswith(f".{query}"):
                            results.add(domain)

                        # Also check for 'forward' field which may contain hostnames
                        forward = entry.get("forward", "")
                        if forward and forward.endswith(f".{query}"):
                            results.add(forward)

        return results
