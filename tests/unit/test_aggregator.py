import pytest
from unittest.mock import AsyncMock, MagicMock

from app.aggregator.aggregator import aggregate, _normalize_url
from app.scrapers.base import RawResult, AbstractScraper


def make_result(url: str, title: str = "Title", engine: str = "test", description: str = "desc") -> RawResult:
    return RawResult(title=title, url=url, description=description, engine=engine)


def test_normalize_url_strips_trailing_slash():
    assert _normalize_url("https://example.com/path/") == "https://example.com/path"


def test_normalize_url_strips_fragment():
    assert _normalize_url("https://example.com/path#section") == "https://example.com/path"


def test_normalize_url_lowercases_host():
    assert _normalize_url("https://EXAMPLE.COM/path") == "https://example.com/path"


@pytest.mark.asyncio
async def test_aggregate_deduplicates_urls():
    scraper1 = MagicMock(spec=AbstractScraper)
    scraper1.search = AsyncMock(return_value=[
        make_result("https://example.com/page1", engine="google"),
        make_result("https://example.com/page2", engine="google"),
    ])
    scraper2 = MagicMock(spec=AbstractScraper)
    scraper2.search = AsyncMock(return_value=[
        make_result("https://example.com/page1/", engine="bing"),  # trailing slash dupe
        make_result("https://other.com/page3", engine="bing"),
    ])

    results = await aggregate([scraper1, scraper2], "test", {}, limit=10)

    urls = [r.url for r in results]
    assert len(urls) == len(set(_normalize_url(u) for u in urls))


@pytest.mark.asyncio
async def test_aggregate_ranks_by_frequency():
    scraper1 = MagicMock(spec=AbstractScraper)
    scraper1.search = AsyncMock(return_value=[
        make_result("https://best.com/page", engine="google"),
    ])
    scraper2 = MagicMock(spec=AbstractScraper)
    scraper2.search = AsyncMock(return_value=[
        make_result("https://best.com/page/", engine="bing"),  # same page
        make_result("https://only-bing.com/page", engine="bing"),
    ])

    results = await aggregate([scraper1, scraper2], "test", {}, limit=10)
    assert results[0].url in ("https://best.com/page", "https://best.com/page/")


@pytest.mark.asyncio
async def test_aggregate_handles_scraper_failures():
    scraper1 = MagicMock(spec=AbstractScraper)
    scraper1.search = AsyncMock(return_value=[
        make_result("https://example.com/page1", engine="working"),
    ])
    scraper2 = MagicMock(spec=AbstractScraper)
    scraper2.search = AsyncMock(return_value=[])  # empty = failed scraper

    results = await aggregate([scraper1, scraper2], "test", {}, limit=10)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_aggregate_respects_limit():
    scraper = MagicMock(spec=AbstractScraper)
    scraper.search = AsyncMock(return_value=[
        make_result(f"https://example.com/page{i}", engine="test") for i in range(20)
    ])

    results = await aggregate([scraper], "test", {}, limit=5)
    assert len(results) <= 5
