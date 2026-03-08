from pydantic import BaseModel
from urllib.parse import urlparse


class MetaUrl(BaseModel):
    scheme: str
    netloc: str
    hostname: str
    favicon: str
    path: str

    @classmethod
    def from_url(cls, url: str) -> "MetaUrl":
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return cls(
            scheme=parsed.scheme,
            netloc=parsed.netloc,
            hostname=hostname,
            favicon=f"https://favicons.githubusercontent.com/{hostname}",
            path=parsed.path,
        )


class Thumbnail(BaseModel):
    src: str
    width: int | None = None
    height: int | None = None


class WebResult(BaseModel):
    title: str
    url: str
    description: str
    age: str | None = None
    meta_url: MetaUrl | None = None
    thumbnail: Thumbnail | None = None
    extra_snippets: list[str] = []


class WebResults(BaseModel):
    type: str = "search"
    results: list[WebResult]


class QueryContext(BaseModel):
    original: str
    altered: str | None = None
    more_results_available: bool = True


class WebSearchResponse(BaseModel):
    type: str = "search"
    query: QueryContext
    web: WebResults


class ImageResult(BaseModel):
    title: str
    url: str
    thumbnail: Thumbnail | None = None
    image_url: str | None = None
    source: str | None = None
    meta_url: MetaUrl | None = None


class ImageResults(BaseModel):
    type: str = "images"
    results: list[ImageResult]


class ImageSearchResponse(BaseModel):
    type: str = "images"
    query: QueryContext
    results: list[ImageResult]


class NewsResult(BaseModel):
    title: str
    url: str
    description: str
    age: str | None = None
    source: str | None = None
    meta_url: MetaUrl | None = None
    thumbnail: Thumbnail | None = None


class NewsSearchResponse(BaseModel):
    type: str = "news"
    query: QueryContext
    results: list[NewsResult]


class VideoResult(BaseModel):
    title: str
    url: str
    description: str = ""
    duration: str | None = None
    thumbnail: Thumbnail | None = None
    source: str | None = None
    age: str | None = None
    meta_url: MetaUrl | None = None


class VideoSearchResponse(BaseModel):
    type: str = "videos"
    query: QueryContext
    results: list[VideoResult]


class SuggestResult(BaseModel):
    query: str
    is_entity: bool = False


class SuggestSearchResponse(BaseModel):
    type: str = "suggest"
    query: QueryContext
    results: list[SuggestResult]
