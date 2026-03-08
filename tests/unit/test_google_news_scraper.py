import base64
import pytest
import httpx

from app.scrapers.google_news import GoogleNewsScraper, _decode_article_url


def _make_article_id(url: str) -> str:
    """Encode a URL the same way Google News does (protobuf header + url bytes, base64url)."""
    url_bytes = url.encode()
    payload = bytes([0x08, 0x13, 0x22, len(url_bytes)]) + url_bytes
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


TC_URL = "https://techcrunch.com/2026/03/08/ai-breakthrough/"
BBC_URL = "https://bbc.com/news/article2"
TC_ID = _make_article_id(TC_URL)
BBC_ID = _make_article_id(BBC_URL)

RSS_FEED = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News</title>
    <item>
      <title>AI breakthrough announced - TechCrunch</title>
      <link>https://news.google.com/rss/articles/{TC_ID}</link>
      <description>Scientists have announced a major AI breakthrough.</description>
      <pubDate>Sun, 08 Mar 2026 10:00:00 GMT</pubDate>
      <source url="https://techcrunch.com">TechCrunch</source>
    </item>
    <item>
      <title>Second article - BBC</title>
      <link>https://news.google.com/rss/articles/{BBC_ID}</link>
      <description>Another news item.</description>
      <pubDate>Sun, 08 Mar 2026 09:00:00 GMT</pubDate>
      <source url="https://bbc.com">BBC</source>
    </item>
  </channel>
</rss>""".encode()

MALFORMED_XML = b"this is not xml at all <<"

EMPTY_CHANNEL = b"""<?xml version="1.0"?>
<rss version="2.0"><channel></channel></rss>"""


@pytest.fixture
def scraper():
    return GoogleNewsScraper(httpx.AsyncClient())


# --- _decode_article_url unit tests ---

def test_decode_article_url_extracts_real_url():
    news_url = f"https://news.google.com/rss/articles/{TC_ID}"
    assert _decode_article_url(news_url) == TC_URL


def test_decode_article_url_passthrough_non_google():
    url = "https://example.com/article"
    assert _decode_article_url(url) == url


def test_decode_article_url_passthrough_on_garbage():
    url = "https://news.google.com/rss/articles/!!!invalid!!!"
    assert _decode_article_url(url) == url


# --- request tests ---

def test_request_uses_rss_endpoint(scraper):
    req = scraper.request("ai news", {"search_lang": "en", "country": "us"})
    assert req["method"] == "GET"
    assert "news.google.com/rss" in req["url"]
    assert req["params"]["q"] == "ai news"


def test_request_includes_freshness(scraper):
    req = scraper.request("news", {"search_lang": "en", "country": "us", "freshness": "pw"})
    assert "qdr:w" in req["params"]["q"]


# --- parse tests ---

def test_parse_extracts_results(scraper):
    response = httpx.Response(200, content=RSS_FEED, headers={"content-type": "application/rss+xml"})
    results = scraper.parse(response)
    assert len(results) == 2


def test_parse_decodes_urls_in_place(scraper):
    """parse() should return original article URLs, not Google News redirects."""
    response = httpx.Response(200, content=RSS_FEED, headers={"content-type": "application/rss+xml"})
    results = scraper.parse(response)
    assert results[0].url == TC_URL
    assert results[1].url == BBC_URL
    assert all("news.google.com" not in r.url for r in results)


def test_parse_strips_source_from_title(scraper):
    response = httpx.Response(200, content=RSS_FEED, headers={"content-type": "application/rss+xml"})
    results = scraper.parse(response)
    assert results[0].title == "AI breakthrough announced"
    assert results[0].source_name == "TechCrunch"


def test_parse_extracts_age(scraper):
    response = httpx.Response(200, content=RSS_FEED, headers={"content-type": "application/rss+xml"})
    results = scraper.parse(response)
    assert "2026" in results[0].age


def test_parse_malformed_xml_returns_empty(scraper):
    response = httpx.Response(200, content=MALFORMED_XML, headers={"content-type": "application/rss+xml"})
    results = scraper.parse(response)
    assert results == []


def test_parse_empty_channel_returns_empty(scraper):
    response = httpx.Response(200, content=EMPTY_CHANNEL, headers={"content-type": "application/rss+xml"})
    results = scraper.parse(response)
    assert results == []
