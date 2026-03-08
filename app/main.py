import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.cache.cache import AsyncCache
from app.config import settings
from app.dependencies import rate_limit_key
from app.scrapers.google import GoogleScraper
from app.scrapers.bing import BingScraper
from app.scrapers.duckduckgo import DuckDuckGoScraper
from app.scrapers.google_images import GoogleImagesScraper
from app.scrapers.bing_images import BingImagesScraper
from app.scrapers.bing_news import BingNewsScraper
from app.scrapers.bing_videos import BingVideosScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ws-api...")

    limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
    timeout = httpx.Timeout(settings.http_timeout)
    http_client = httpx.AsyncClient(limits=limits, timeout=timeout, http2=True)

    cache = AsyncCache(settings.cache_dir, ttl=settings.cache_ttl)

    app.state.http_client = http_client
    app.state.cache = cache

    # Initialize scrapers (share single HTTP client)
    app.state.scrapers_web = [
        GoogleScraper(http_client),
        BingScraper(http_client),
        DuckDuckGoScraper(http_client),
    ]
    app.state.scrapers_images = [
        BingImagesScraper(http_client),
        GoogleImagesScraper(http_client),
    ]
    app.state.scrapers_news = [
        BingNewsScraper(http_client),
    ]
    app.state.scrapers_videos = [
        BingVideosScraper(http_client),
    ]

    logger.info("ws-api ready")
    yield

    await http_client.aclose()
    cache.close()
    logger.info("ws-api shutdown complete")


limiter = Limiter(key_func=rate_limit_key, default_limits=[f"{settings.rate_limit}/minute"])


def create_app() -> FastAPI:
    app = FastAPI(
        title="Web Search API",
        description="Self-hosted search API compatible with Brave Search API schema",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    from app.api.v1.router import router
    app.include_router(router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
