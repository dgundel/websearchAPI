import json
import logging
import re
import random

import httpx
from lxml import html

from .base import AbstractScraper, RawResult

logger = logging.getLogger(__name__)

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

SAFESEARCH_MAP = {"off": "&safe=off", "moderate": "", "strict": "&safe=active"}

SIZE_MAP = {
    "small": "isz:s",
    "medium": "isz:m",
    "large": "isz:l",
    "wallpaper": "isz:qsvga",
}


class GoogleImagesScraper(AbstractScraper):
    name = "google_images"

    def request(self, query: str, params: dict) -> dict:
        safe = SAFESEARCH_MAP.get(params.get("safesearch", "moderate"), "")
        lang = params.get("search_lang", "en")
        country = params.get("country", "us")
        size = params.get("size")
        tbs = SIZE_MAP.get(size, "") if size else ""

        url = (
            f"https://www.google.com/search"
            f"?q={query}&tbm=isch&hl={lang}&gl={country}{safe}"
            + (f"&tbs={tbs}" if tbs else "")
        )
        return {
            "method": "GET",
            "url": url,
            "headers": {
                "User-Agent": random.choice(UAS),
                "Accept": "text/html",
                "Accept-Language": f"{lang},en;q=0.5",
                "Cookie": "CONSENT=YES+cb; SOCS=CAI",
            },
        }

    def parse(self, response: httpx.Response) -> list[RawResult]:
        content = response.content
        if b"sorry/index" in content:
            logger.warning("[google_images] CAPTCHA detected")
            return []

        # Extract image data from embedded JSON in page scripts
        results = []
        text = response.text

        # Google embeds image data in AF_initDataCallback scripts
        pattern = re.compile(r'\["(https?://[^"]+?)",\s*(\d+),\s*(\d+)\]')
        seen_urls: set[str] = set()

        for m in pattern.finditer(text):
            img_url = m.group(1)
            if img_url in seen_urls:
                continue
            # Skip Google's own thumbnails served via encrypted-tbn
            if "encrypted-tbn" in img_url:
                continue
            seen_urls.add(img_url)

            results.append(RawResult(
                title="",
                url=img_url,
                description="",
                engine=self.name,
                image_src=img_url,
            ))

            if len(results) >= 20:
                break

        return results
