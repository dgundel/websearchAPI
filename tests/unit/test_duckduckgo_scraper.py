import pytest
import httpx
import respx

from app.scrapers.duckduckgo import DuckDuckGoScraper

DDG_VQD_HTML = b"""
<html><body>
<script>vqd="1234-5678"</script>
</body></html>
"""

DDG_RESULTS_JSON = b"""
{
  "results": [
    {"t": "DDG Result One", "u": "https://example.com/ddg1", "a": "Description one", "date": null},
    {"t": "DDG Result Two", "u": "https://example.org/ddg2", "a": "Description two", "date": "2024-01-01"}
  ]
}
"""


@pytest.fixture
def scraper():
    return DuckDuckGoScraper(httpx.AsyncClient())


def test_parse_extracts_results(scraper):
    response = httpx.Response(200, content=DDG_RESULTS_JSON, headers={"content-type": "application/json"})
    results = scraper.parse(response)
    assert len(results) == 2
    assert results[0].title == "DDG Result One"
    assert results[0].url == "https://example.com/ddg1"
    assert results[0].engine == "duckduckgo"


def test_parse_extracts_age(scraper):
    response = httpx.Response(200, content=DDG_RESULTS_JSON, headers={"content-type": "application/json"})
    results = scraper.parse(response)
    assert results[1].age == "2024-01-01"


def test_parse_skips_invalid_urls(scraper):
    json_data = b'{"results": [{"t": "Bad", "u": "/relative/path", "a": "desc"}]}'
    response = httpx.Response(200, content=json_data, headers={"content-type": "application/json"})
    results = scraper.parse(response)
    assert results == []


@pytest.mark.asyncio
async def test_search_without_vqd_returns_empty():
    with respx.mock() as mock:
        mock.get(url__regex=r"duckduckgo\.com").mock(return_value=httpx.Response(200, content=b"<html></html>"))
        async with httpx.AsyncClient() as client:
            scraper = DuckDuckGoScraper(client)
            results = await scraper.search("test", {})
            assert results == []
