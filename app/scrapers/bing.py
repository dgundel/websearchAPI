import base64
import logging
import random
from urllib.parse import urlparse, parse_qs

from lxml import html
import httpx

from .base import AbstractScraper, RawResult

logger = logging.getLogger(__name__)

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

SAFESEARCH_MAP = {"off": "off", "moderate": "Moderate", "strict": "Strict"}


def _decode_bing_url(href: str) -> str:
    """Decode Bing's /ck/a?!&&p= redirect URLs (relative or absolute)."""
    if "/ck/a" not in href and not href.startswith("/ck/"):
        return href
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    u_param = qs.get("u", [None])[0]
    if u_param and u_param.startswith("a1"):
        try:
            # Bing encodes as: 'a1' + base64url(url)
            b64 = u_param[2:]
            # pad to multiple of 4
            b64 += "=" * (-len(b64) % 4)
            return base64.urlsafe_b64decode(b64).decode("utf-8", errors="replace")
        except Exception:
            pass
    return href


class BingScraper(AbstractScraper):
    name = "bing"

    def request(self, query: str, params: dict) -> dict:
        count = params.get("count", 10)
        offset = params.get("offset", 0)
        lang = params.get("search_lang", "en")
        country = params.get("country", "us")
        safe = SAFESEARCH_MAP.get(params.get("safesearch", "moderate"), "Moderate")

        return {
            "method": "GET",
            "url": "https://www.bing.com/search",
            "params": {
                "q": query,
                "count": count,
                "first": offset * count + 1,
                "mkt": f"{lang}-{country.upper()}",
                "safeSearch": safe,
            },
            "headers": {
                "User-Agent": random.choice(UAS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": f"{lang}-{country.upper()},{lang};q=0.5",
            },
        }

    def parse(self, response: httpx.Response) -> list[RawResult]:
        content = response.content
        tree = html.fromstring(content)
        results = []

        for li in tree.cssselect("li.b_algo"):
            title_el = li.cssselect("h2 a")
            desc_el = li.cssselect("div.b_caption p, p.b_lineclamp2, p.b_lineclamp4")
            date_el = li.cssselect("span.news_dt")

            if not title_el:
                continue

            title = title_el[0].text_content().strip()
            href = title_el[0].get("href", "")
            href = _decode_bing_url(href)
            if not href.startswith("http"):
                continue

            description = desc_el[0].text_content().strip() if desc_el else ""
            age = date_el[0].text_content().strip() if date_el else None

            results.append(RawResult(
                title=title,
                url=href,
                description=description,
                engine=self.name,
                age=age,
            ))

        return results
