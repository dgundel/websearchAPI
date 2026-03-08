# API Reference

Base URL: `http://localhost:8000`

## Authentifizierung

Alle Endpoints erfordern einen API-Key im Header:

```
X-API-Key: your-key
```

Wenn `API_KEYS` in der Konfiguration leer ist, ist Auth deaktiviert (Dev-Modus).

Fehler bei ungültigem Key:
```json
{ "detail": "Invalid or missing X-API-Key header" }
```
HTTP Status: `401 Unauthorized`

---

## GET /v1/web/search

Web-Suche über Google, Bing und DuckDuckGo. Ergebnisse werden aggregiert und nach Häufigkeit + Position gerankt.

### Parameter

| Name | Typ | Default | Beschreibung |
|---|---|---|---|
| `q` | string | **required** | Suchanfrage |
| `count` | integer | `10` | Anzahl Ergebnisse (1–20) |
| `offset` | integer | `0` | Ergebnis-Offset für Paginierung (0–9) |
| `country` | string | `us` | Ländercode (ISO 3166-1 alpha-2) |
| `search_lang` | string | `en` | Sprachcode (ISO 639-1) |
| `safesearch` | string | `moderate` | `off`, `moderate` oder `strict` |

### Beispiel

```bash
curl -H "X-API-Key: dev" \
  "http://localhost:8000/v1/web/search?q=python+asyncio&count=5&country=de&search_lang=de"
```

### Response

```json
{
  "type": "search",
  "query": {
    "original": "python asyncio",
    "altered": null,
    "more_results_available": true
  },
  "web": {
    "type": "search",
    "results": [
      {
        "title": "asyncio — Asynchronous I/O — Python Documentation",
        "url": "https://docs.python.org/3/library/asyncio.html",
        "description": "asyncio is a library to write concurrent code using the async/await syntax.",
        "age": "2 days ago",
        "meta_url": {
          "scheme": "https",
          "netloc": "docs.python.org",
          "hostname": "docs.python.org",
          "favicon": "https://favicons.githubusercontent.com/docs.python.org",
          "path": "/3/library/asyncio.html"
        },
        "thumbnail": null,
        "extra_snippets": []
      }
    ]
  }
}
```

---

## GET /v1/images/search

Bildsuche über Bing Images (primär) und Google Images (Fallback).

### Parameter

| Name | Typ | Default | Beschreibung |
|---|---|---|---|
| `q` | string | **required** | Suchanfrage |
| `count` | integer | `10` | Anzahl Ergebnisse (1–20) |
| `country` | string | `us` | Ländercode |
| `search_lang` | string | `en` | Sprachcode |
| `safesearch` | string | `moderate` | `off`, `moderate` oder `strict` |
| `size` | string | `null` | `small`, `medium`, `large` oder `wallpaper` |

### Beispiel

```bash
curl -H "X-API-Key: dev" \
  "http://localhost:8000/v1/images/search?q=golden+gate+bridge&size=large&count=5"
```

### Response

```json
{
  "type": "images",
  "query": { "original": "golden gate bridge" },
  "results": [
    {
      "title": "Golden Gate Bridge at Sunset",
      "url": "https://example.com/golden-gate/",
      "thumbnail": { "src": "https://ts1.mm.bing.net/th?id=OIP...." },
      "image_url": "https://example.com/images/golden-gate.jpg",
      "source": null,
      "meta_url": { ... }
    }
  ]
}
```

---

## GET /v1/news/search

Nachrichtensuche über Bing News. Liefert direkte Original-URLs (keine Bing-Weiterleitungen).

### Parameter

| Name | Typ | Default | Beschreibung |
|---|---|---|---|
| `q` | string | **required** | Suchanfrage |
| `count` | integer | `10` | Anzahl Ergebnisse (1–20) |
| `country` | string | `us` | Ländercode |
| `search_lang` | string | `en` | Sprachcode |
| `freshness` | string | `null` | `pd` (Tag), `pw` (Woche), `pm` (Monat), `py` (Jahr) |

### Beispiel

```bash
curl -H "X-API-Key: dev" \
  "http://localhost:8000/v1/news/search?q=artificial+intelligence&freshness=pw"
```

### Response

```json
{
  "type": "news",
  "query": { "original": "artificial intelligence" },
  "results": [
    {
      "title": "OpenAI releases new model",
      "url": "https://techcrunch.com/...",
      "description": "OpenAI today announced...",
      "age": "3 hours ago",
      "source": "TechCrunch",
      "meta_url": { ... },
      "thumbnail": null
    }
  ]
}
```

---

## GET /v1/videos/search

Videosuche über Bing Videos. Liefert direkte Video-URLs (YouTube, Vimeo, etc.) mit Thumbnail, Dauer und Quelle.

### Parameter

| Name | Typ | Default | Beschreibung |
|---|---|---|---|
| `q` | string | **required** | Suchanfrage |
| `count` | integer | `10` | Anzahl Ergebnisse (1–20) |
| `country` | string | `us` | Ländercode |
| `search_lang` | string | `en` | Sprachcode |
| `safesearch` | string | `moderate` | `off`, `moderate` oder `strict` |

### Beispiel

```bash
curl -H "X-API-Key: dev" \
  "http://localhost:8000/v1/videos/search?q=python+tutorial&count=5"
```

### Response

```json
{
  "type": "videos",
  "query": { "original": "python tutorial" },
  "results": [
    {
      "title": "Learn Python - Full Course for Beginners",
      "url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
      "description": "",
      "duration": "4:26:52",
      "thumbnail": { "src": "https://th.bing.com/th/id/..." },
      "source": "YouTube",
      "age": "11. Juli 2018",
      "meta_url": { "scheme": "https", "hostname": "youtube.com", ... }
    }
  ]
}
```

---

## GET /v1/suggest/search

Autovervollständigungs-Vorschläge von Google.

### Parameter

| Name | Typ | Default | Beschreibung |
|---|---|---|---|
| `q` | string | **required** | Teilanfrage |
| `country` | string | `us` | Ländercode |
| `search_lang` | string | `en` | Sprachcode |

### Beispiel

```bash
curl -H "X-API-Key: dev" \
  "http://localhost:8000/v1/suggest/search?q=python+fast"
```

### Response

```json
{
  "type": "suggest",
  "query": { "original": "python fast" },
  "results": [
    { "query": "python fastapi", "is_entity": false },
    { "query": "python fastest sort", "is_entity": false },
    { "query": "python faster than java", "is_entity": false }
  ]
}
```

---

## GET /health

Health-Check Endpoint, keine Auth erforderlich.

```bash
curl http://localhost:8000/health
```

```json
{ "status": "ok" }
```

---

## Fehler-Codes

| HTTP Status | Bedeutung |
|---|---|
| `200` | Erfolg |
| `401` | Fehlender oder ungültiger `X-API-Key` |
| `422` | Ungültige Query-Parameter (z.B. `count=999`) |
| `429` | Rate Limit überschritten |
| `500` | Interner Fehler |

---

## Paginierung

Web-Suche unterstützt Offset-basierte Paginierung:

```bash
# Seite 1
curl -H "X-API-Key: dev" "http://localhost:8000/v1/web/search?q=python&count=10&offset=0"

# Seite 2
curl -H "X-API-Key: dev" "http://localhost:8000/v1/web/search?q=python&count=10&offset=1"
```

`offset` gibt die Seite an (0–9), nicht den absoluten Index. Seite 2 mit `count=10` = Ergebnisse 11–20 bei der jeweiligen Engine.
