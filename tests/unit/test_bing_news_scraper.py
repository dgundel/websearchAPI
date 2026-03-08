import pytest
import httpx
import respx

from app.scrapers.bing_news import BingNewsScraper

BING_NEWS_HTML = b"""
<html><body>
<div class="news-card newsitem cardcommon"
     data-url="https://www.elektro.net/sps-programmierung-mit-scl-tia-portal"
     data-title="SPS-Programmierung mit SCL im TIA Portal">
  <a class="title" href="https://www.elektro.net/sps-programmierung-mit-scl-tia-portal">
    SPS-Programmierung mit SCL im TIA Portal
  </a>
  <div class="snippet">Structured Control Language im Einsatz</div>
  <div class="source">
    <a href="/news/search?q=site:elektro.net">elektro.net</a>
    <span class="time">3 Std.</span>
    <div class="ns_sc_tm">3 Std.</div>
  </div>
</div>
<div class="news-card newsitem cardcommon"
     data-url="https://www.sps-magazin.de/artikel/2026-03-automatisierung"
     data-title="Automatisierung 2026">
  <a class="title" href="https://www.sps-magazin.de/artikel/2026-03-automatisierung">
    Automatisierung 2026: Trends und Ausblick
  </a>
  <div class="snippet">Die wichtigsten Automatisierungstrends.</div>
  <div class="source">
    <a href="/news/search?q=site:sps-magazin.de">SPS-Magazin</a>
    <div class="ns_sc_tm">2 Tage</div>
  </div>
</div>
</body></html>
"""


@pytest.fixture
def scraper():
    return BingNewsScraper(httpx.AsyncClient())


def test_request_uses_bing_news_endpoint(scraper):
    req = scraper.request("SPS Programmierung", {"search_lang": "de", "country": "de"})
    assert req["method"] == "GET"
    assert "bing.com/news/search" in req["url"]
    assert req["params"]["q"] == "SPS Programmierung"
    assert "DE" in req["params"]["mkt"]


def test_request_includes_freshness(scraper):
    req = scraper.request("news", {"search_lang": "en", "country": "us", "freshness": "pw"})
    assert "qft" in req["params"]
    assert "interval=2" in req["params"]["qft"]


def test_parse_extracts_direct_urls(scraper):
    response = httpx.Response(200, content=BING_NEWS_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert len(results) == 2
    assert results[0].url == "https://www.elektro.net/sps-programmierung-mit-scl-tia-portal"
    assert results[1].url == "https://www.sps-magazin.de/artikel/2026-03-automatisierung"


def test_parse_no_bing_redirect_urls(scraper):
    """URLs must be direct article links, never bing.com or news.google.com."""
    response = httpx.Response(200, content=BING_NEWS_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert all("bing.com" not in r.url for r in results)
    assert all("google.com" not in r.url for r in results)


def test_parse_extracts_title(scraper):
    response = httpx.Response(200, content=BING_NEWS_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert "SPS-Programmierung" in results[0].title


def test_parse_extracts_description(scraper):
    response = httpx.Response(200, content=BING_NEWS_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert "Structured Control Language" in results[0].description


def test_parse_extracts_age(scraper):
    response = httpx.Response(200, content=BING_NEWS_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results[0].age is not None


def test_parse_extracts_source(scraper):
    response = httpx.Response(200, content=BING_NEWS_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results[0].source_name == "elektro.net"


def test_parse_empty_returns_empty(scraper):
    response = httpx.Response(200, content=b"<html><body></body></html>", headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results == []


@pytest.mark.asyncio
async def test_search_returns_empty_on_error():
    with respx.mock() as mock:
        mock.get(url__regex=r"bing\.com/news").mock(return_value=httpx.Response(503))
        async with httpx.AsyncClient() as client:
            scraper = BingNewsScraper(client)
            results = await scraper.search("test", {})
            assert results == []
