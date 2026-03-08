import asyncio
import hashlib
import json
from typing import Any

import diskcache


class AsyncCache:
    def __init__(self, directory: str, ttl: int = 300) -> None:
        self._cache = diskcache.Cache(directory)
        self._ttl = ttl

    def _make_key(self, prefix: str, params: dict) -> str:
        serialized = json.dumps(params, sort_keys=True)
        digest = hashlib.sha256(serialized.encode()).hexdigest()[:16]
        return f"{prefix}:{digest}"

    async def get(self, key: str) -> Any | None:
        return await asyncio.to_thread(self._cache.get, key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expire = ttl if ttl is not None else self._ttl
        await asyncio.to_thread(self._cache.set, key, value, expire)

    def make_key(self, prefix: str, params: dict) -> str:
        return self._make_key(prefix, params)

    def close(self) -> None:
        self._cache.close()
