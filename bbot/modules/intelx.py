from bbot.modules.templates.subdomain_enum import subdomain_enum_apikey


class intelx(subdomain_enum_apikey):
    watched_events = ["DNS_NAME"]
    produced_events = ["DNS_NAME"]
    flags = ["subdomain-enum", "passive", "safe"]
    meta = {
        "description": "Query Intelligence X API for subdomains using the Phonebook service",
        "created_date": "2025-10-12",
        "author": "@blacklanternsecurity",
        "auth_required": True,
    }
    options = {"api_key": ""}
    options_desc = {"api_key": "Intelligence X API Key"}

    base_url = "https://2.intelx.io"

    async def setup(self):
        return await super().setup()

    def prepare_api_request(self, url, kwargs):
        kwargs["headers"]["x-key"] = self.api_key
        return url, kwargs

    async def ping(self):
        # Test API key with a simple phonebook search
        url = f"{self.base_url}/phonebook/search"
        json_data = {"term": "example.com", "maxresults": 1, "media": 0, "target": 1}
        r = await self.api_request(url, method="POST", json=json_data, retry_on_http_429=False)
        assert r.status_code == 200, f"API key validation failed with status {r.status_code}"

    async def request_url(self, query):
        # First, initiate the search
        search_url = f"{self.base_url}/phonebook/search"
        search_data = {
            "term": query,
            "maxresults": 10000,
            "media": 0,  # 0 = no media type filter
            "target": 1,  # 1 = domains
        }

        search_response = await self.api_request(search_url, method="POST", json=search_data)
        search_json = search_response.json()

        # Get the search ID
        search_id = search_json.get("id")
        if not search_id:
            return None

        # Poll for results
        result_url = f"{self.base_url}/phonebook/search/result"
        result_data = {"id": search_id, "limit": 10000}

        # Intelligence X may require polling, but we'll try once
        # In practice, results are usually available immediately for phonebook
        import asyncio
        await asyncio.sleep(1)  # Brief delay to allow results to populate

        result_response = await self.api_request(result_url, method="POST", json=result_data)
        return result_response

    async def parse_results(self, r, query):
        results = set()
        if not r:
            return results

        j = r.json()
        if isinstance(j, dict):
            # Parse the selectors (results)
            for selector in j.get("selectors", []):
                # Each selector contains a domain/subdomain
                domain = selector.get("selectorvalue", "")
                if domain and domain.endswith(f".{query}"):
                    results.add(domain)

        return results
