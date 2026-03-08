import logging
import random
from lxml import html
import httpx

from .base import AbstractScraper, RawResult

logger = logging.getLogger(__name__)

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

FRESHNESS_MAP = {
    "pd": "1",   # past day
    "pw": "2",   # past week
    "pm": "3",   # past month
    "py": "4",   # past year (Bing: any time = default, use week as closest)
}


class BingNewsScraper(AbstractScraper):
    name = "bing_news"

    def request(self, query: str, params: dict) -> dict:
        lang = params.get("search_lang", "en")
        country = params.get("country", "us")
        freshness = params.get("freshness")

        req_params = {
            "q": query,
            "count": params.get("count", 10),
            "mkt": f"{lang}-{country.upper()}",
            "setlang": lang,
        }
        if freshness and freshness in FRESHNESS_MAP:
            req_params["qft"] = f"interval={FRESHNESS_MAP[freshness]}"

        return {
            "method": "GET",
            "url": "https://www.bing.com/news/search",
            "params": req_params,
            "headers": {
                "User-Agent": random.choice(UAS),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": f"{lang}-{country.upper()},{lang};q=0.8",
            },
        }

    def parse(self, response: httpx.Response) -> list[RawResult]:
        content = response.content
        tree = html.fromstring(content)
        results = []

        for card in tree.cssselect("div.news-card"):
            # Direct article URL stored in data-url attribute
            url = card.get("data-url", "").strip()
            if not url or not url.startswith("http"):
                # Fallback: a.title href
                title_link = card.cssselect("a.title")
                if title_link:
                    url = title_link[0].get("href", "").strip()
            if not url or not url.startswith("http"):
                continue

            title_el = card.cssselect("a.title")
            desc_el = card.cssselect("div.snippet")
            date_el = card.cssselect("div.ns_sc_tm, span.time")
            source_el = card.cssselect("div.source a, a.source")
            thumb_el = card.cssselect("img.rms_img, div.img_cont img")

            title = title_el[0].text_content().strip() if title_el else card.get("data-title", "")
            description = desc_el[0].text_content().strip() if desc_el else ""
            age = date_el[0].text_content().strip() if date_el else None
            source = source_el[0].text_content().strip() if source_el else None
            thumbnail_src = thumb_el[0].get("src") if thumb_el else None

            results.append(RawResult(
                title=title,
                url=url,
                description=description,
                engine=self.name,
                age=age,
                source_name=source,
                thumbnail_src=thumbnail_src,
            ))

        return results
