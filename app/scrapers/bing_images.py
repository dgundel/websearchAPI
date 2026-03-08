import json
import logging
import random

import httpx
from lxml import html

from .base import AbstractScraper, RawResult

logger = logging.getLogger(__name__)

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

SAFESEARCH_MAP = {"off": "Off", "moderate": "Moderate", "strict": "Strict"}

SIZE_MAP = {
    "small": "Small",
    "medium": "Medium",
    "large": "Large",
    "wallpaper": "Wallpaper",
}


class BingImagesScraper(AbstractScraper):
    name = "bing_images"

    def request(self, query: str, params: dict) -> dict:
        lang = params.get("search_lang", "en")
        country = params.get("country", "us")
        safe = SAFESEARCH_MAP.get(params.get("safesearch", "moderate"), "Moderate")
        size = params.get("size")

        req_params = {
            "q": query,
            "count": params.get("count", 20),
            "mkt": f"{lang}-{country.upper()}",
            "safeSearch": safe,
            "first": 1,
        }
        if size and size in SIZE_MAP:
            req_params["qft"] = f"imagesize:{SIZE_MAP[size]}"

        return {
            "method": "GET",
            "url": "https://www.bing.com/images/search",
            "params": req_params,
            "headers": {
                "User-Agent": random.choice(UAS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": f"{lang}-{country.upper()},{lang};q=0.5",
            },
        }

    def parse(self, response: httpx.Response) -> list[RawResult]:
        results = []
        tree = html.fromstring(response.content)
        for el in tree.cssselect("a.iusc[m]"):
            try:
                data = json.loads(el.get("m"))
            except (json.JSONDecodeError, TypeError):
                continue

            img_url = data.get("murl", "")
            page_url = data.get("purl", "")
            thumb_url = data.get("turl", "")
            title = data.get("t", "")

            if not img_url or not img_url.startswith("http"):
                continue

            results.append(RawResult(
                title=title,
                url=page_url or img_url,
                description="",
                engine=self.name,
                image_src=img_url,
                thumbnail_src=thumb_url or None,
            ))

            if len(results) >= 20:
                break

        if not results:
            logger.warning("[bing_images] No results parsed from response")

        return results
