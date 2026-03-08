import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.scrapers.base import RawResult

AUTH = {"X-API-Key": "test"}


@pytest.fixture
def mock_scrapers_videos():
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[
        RawResult(
            title="Learn Python - Full Course",
            url="https://www.youtube.com/watch?v=rfscVS0vtbw",
            description="",
            engine="bing_videos",
            thumbnail_src="https://th.bing.com/th/id/thumb123",
            source_name="YouTube",
            age="11. Juli 2018",
        )
    ])
    return [mock]


def test_videos_search_requires_auth():
    with TestClient(app) as client:
        resp = client.get("/v1/videos/search?q=python")
        assert resp.status_code == 401


def test_videos_search_returns_response(mock_scrapers_videos):
    with TestClient(app) as client:
        client.app.state.scrapers_videos = mock_scrapers_videos
        resp = client.get("/v1/videos/search?q=python+tutorial&count=5", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "videos"
        assert "results" in data
        assert data["query"]["original"] == "python tutorial"


def test_videos_search_response_schema(mock_scrapers_videos):
    with TestClient(app) as client:
        client.app.state.scrapers_videos = mock_scrapers_videos
        resp = client.get("/v1/videos/search?q=test", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        results = data["results"]
        assert len(results) == 1
        r = results[0]
        assert r["title"] == "Learn Python - Full Course"
        assert r["url"] == "https://www.youtube.com/watch?v=rfscVS0vtbw"
        assert r["source"] == "YouTube"
        assert r["age"] == "11. Juli 2018"
        assert r["thumbnail"]["src"] == "https://th.bing.com/th/id/thumb123"


def test_videos_search_count_bound_lower():
    with TestClient(app) as client:
        resp = client.get("/v1/videos/search?q=test&count=0", headers=AUTH)
        assert resp.status_code == 422


def test_videos_search_count_bound_upper():
    with TestClient(app) as client:
        resp = client.get("/v1/videos/search?q=test&count=21", headers=AUTH)
        assert resp.status_code == 422


def test_videos_search_empty_results():
    with TestClient(app) as client:
        empty_mock = MagicMock()
        empty_mock.search = AsyncMock(return_value=[])
        client.app.state.scrapers_videos = [empty_mock]
        resp = client.get("/v1/videos/search?q=xyzzy12345", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
