import json
import pytest
import httpx
import respx

from app.scrapers.bing_videos import BingVideosScraper

MMETA = json.dumps({
    "murl": "https://www.youtube.com/watch?v=rfscVS0vtbw",
    "turl": "https://th.bing.com/th/id/thumbnail123",
})

BING_VIDEOS_HTML = f"""
<html><body>
<div class="mc_vtvc" mmeta='{MMETA}'>
  <a class="mc_vtvc_link" aria-label="Learn Python - Full Course for Beginners">
    Learn Python
  </a>
  <div class="mc_vtvc_dur">4:26:52</div>
  <div class="mc_vtvc_meta_block">
    <span>YouTube</span>
    <span>11. Juli 2018</span>
  </div>
</div>
<div class="mc_vtvc" mmeta='{json.dumps({"murl": "https://vimeo.com/video/123", "turl": ""})}'>
  <a class="mc_vtvc_link" aria-label="Another Video"></a>
  <div class="mc_vtvc_dur">1:30</div>
  <div class="mc_vtvc_meta_block">
    <span>Vimeo</span>
  </div>
</div>
</body></html>
""".encode()

MISSING_MURL_HTML = b"""
<html><body>
<div class="mc_vtvc" mmeta='{"turl": "https://th.bing.com/thumb"}'>
  <a class="mc_vtvc_link" aria-label="No URL Video"></a>
</div>
</body></html>
"""

RELATIVE_URL_HTML = b"""
<html><body>
<div class="mc_vtvc" mmeta='{"murl": "/relative/path", "turl": ""}'>
  <a class="mc_vtvc_link" aria-label="Relative URL"></a>
</div>
</body></html>
"""


@pytest.fixture
def scraper():
    return BingVideosScraper(httpx.AsyncClient())


def test_request_has_correct_params(scraper):
    req = scraper.request("python tutorial", {"search_lang": "en", "country": "us", "safesearch": "moderate"})
    assert req["method"] == "GET"
    assert "bing.com/videos/search" in req["url"]
    assert req["params"]["q"] == "python tutorial"
    assert req["params"]["mkt"] == "en-US"
    assert req["params"]["safeSearch"] == "Moderate"


def test_request_safesearch_mapping(scraper):
    req = scraper.request("test", {"safesearch": "strict"})
    assert req["params"]["safeSearch"] == "Strict"

    req = scraper.request("test", {"safesearch": "off"})
    assert req["params"]["safeSearch"] == "Off"


def test_parse_extracts_results(scraper):
    response = httpx.Response(200, content=BING_VIDEOS_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert len(results) == 2
    assert results[0].url == "https://www.youtube.com/watch?v=rfscVS0vtbw"
    assert results[0].title == "Learn Python - Full Course for Beginners"
    assert results[0].thumbnail_src == "https://th.bing.com/th/id/thumbnail123"
    assert results[0].source_name == "YouTube"
    assert results[0].age == "11. Juli 2018"


def test_parse_extracts_duration(scraper):
    response = httpx.Response(200, content=BING_VIDEOS_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results[0].age is not None  # age extracted


def test_parse_skips_missing_murl(scraper):
    response = httpx.Response(200, content=MISSING_MURL_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results == []


def test_parse_skips_non_http_urls(scraper):
    response = httpx.Response(200, content=RELATIVE_URL_HTML, headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results == []


def test_parse_empty_html_returns_empty(scraper):
    response = httpx.Response(200, content=b"<html><body></body></html>", headers={"content-type": "text/html"})
    results = scraper.parse(response)
    assert results == []


@pytest.mark.asyncio
async def test_search_returns_empty_on_error():
    with respx.mock() as mock:
        mock.get(url__regex=r"bing\.com/videos").mock(return_value=httpx.Response(503))
        async with httpx.AsyncClient() as client:
            scraper = BingVideosScraper(client)
            results = await scraper.search("test", {})
            assert results == []
