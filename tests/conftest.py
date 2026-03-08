import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture(autouse=True)
def override_api_keys(monkeypatch):
    """Ensure API_KEYS contains 'test' for all tests."""
    monkeypatch.setattr(settings, "api_keys", ["test"])


@pytest.fixture
def test_client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test"}


@pytest.fixture
def mock_http():
    with respx.mock(assert_all_called=False) as mock:
        yield mock
