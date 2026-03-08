from fastapi import APIRouter, Depends, Request
from fastapi.params import Query

from app.dependencies import verify_api_key
from app.aggregator.aggregator import aggregate
from app.schemas.response import (
    VideoSearchResponse, VideoResult, QueryContext, MetaUrl, Thumbnail
)
from app.scrapers.base import RawResult

router = APIRouter()


def _raw_to_video_result(r: RawResult) -> VideoResult:
    meta = None
    try:
        meta = MetaUrl.from_url(r.url)
    except Exception:
        pass

    thumbnail = Thumbnail(src=r.thumbnail_src) if r.thumbnail_src else None

    return VideoResult(
        title=r.title,
        url=r.url,
        description=r.description,
        age=r.age,
        source=r.source_name,
        thumbnail=thumbnail,
        meta_url=meta,
    )


@router.get("/videos/search", response_model=VideoSearchResponse)
async def videos_search(
    request: Request,
    q: str = Query(..., description="Search query"),
    count: int = Query(default=10, ge=1, le=20),
    country: str = Query(default="us"),
    search_lang: str = Query(default="en"),
    safesearch: str = Query(default="moderate"),
    _: str = Depends(verify_api_key),
) -> VideoSearchResponse:
    params = {
        "count": count,
        "country": country,
        "search_lang": search_lang,
        "safesearch": safesearch,
    }

    cache = request.app.state.cache
    cache_key = cache.make_key("videos", {"q": q, **params})
    cached = await cache.get(cache_key)
    if cached is not None:
        return VideoSearchResponse(**cached)

    scrapers = request.app.state.scrapers_videos
    raw_results = await aggregate(scrapers, q, params, limit=count)
    results = [_raw_to_video_result(r) for r in raw_results]

    response = VideoSearchResponse(
        query=QueryContext(original=q),
        results=results,
    )
    await cache.set(cache_key, response.model_dump())
    return response
