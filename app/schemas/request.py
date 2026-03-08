from enum import Enum
from pydantic import BaseModel, Field


class SafeSearch(str, Enum):
    off = "off"
    moderate = "moderate"
    strict = "strict"


class Freshness(str, Enum):
    pd = "pd"   # past day
    pw = "pw"   # past week
    pm = "pm"   # past month
    py = "py"   # past year


class WebSearchParams(BaseModel):
    q: str
    count: int = Field(default=10, ge=1, le=20)
    offset: int = Field(default=0, ge=0, le=9)
    country: str = "us"
    search_lang: str = "en"
    safesearch: SafeSearch = SafeSearch.moderate


class ImageSearchParams(BaseModel):
    q: str
    count: int = Field(default=10, ge=1, le=20)
    country: str = "us"
    search_lang: str = "en"
    safesearch: SafeSearch = SafeSearch.moderate
    size: str | None = None  # small, medium, large, wallpaper


class NewsSearchParams(BaseModel):
    q: str
    count: int = Field(default=10, ge=1, le=20)
    country: str = "us"
    search_lang: str = "en"
    freshness: Freshness | None = None


class SuggestSearchParams(BaseModel):
    q: str
    country: str = "us"
    search_lang: str = "en"
