# websearchAPI

![CI](https://github.com/dgundel/websearchAPI/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Self-hosted web search API, compatible with the [Brave Search API](https://api.search.brave.com/app/documentation/web-search/get-started) schema. Aggregates results from Google, Bing and DuckDuckGo via async HTML scraping — no third-party search API keys required.

```
GET /v1/web/search?q=python+fastapi&count=5
X-API-Key: your-key
```

```json
{
  "type": "search",
  "query": { "original": "python fastapi" },
  "web": {
    "results": [
      {
        "title": "FastAPI - Modern Python Web Framework",
        "url": "https://fastapi.tiangolo.com/",
        "description": "FastAPI framework, high performance, easy to learn...",
        "age": "3 days ago",
        "meta_url": { "scheme": "https", "hostname": "fastapi.tiangolo.com", ... }
      }
    ]
  }
}
```

---

## Features

- **Brave-compatible schema** — drop-in replacement for clients using the Brave Search API
- **Multi-engine aggregation** — Google, Bing, DuckDuckGo scraped in parallel
- **Smart ranking** — results appearing in more engines rank higher; tie-broken by position
- **URL deduplication** — normalized comparison strips trailing slashes, fragments and case
- **File-based cache** — [diskcache](https://github.com/grantjenks/python-diskcache) with configurable TTL; process-safe, no Redis needed
- **Rate limiting** — per API key via [slowapi](https://github.com/laurentS/slowapi)
- **API key auth** — `X-API-Key` header; leave `API_KEYS` empty for dev mode (no auth)
- **HTTP/2** — shared `httpx.AsyncClient` with connection pooling across all scrapers

---

## Quickstart

```bash
# Clone / enter project
cd /home/dg/ws_api

# Install
pip3 install --user -e ".[dev]"

# Configure (copy and edit)
cp .env.example .env

# Run
python3 -m uvicorn app.main:app --reload

# Smoke test (auth disabled when API_KEYS is empty)
curl "http://localhost:8000/v1/web/search?q=hello+world"

# With auth key
curl -H "X-API-Key: dev" "http://localhost:8000/v1/web/search?q=hello+world&count=5"
```

Interactive API docs: `http://localhost:8000/docs`

---

## Configuration

All settings are read from environment variables or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `API_KEYS` | *(empty)* | Comma-separated keys. Empty = auth disabled (dev mode) |
| `CACHE_DIR` | `/tmp/ws_api_cache` | diskcache directory |
| `CACHE_TTL` | `300` | Cache TTL in seconds |
| `RATE_LIMIT` | `60` | Requests per minute per key/IP |
| `HTTP_TIMEOUT` | `10.0` | HTTP client timeout in seconds |

```bash
# .env
API_KEYS=secret1,secret2
CACHE_TTL=600
RATE_LIMIT=30
```

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/web/search` | Web search (Google + Bing + DuckDuckGo) |
| `GET` | `/v1/images/search` | Image search (Bing Images + Google Images fallback) |
| `GET` | `/v1/news/search` | News search (Bing News) |
| `GET` | `/v1/videos/search` | Video search (Bing Videos) |
| `GET` | `/v1/suggest/search` | Autocomplete suggestions (Google) |
| `GET` | `/health` | Health check |

Full parameter reference: [docs/api-reference.md](docs/api-reference.md)

---

## Development

```bash
# Run tests
python3 -m pytest tests/ -v

# Lint
python3 -m ruff check app/ tests/

# Format
python3 -m ruff format app/ tests/
```

See [docs/architecture.md](docs/architecture.md) for internals, scraper patterns and extension guide.

---

## License

MIT
