import base64
import logging
import re
from lxml import etree
import httpx

from .base import AbstractScraper, RawResult

logger = logging.getLogger(__name__)

_ARTICLE_ID_RE = re.compile(r"/articles/([A-Za-z0-9_=-]+)")


def _decode_article_url(news_url: str) -> str:
    """
    Extract the original article URL from a Google News RSS link.

    Google News RSS `<link>` elements contain URLs like:
        https://news.google.com/rss/articles/CBMiXGh0dHBz...

    The path component after /articles/ is a base64url-encoded protobuf.
    Google embeds the plain-text article URL inside those bytes, so we can
    extract it by base64url-decoding and scanning for `http`.
    """
    m = _ARTICLE_ID_RE.search(news_url)
    if not m:
        return news_url

    article_id = m.group(1)
    # Restore base64 padding
    article_id += "=" * (-len(article_id) % 4)

    try:
        decoded = base64.urlsafe_b64decode(article_id)
    except Exception:
        return news_url

    # The protobuf payload contains the URL as a plain UTF-8 string.
    # Find the first occurrence of "http" to locate it.
    start = decoded.find(b"http")
    if start == -1:
        return news_url

    # URL ends at the first byte < 0x20 (control char / null terminator)
    end = start
    while end < len(decoded) and decoded[end] >= 0x20:
        end += 1

    extracted = decoded[start:end].decode("utf-8", errors="replace")
    # Sanity check: must look like a URL
    if extracted.startswith("http") and "." in extracted:
        return extracted

    return news_url


class GoogleNewsScraper(AbstractScraper):
    name = "google_news"

    def request(self, query: str, params: dict) -> dict:
        lang = params.get("search_lang", "en")
        country = params.get("country", "us").upper()
        freshness = params.get("freshness")

        q = query
        if freshness:
            tbs_map = {"pd": "qdr:d", "pw": "qdr:w", "pm": "qdr:m", "py": "qdr:y"}
            tbs = tbs_map.get(freshness)
            if tbs:
                q = f"{query} when:{tbs}"

        return {
            "method": "GET",
            "url": "https://news.google.com/rss/search",
            "params": {
                "q": q,
                "hl": f"{lang}-{country}",
                "gl": country,
                "ceid": f"{country}:{lang}",
            },
            "headers": {
                "Accept": "application/rss+xml, application/xml, text/xml",
                "User-Agent": "Mozilla/5.0 (compatible; RSS reader)",
            },
            "follow_redirects": True,
        }

    def parse(self, response: httpx.Response) -> list[RawResult]:
        try:
            root = etree.fromstring(response.content)
        except etree.XMLSyntaxError as exc:
            logger.warning("[google_news] XML parse error: %s", exc)
            return []

        channel = root.find("channel")
        if channel is None:
            return []

        results = []
        for item in channel.findall("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")
            source_el = item.find("source")

            if title_el is None or link_el is None:
                continue

            # Google News title format: "Article title - Source Name"
            raw_title = (title_el.text or "").strip()
            source_name = None
            if source_el is not None:
                source_name = (source_el.text or "").strip() or None
                if source_name and raw_title.endswith(f" - {source_name}"):
                    raw_title = raw_title[: -(len(source_name) + 3)]

            raw_url = (link_el.text or "").strip()
            if not raw_url.startswith("http"):
                continue

            # Decode the article URL from the base64-encoded protobuf path.
            # Falls back to the redirect URL if decoding fails.
            url = _decode_article_url(raw_url)

            description = ""
            if desc_el is not None and desc_el.text:
                try:
                    desc_tree = etree.fromstring(f"<div>{desc_el.text}</div>")
                    description = "".join(desc_tree.itertext()).strip()
                except Exception:
                    description = desc_el.text.strip()

            age = (pub_el.text or "").strip() if pub_el is not None else None

            results.append(RawResult(
                title=raw_title,
                url=url,
                description=description,
                engine=self.name,
                age=age,
                source_name=source_name,
            ))

        return results
