import pytest
import httpx
import respx

from app.scrapers.google import GoogleScraper

GOOGLE_HTML = b"""
<html><body>
<div class="MjjYud">
  <a href="https://example.com/page1">
    <h3>Example Page 1</h3>
  </a>
  <div class="VwiC3b">This is a description for page 1.</div>
</div>
<div class="MjjYud">
  <a href="https://example.org/page2">
    <h3>Example Page 2</h3>
  </a>
  <div class="VwiC3b">This is a description for page 2.</div>
  <span class="LEwnzc">2 days ago</span>
</div>
</body></html>
"""

CAPTCHA_HTML = b"""
<html><body>
<div>Our systems have detected unusual traffic from your computer network.
<a href="/sorry/index">Continue</a>
</div></body></html>
"""


@pytest.fixture
def scraper():
    client = httpx.AsyncClient()
    return GoogleScraper(client)


def test_request_builds_correct_url(scraper):
    req = scraper.request("python fastapi", {"count": 5, "offset": 0, "search_lang": "en", "country": "us", "safesearch": "moderate"})
    assert req["method"] == "GET"
    assert "google.com/search" in req["url"]
    assert "python+fastapi" in req["url"] or "python" in req["url"]


def test_parse_extracts_results(scraper):
    response = httpx.Response(200, content=GOOGLE_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert len(results) == 2
    assert results[0].title == "Example Page 1"
    assert results[0].url == "https://example.com/page1"
    assert "description" in results[0].description
    assert results[0].engine == "google"


def test_parse_extracts_age(scraper):
    response = httpx.Response(200, content=GOOGLE_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results[1].age == "2 days ago"


def test_parse_captcha_returns_empty(scraper):
    response = httpx.Response(200, content=CAPTCHA_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results == []


@pytest.mark.asyncio
async def test_search_returns_empty_on_http_error():
    with respx.mock() as mock:
        mock.get(url__regex=r"google\.com").mock(return_value=httpx.Response(429))
        async with httpx.AsyncClient() as client:
            scraper = GoogleScraper(client)
            results = await scraper.search("test", {})
            assert results == []
