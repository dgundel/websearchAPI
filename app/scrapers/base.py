from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RawResult:
    title: str
    url: str
    description: str
    engine: str
    age: str | None = None
    thumbnail_src: str | None = None
    image_src: str | None = None
    source_name: str | None = None
    duration: str | None = None


class AbstractScraper(ABC):
    name: str = "base"

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self.client = http_client

    @abstractmethod
    def request(self, query: str, params: dict) -> dict:
        """Build HTTP request spec. Returns kwargs for httpx request."""

    @abstractmethod
    def parse(self, response: httpx.Response) -> list[RawResult]:
        """Parse HTTP response into RawResult list. No I/O."""

    async def search(self, query: str, params: dict) -> list[RawResult]:
        """Orchestrate request + parse with error containment."""
        try:
            req_kwargs = self.request(query, params)
            response = await self.client.request(**req_kwargs)
            response.raise_for_status()
            return self.parse(response)
        except Exception as exc:
            logger.warning("[%s] search failed: %s", self.name, exc)
            return []
