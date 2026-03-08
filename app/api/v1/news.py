from fastapi import APIRouter, Depends, Request
from fastapi.params import Query

from app.dependencies import verify_api_key
from app.aggregator.aggregator import aggregate
from app.schemas.request import Freshness
from app.schemas.response import (
    NewsSearchResponse, NewsResult, QueryContext, MetaUrl, Thumbnail
)
from app.scrapers.base import RawResult

router = APIRouter()


def _raw_to_news_result(r: RawResult) -> NewsResult:
    meta = None
    try:
        meta = MetaUrl.from_url(r.url)
    except Exception:
        pass

    thumbnail = Thumbnail(src=r.thumbnail_src) if r.thumbnail_src else None

    return NewsResult(
        title=r.title,
        url=r.url,
        description=r.description,
        age=r.age,
        source=r.source_name,
        meta_url=meta,
        thumbnail=thumbnail,
    )


@router.get("/news/search", response_model=NewsSearchResponse)
async def news_search(
    request: Request,
    q: str = Query(..., description="Search query"),
    count: int = Query(default=10, ge=1, le=20),
    country: str = Query(default="us"),
    search_lang: str = Query(default="en"),
    freshness: Freshness | None = Query(default=None),
    _: str = Depends(verify_api_key),
) -> NewsSearchResponse:
    params = {
        "count": count,
        "country": country,
        "search_lang": search_lang,
        "freshness": freshness.value if freshness else None,
    }

    cache = request.app.state.cache
    cache_key = cache.make_key("news", {"q": q, **params})
    cached = await cache.get(cache_key)
    if cached is not None:
        return NewsSearchResponse(**cached)

    scrapers = request.app.state.scrapers_news
    raw_results = await aggregate(scrapers, q, params, limit=count)
    results = [_raw_to_news_result(r) for r in raw_results]

    response = NewsSearchResponse(
        query=QueryContext(original=q),
        results=results,
    )
    await cache.set(cache_key, response.model_dump())
    return response
