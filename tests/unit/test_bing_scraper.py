import pytest
import httpx
import respx

from app.scrapers.bing import BingScraper, _decode_bing_url

BING_HTML = b"""
<html><body>
<ol id="b_results">
  <li class="b_algo">
    <h2><a href="https://example.com/result1">Result One</a></h2>
    <div class="b_caption"><p>Description for result one.</p></div>
  </li>
  <li class="b_algo">
    <h2><a href="https://example.org/result2">Result Two</a></h2>
    <div class="b_caption"><p>Description for result two.</p></div>
    <span class="news_dt">Jan 1, 2024</span>
  </li>
</ol>
</body></html>
"""


@pytest.fixture
def scraper():
    return BingScraper(httpx.AsyncClient())


def test_decode_bing_url_passthrough():
    assert _decode_bing_url("https://example.com") == "https://example.com"


def test_request_has_correct_params(scraper):
    req = scraper.request("test query", {"count": 10, "offset": 0, "search_lang": "en", "country": "us", "safesearch": "moderate"})
    assert req["method"] == "GET"
    assert "bing.com/search" in req["url"]
    assert req["params"]["q"] == "test query"
    assert req["params"]["safeSearch"] == "Moderate"


def test_parse_extracts_results(scraper):
    response = httpx.Response(200, content=BING_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert len(results) == 2
    assert results[0].title == "Result One"
    assert results[0].url == "https://example.com/result1"
    assert results[0].engine == "bing"


def test_parse_extracts_age(scraper):
    response = httpx.Response(200, content=BING_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results[1].age == "Jan 1, 2024"


@pytest.mark.asyncio
async def test_search_returns_empty_on_error():
    with respx.mock() as mock:
        mock.get(url__regex=r"bing\.com").mock(return_value=httpx.Response(503))
        async with httpx.AsyncClient() as client:
            scraper = BingScraper(client)
            results = await scraper.search("test", {})
            assert results == []
