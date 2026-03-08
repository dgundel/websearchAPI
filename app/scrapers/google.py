import random
import logging
from lxml import html
import httpx

from .base import AbstractScraper, RawResult

logger = logging.getLogger(__name__)

DESKTOP_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

SAFESEARCH_MAP = {"off": "&safe=off", "moderate": "", "strict": "&safe=active"}


class GoogleScraper(AbstractScraper):
    name = "google"

    def request(self, query: str, params: dict) -> dict:
        safe = SAFESEARCH_MAP.get(params.get("safesearch", "moderate"), "")
        count = params.get("count", 10)
        offset = params.get("offset", 0)
        lang = params.get("search_lang", "en")
        country = params.get("country", "us")

        url = (
            f"https://www.google.com/search"
            f"?q={query}&num={count}&start={offset * count}"
            f"&hl={lang}&gl={country}{safe}"
        )
        return {
            "method": "GET",
            "url": url,
            "headers": {
                "User-Agent": random.choice(DESKTOP_UAS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": f"{lang},en;q=0.5",
                "Cookie": "CONSENT=YES+cb; SOCS=CAI",
            },
        }

    def parse(self, response: httpx.Response) -> list[RawResult]:
        content = response.content
        if b"sorry/index" in content or b"recaptcha" in content.lower():
            logger.warning("[google] CAPTCHA detected")
            return []

        tree = html.fromstring(content)
        results = []

        for block in tree.cssselect("div.MjjYud, div.g"):
            title_el = block.cssselect("h3")
            link_el = block.cssselect("a[href]")
            desc_el = block.cssselect("div.VwiC3b, span.aCOpRe, div[data-sncf]")

            if not title_el or not link_el:
                continue

            title = title_el[0].text_content().strip()
            href = link_el[0].get("href", "")
            if not href.startswith("http"):
                continue

            description = desc_el[0].text_content().strip() if desc_el else ""
            age_el = block.cssselect("span.LEwnzc, span[class*='date']")
            age = age_el[0].text_content().strip() if age_el else None

            results.append(RawResult(
                title=title,
                url=href,
                description=description,
                engine=self.name,
                age=age,
            ))

        return results
