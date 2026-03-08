import json
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

SAFESEARCH_MAP = {
    "off": "Off",
    "moderate": "Moderate",
    "strict": "Strict",
}


class BingVideosScraper(AbstractScraper):
    name = "bing_videos"

    def request(self, query: str, params: dict) -> dict:
        lang = params.get("search_lang", "en")
        country = params.get("country", "us")
        safesearch = params.get("safesearch", "moderate")

        return {
            "method": "GET",
            "url": "https://www.bing.com/videos/search",
            "params": {
                "q": query,
                "count": params.get("count", 10),
                "mkt": f"{lang}-{country.upper()}",
                "safeSearch": SAFESEARCH_MAP.get(safesearch, "Moderate"),
            },
            "headers": {
                "User-Agent": random.choice(UAS),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": f"{lang}-{country.upper()},{lang};q=0.8",
            },
        }

    def parse(self, response: httpx.Response) -> list[RawResult]:
        tree = html.fromstring(response.content)
        results = []

        for card in tree.cssselect("div.mc_vtvc"):
            # Extract mmeta JSON attribute for URL and thumbnail
            mmeta_raw = card.get("mmeta", "")
            mmeta = {}
            if mmeta_raw:
                try:
                    mmeta = json.loads(mmeta_raw)
                except (json.JSONDecodeError, ValueError):
                    pass

            url = mmeta.get("murl", "").strip()
            if not url:
                # Fallback: ourl from child div
                rc = card.cssselect("div.mc_vtvc_con_rc")
                if rc:
                    url = rc[0].get("ourl", "").strip()
            if not url or not url.startswith("http"):
                continue

            thumbnail_src = mmeta.get("turl", "").strip() or None

            # Title from aria-label on link or meta div text
            title = ""
            link_el = card.cssselect("a.mc_vtvc_link")
            if link_el:
                title = link_el[0].get("aria-label", "").strip()
            if not title:
                meta_el = card.cssselect("div.mc_vtvc_meta")
                if meta_el:
                    title = meta_el[0].text_content().strip()

            # Duration from overlay span
            duration = None
            dur_el = card.cssselect("div.mc_vtvc_dur, span.mc_vtvc_dur")
            if dur_el:
                duration = dur_el[0].text_content().strip() or None

            # Source and age from meta spans
            source = None
            age = None
            spans = card.cssselect("div.mc_vtvc_meta_block span, div.mc_vtvc_meta span")
            span_texts = [s.text_content().strip() for s in spans if s.text_content().strip()]
            if span_texts:
                source = span_texts[0]
            if len(span_texts) >= 2:
                age = span_texts[-1]

            results.append(RawResult(
                title=title,
                url=url,
                description="",
                engine=self.name,
                thumbnail_src=thumbnail_src,
                source_name=source,
                age=age,
                duration=duration,
            ))

        return results
