from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_keys: list[str] = []
    cache_dir: str = "/tmp/ws_api_cache"
    cache_ttl: int = 300
    rate_limit: int = 60
    http_timeout: float = 10.0

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        return v


settings = Settings()
