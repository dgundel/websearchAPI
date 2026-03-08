import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.scrapers.base import RawResult

AUTH = {"X-API-Key": "test"}


@pytest.fixture
def mock_scrapers_web():
    """Patch app.state.scrapers_web with a mock."""
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[
        RawResult(
            title="Test Result",
            url="https://example.com/test",
            description="A test description",
            engine="google",
        )
    ])
    return [mock]


def test_health_endpoint():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_web_search_requires_auth():
    with TestClient(app) as client:
        resp = client.get("/v1/web/search?q=test")
        assert resp.status_code == 401


def test_web_search_returns_response(mock_scrapers_web):
    with TestClient(app) as client:
        client.app.state.scrapers_web = mock_scrapers_web
        resp = client.get("/v1/web/search?q=python+fastapi&count=5", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "search"
        assert "web" in data
        assert "query" in data
        assert data["query"]["original"] == "python fastapi"


def test_web_search_response_schema(mock_scrapers_web):
    with TestClient(app) as client:
        client.app.state.scrapers_web = mock_scrapers_web
        resp = client.get("/v1/web/search?q=test", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        results = data["web"]["results"]
        if results:
            r = results[0]
            assert "title" in r
            assert "url" in r
            assert "description" in r


def test_images_search_requires_auth():
    with TestClient(app) as client:
        resp = client.get("/v1/images/search?q=cats")
        assert resp.status_code == 401


def test_news_search_requires_auth():
    with TestClient(app) as client:
        resp = client.get("/v1/news/search?q=news")
        assert resp.status_code == 401


def test_suggest_search_requires_auth():
    with TestClient(app) as client:
        resp = client.get("/v1/suggest/search?q=pyt")
        assert resp.status_code == 401


def test_web_search_invalid_count():
    with TestClient(app) as client:
        resp = client.get("/v1/web/search?q=test&count=100", headers=AUTH)
        assert resp.status_code == 422


def test_web_search_invalid_offset():
    with TestClient(app) as client:
        resp = client.get("/v1/web/search?q=test&offset=99", headers=AUTH)
        assert resp.status_code == 422
