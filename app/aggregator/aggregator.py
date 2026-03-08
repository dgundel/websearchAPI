import asyncio
from urllib.parse import urlparse, urlunparse

from app.scrapers.base import AbstractScraper, RawResult


def _normalize_url(url: str) -> str:
    """Normalize URL for deduplication: lowercase host, strip trailing slash and fragment."""
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            parsed.query,
            "",  # strip fragment
        ))
        return normalized
    except Exception:
        return url


async def aggregate(
    scrapers: list[AbstractScraper],
    query: str,
    params: dict,
    limit: int = 20,
) -> list[RawResult]:
    """Run scrapers in parallel, dedup by URL, rank by frequency + position."""
    all_results: list[list[RawResult]] = await asyncio.gather(
        *[s.search(query, params) for s in scrapers]
    )

    # Track: url -> (best RawResult, occurrence count, position score)
    seen: dict[str, tuple[RawResult, int, float]] = {}

    for engine_results in all_results:
        for idx, result in enumerate(engine_results):
            key = _normalize_url(result.url)
            position_score = 1.0 / (idx + 1)

            if key in seen:
                existing, count, score = seen[key]
                # Keep result with better description
                best = existing if len(existing.description) >= len(result.description) else result
                seen[key] = (best, count + 1, score + position_score)
            else:
                seen[key] = (result, 1, position_score)

    # Sort: primary = occurrence count (desc), secondary = position score (desc)
    sorted_items = sorted(
        seen.values(),
        key=lambda x: (x[1], x[2]),
        reverse=True,
    )

    return [item[0] for item in sorted_items[:limit]]
