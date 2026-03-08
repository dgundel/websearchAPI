from fastapi import APIRouter, Depends, Request
from fastapi.params import Query

from app.dependencies import verify_api_key
from app.aggregator.aggregator import aggregate
from app.schemas.request import SafeSearch
from app.schemas.response import (
    WebSearchResponse, WebResults, WebResult, QueryContext, MetaUrl, Thumbnail
)
from app.scrapers.base import RawResult

router = APIRouter()


def _raw_to_web_result(r: RawResult) -> WebResult:
    meta = None
    try:
        meta = MetaUrl.from_url(r.url)
    except Exception:
        pass

    thumbnail = Thumbnail(src=r.thumbnail_src) if r.thumbnail_src else None

    return WebResult(
        title=r.title,
        url=r.url,
        description=r.description,
        age=r.age,
        meta_url=meta,
        thumbnail=thumbnail,
    )


@router.get("/web/search", response_model=WebSearchResponse)
async def web_search(
    request: Request,
    q: str = Query(..., description="Search query"),
    count: int = Query(default=10, ge=1, le=20),
    offset: int = Query(default=0, ge=0, le=9),
    country: str = Query(default="us"),
    search_lang: str = Query(default="en"),
    safesearch: SafeSearch = Query(default=SafeSearch.moderate),
    _: str = Depends(verify_api_key),
) -> WebSearchResponse:
    params = {
        "count": count,
        "offset": offset,
        "country": country,
        "search_lang": search_lang,
        "safesearch": safesearch.value,
    }

    # Check cache
    cache = request.app.state.cache
    cache_key = cache.make_key("web", {"q": q, **params})
    cached = await cache.get(cache_key)
    if cached is not None:
        return WebSearchResponse(**cached)

    # Scrape
    scrapers = request.app.state.scrapers_web
    raw_results = await aggregate(scrapers, q, params, limit=count)

    web_results = [_raw_to_web_result(r) for r in raw_results]

    response = WebSearchResponse(
        query=QueryContext(original=q),
        web=WebResults(results=web_results),
    )

    await cache.set(cache_key, response.model_dump())
    return response
