from fastapi import APIRouter, Depends, Request
from fastapi.params import Query

from app.dependencies import verify_api_key
from app.aggregator.aggregator import aggregate
from app.schemas.request import SafeSearch
from app.schemas.response import (
    ImageSearchResponse, ImageResult, QueryContext, MetaUrl, Thumbnail
)
from app.scrapers.base import RawResult

router = APIRouter()


def _raw_to_image_result(r: RawResult) -> ImageResult:
    meta = None
    try:
        meta = MetaUrl.from_url(r.url)
    except Exception:
        pass

    thumbnail = Thumbnail(src=r.thumbnail_src) if r.thumbnail_src else None

    return ImageResult(
        title=r.title,
        url=r.url,
        thumbnail=thumbnail,
        image_url=r.image_src,
        source=r.source_name,
        meta_url=meta,
    )


@router.get("/images/search", response_model=ImageSearchResponse)
async def images_search(
    request: Request,
    q: str = Query(..., description="Search query"),
    count: int = Query(default=10, ge=1, le=20),
    country: str = Query(default="us"),
    search_lang: str = Query(default="en"),
    safesearch: SafeSearch = Query(default=SafeSearch.moderate),
    size: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
) -> ImageSearchResponse:
    params = {
        "count": count,
        "country": country,
        "search_lang": search_lang,
        "safesearch": safesearch.value,
        "size": size,
    }

    cache = request.app.state.cache
    cache_key = cache.make_key("images", {"q": q, **params})
    cached = await cache.get(cache_key)
    if cached is not None:
        return ImageSearchResponse(**cached)

    scrapers = request.app.state.scrapers_images
    raw_results = await aggregate(scrapers, q, params, limit=count)
    results = [_raw_to_image_result(r) for r in raw_results]

    response = ImageSearchResponse(
        query=QueryContext(original=q),
        results=results,
    )
    await cache.set(cache_key, response.model_dump())
    return response
