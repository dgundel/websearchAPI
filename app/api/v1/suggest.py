import logging
from fastapi import APIRouter, Depends, Request
from fastapi.params import Query

from app.dependencies import verify_api_key
from app.schemas.response import SuggestSearchResponse, SuggestResult, QueryContext

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/suggest/search", response_model=SuggestSearchResponse)
async def suggest_search(
    request: Request,
    q: str = Query(..., description="Search query"),
    country: str = Query(default="us"),
    search_lang: str = Query(default="en"),
    _: str = Depends(verify_api_key),
) -> SuggestSearchResponse:
    """Fetch search suggestions from Google's autocomplete API."""
    client = request.app.state.http_client

    suggestions: list[SuggestResult] = []
    try:
        resp = await client.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "q": q, "hl": search_lang, "gl": country},
            headers={"Accept": "application/json"},
        )
        data = resp.json()
        for s in data[1]:
            suggestions.append(SuggestResult(query=s))
    except Exception as exc:
        logger.warning("[suggest] Google suggest failed: %s", exc)

    return SuggestSearchResponse(
        query=QueryContext(original=q),
        results=suggestions,
    )
