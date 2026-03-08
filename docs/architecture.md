# Architecture

## Overview

ws-api ist eine FastAPI-Anwendung, die Suchergebnisse von mehreren Engines parallel scrapt, aggregiert und im Brave Search API-Format zurückgibt.

```
Client
  │  X-API-Key Header
  ▼
FastAPI App (app/main.py)
  │  Auth (dependencies.py)
  │  Rate Limiting (slowapi)
  ▼
API Router (api/v1/)
  │
  ├── web.py      ──▶  Aggregator ──▶ [GoogleScraper, BingScraper, DDGScraper]
  ├── images.py   ──▶  Aggregator ──▶ [BingImagesScraper, GoogleImagesScraper]
  ├── news.py     ──▶  Aggregator ──▶ [BingNewsScraper]
  └── suggest.py  ──▶  httpx direkt (Google Autocomplete API)
         │
         │  AsyncCache (diskcache)
         └── Cache-Hit ──▶ sofort zurück
```

---

## Komponenten

### App Factory & Lifespan (`app/main.py`)

Die App wird über `create_app()` erzeugt. Im `lifespan`-Contextmanager werden beim Start alle langlebigen Ressourcen initialisiert:

```python
@asynccontextmanager
async def lifespan(app):
    app.state.http_client = httpx.AsyncClient(http2=True, ...)
    app.state.cache = AsyncCache(settings.cache_dir)
    app.state.scrapers_web    = [GoogleScraper(client), BingScraper(client), DDGScraper(client)]
    app.state.scrapers_images = [BingImagesScraper(client), GoogleImagesScraper(client)]
    app.state.scrapers_news   = [BingNewsScraper(client)]
    yield
    await http_client.aclose()
    cache.close()
```

**Wichtig:** Alle Scraper teilen sich einen einzigen `httpx.AsyncClient`. Das ermöglicht Connection Pooling über alle parallelen Requests hinweg.

---

### Scraper Pattern (`app/scrapers/`)

Jeder Scraper folgt dem gleichen Muster, adaptiert von SearXNG's Engine-Architektur:

```
AbstractScraper (base.py)
  ├── request(query, params) → dict    # baut HTTP-Spec, kein I/O
  ├── parse(response) → list[RawResult]  # parst HTML/JSON, kein I/O
  └── search(query, params) → list[RawResult]  # orchestriert, mit Error-Containment
```

Die Trennung von `request()` und `parse()` macht Unit-Tests trivial — keine I/O, keine Mocks nötig für die Kernlogik.

#### Spezialfall DuckDuckGo

DDG benötigt ein VQD-Token, das pro Query frisch gefetcht werden muss. `DuckDuckGoScraper` überschreibt deshalb `search()` und fetcht das Token vorab:

```python
async def search(self, query, params):
    vqd = await self._fetch_vqd(query)
    if not vqd:
        return []
    # ... normaler Request mit VQD im Body
```

#### RawResult — gemeinsames internes Format

```python
@dataclass
class RawResult:
    title: str
    url: str
    description: str
    engine: str
    age: str | None = None
    thumbnail_src: str | None = None
    image_src: str | None = None
    source_name: str | None = None
```

Alle Scraper geben `RawResult`-Objekte zurück. Die Konvertierung in das Brave-kompatible Response-Schema findet erst im jeweiligen API-Handler statt.

---

### Aggregator (`app/aggregator/aggregator.py`)

```python
async def aggregate(scrapers, query, params, limit) -> list[RawResult]:
    # 1. Alle Scraper parallel ausführen
    all_results = await asyncio.gather(*[s.search(query, params) for s in scrapers])

    # 2. URL-Deduplication (normalisiert: lowercase, kein trailing slash, kein Fragment)
    # 3. Ranking: occurrence_count DESC, position_score DESC
    # 4. Limit anwenden
```

**Ranking-Logik:**
- Erscheint eine URL bei mehreren Engines → höherer `occurrence_count`
- Tiebreaker: `position_score = sum(1 / (idx+1))` — frühe Positionen zählen mehr
- Result mit besserer `description` gewinnt bei Duplikaten

**Error Containment:** Scheitert ein Scraper, gibt er `[]` zurück (loggt eine Warning). `asyncio.gather` läuft trotzdem durch.

---

### Cache (`app/cache/cache.py`)

```python
class AsyncCache:
    def __init__(self, directory, ttl=300):
        self._cache = diskcache.Cache(directory)

    async def get(self, key): ...      # via asyncio.to_thread
    async def set(self, key, value, ttl): ...
```

[diskcache](https://github.com/grantjenks/python-diskcache) verwendet File-Locking und ist damit inherent process-safe. Mehrere uvicorn-Worker können gleichzeitig auf den Cache zugreifen — kein Redis-Daemon nötig.

Cache-Keys werden als SHA-256 über die serialisierten Query-Parameter gebildet:
```python
def make_key(self, prefix, params) -> str:
    serialized = json.dumps(params, sort_keys=True)
    return f"{prefix}:{sha256(serialized)[:16]}"
```

---

### Auth & Rate Limiting (`app/dependencies.py`)

```python
async def verify_api_key(x_api_key = Header(alias="X-API-Key")) -> str:
    if not settings.api_keys:
        return "dev"  # Auth deaktiviert
    if x_api_key not in settings.api_keys:
        raise HTTPException(401)
```

Rate Limiting über [slowapi](https://github.com/laurentS/slowapi) (Starlette-Middleware):
- Key-Funktion: API-Key → `key:xyz`, sonst Client-IP → `ip:1.2.3.4`
- Default: 60 Requests/Minute, konfigurierbar via `RATE_LIMIT`

---

### Response Schema

Das Schema ist kompatibel mit der [Brave Search API](https://api.search.brave.com/app/documentation/web-search/get-started):

```
WebSearchResponse
  ├── type: "search"
  ├── query: QueryContext (original, altered, more_results_available)
  └── web: WebResults
        └── results: list[WebResult]
              ├── title, url, description, age
              ├── meta_url: MetaUrl (scheme, netloc, hostname, favicon, path)
              ├── thumbnail: Thumbnail (src, width, height)
              └── extra_snippets: list[str]
```

---

## Datenfluss (Web Search)

```
GET /v1/web/search?q=fastapi&count=5
  │
  ├── verify_api_key()              # 401 wenn Key ungültig
  │
  ├── cache.get(cache_key)          # Cache-Hit → sofort Response
  │
  ├── aggregate(scrapers_web, ...)
  │     ├── GoogleScraper.search()  ─┐
  │     ├── BingScraper.search()    ─┤ asyncio.gather (parallel)
  │     └── DDGScraper.search()    ─┘
  │           │
  │           └── URL-Dedup + Ranking
  │
  ├── list[RawResult] → list[WebResult]
  │
  ├── cache.set(cache_key, response)
  │
  └── WebSearchResponse (JSON)
```

---

## Bekannte Limitierungen & Fallstricke

| Problem | Ursache | Lösung |
|---|---|---|
| Google CAPTCHA | Zu viele Requests von einer IP | `sorry/index` im Content detektieren → `[]` zurückgeben; UA rotieren |
| DDG VQD-Token | Muss per Query frisch gefetcht werden | `_fetch_vqd()` vor jedem Search-Request |
| Bing `ck/a?` Redirects | Bing encoded URLs (relativ u. absolut) als `a1` + base64url | `_decode_bing_url()` prüft auf `/ck/a` in der URL und dekodiert den `u`-Parameter |
| Bing Images `m`-Attribut | Regex matcht nicht zuverlässig gegen geparsten HTML | lxml `cssselect("a.iusc[m]")` + `json.loads(el.get("m"))` statt Regex |
| lxml encoding | `resp.text` kann encoding-Fehler erzeugen | `resp.content` (bytes) an `html.fromstring()` übergeben |
| Veraltete XPath/CSS-Selektoren | Google/Bing/DDG ändern ihr HTML regelmäßig | Scraper sind in isolierten Files — nur 1 File pro Breakage |

---

## Einen neuen Scraper hinzufügen

1. Neue Datei `app/scrapers/mysearch.py`, Klasse erbt von `AbstractScraper`
2. `request()` und `parse()` implementieren
3. Scraper in `app/main.py` `lifespan` dem passenden `scrapers_*`-Array hinzufügen
4. Unit-Tests in `tests/unit/test_mysearch_scraper.py`

```python
class MySearchScraper(AbstractScraper):
    name = "mysearch"

    def request(self, query: str, params: dict) -> dict:
        return {
            "method": "GET",
            "url": f"https://mysearch.example.com/search?q={query}",
            "headers": {"User-Agent": "Mozilla/5.0 ..."},
        }

    def parse(self, response: httpx.Response) -> list[RawResult]:
        tree = html.fromstring(response.content)
        results = []
        for el in tree.cssselect("div.result"):
            ...
        return results
```
