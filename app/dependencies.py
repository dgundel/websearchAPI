from fastapi import Header, HTTPException, Request, status

from app.config import settings


async def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """Verify API key from X-API-Key header. Disabled when API_KEYS is empty."""
    if not settings.api_keys:
        # Auth disabled in dev mode
        return "dev"
    if x_api_key is None or x_api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return x_api_key


def rate_limit_key(request: Request) -> str:
    """Key function for slowapi rate limiting: use API key or client IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    return f"ip:{request.client.host}"
