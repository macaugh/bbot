from bbot.modules.templates.subdomain_enum import subdomain_enum_apikey


class netlas(subdomain_enum_apikey):
    watched_events = ["DNS_NAME"]
    produced_events = ["DNS_NAME"]
    flags = ["subdomain-enum", "passive", "safe"]
    meta = {
        "description": "Query Netlas.io API for subdomains",
        "created_date": "2025-10-12",
        "author": "@blacklanternsecurity",
        "auth_required": True,
    }
    options = {"api_key": ""}
    options_desc = {"api_key": "Netlas API Key"}

    base_url = "https://app.netlas.io/api"

    async def setup(self):
        return await super().setup()

    def prepare_api_request(self, url, kwargs):
        kwargs["headers"]["X-API-Key"] = self.api_key
        return url, kwargs

    async def ping(self):
        # Check API key validity and quota
        url = f"{self.base_url}/users/current/"
        j = (await self.api_request(url, retry_on_http_429=False)).json()
        assert j.get("balance", 0) > 0, "No balance/quota remaining"

    async def request_url(self, query):
        # Use the domains search endpoint
        url = f"{self.base_url}/domains/?q=*.{self.helpers.quote(query)}"
        response = await self.api_request(url)
        return response

    async def parse_results(self, r, query):
        results = set()
        j = r.json()
        if isinstance(j, dict):
            for item in j.get("items", []):
                domain = item.get("data", {}).get("domain", "")
                if domain and domain.endswith(f".{query}"):
                    results.add(domain)
        return results
