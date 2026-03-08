import logging
import re
import httpx

from .base import AbstractScraper, RawResult

logger = logging.getLogger(__name__)

SAFESEARCH_MAP = {"off": "-2", "moderate": "-1", "strict": "1"}

VQD_RE = re.compile(r'vqd=["\']([\d-]+)["\']')


class DuckDuckGoScraper(AbstractScraper):
    name = "duckduckgo"

    async def _fetch_vqd(self, query: str) -> str | None:
        """Fetch VQD token required for DDG search."""
        try:
            resp = await self.client.get(
                "https://duckduckgo.com/",
                params={"q": query},
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
                    "Accept": "text/html",
                },
            )
            m = VQD_RE.search(resp.text)
            if m:
                return m.group(1)
            # fallback: try x.js endpoint
            resp2 = await self.client.get(
                "https://duckduckgo.com/x.js",
                params={"q": query, "bk": "0"},
            )
            m2 = VQD_RE.search(resp2.text)
            return m2.group(1) if m2 else None
        except Exception as exc:
            logger.warning("[duckduckgo] VQD fetch failed: %s", exc)
            return None

    def request(self, query: str, params: dict) -> dict:
        # This is overridden; search() calls it after fetching VQD
        raise NotImplementedError("Use search() directly")

    def _build_request(self, query: str, params: dict, vqd: str) -> dict:
        count = params.get("count", 10)
        offset = params.get("offset", 0)
        safe = SAFESEARCH_MAP.get(params.get("safesearch", "moderate"), "-1")
        lang = params.get("search_lang", "en")
        country = params.get("country", "us")

        return {
            "method": "POST",
            "url": "https://links.duckduckgo.com/d.js",
            "data": {
                "q": query,
                "l": f"{country}-{lang}",
                "p": safe,
                "s": offset * count,
                "dl": "en",
                "ct": "US",
                "ss_mkt": country,
                "vqd": vqd,
                "o": "json",
                "sp": "0",
            },
            "headers": {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Accept": "application/json, */*",
                "Origin": "https://duckduckgo.com",
                "Referer": "https://duckduckgo.com/",
            },
        }

    def parse(self, response: httpx.Response) -> list[RawResult]:
        try:
            data = response.json()
        except Exception:
            return []

        if b"CAPTCHA" in response.content:
            logger.warning("[duckduckgo] CAPTCHA detected")
            return []

        results = []
        for item in data.get("results", []):
            url = item.get("u") or item.get("url", "")
            if not url or not url.startswith("http"):
                continue
            results.append(RawResult(
                title=item.get("t", ""),
                url=url,
                description=item.get("a", ""),
                engine=self.name,
                age=item.get("date"),
            ))
        return results

    async def search(self, query: str, params: dict) -> list[RawResult]:
        vqd = await self._fetch_vqd(query)
        if not vqd:
            logger.warning("[duckduckgo] no VQD token, skipping")
            return []
        try:
            req_kwargs = self._build_request(query, params, vqd)
            response = await self.client.request(**req_kwargs)
            response.raise_for_status()
            return self.parse(response)
        except Exception as exc:
            logger.warning("[duckduckgo] search failed: %s", exc)
            return []
