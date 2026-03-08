---
name: web_search
description: Custom web, news, image & video search using local API (http://localhost:8000)
tools:
  - exec
---

# Custom Web Search Skill

This skill provides web search, image search, news search, video search, and autocomplete using the local search API at http://localhost:8000.

## Available Tools

Use the `exec` tool to make API calls to localhost:8000.

## Endpoints

| Endpoint | Path | Description |
|----------|------|-------------|
| Web Search | `/v1/web/search` | Web results with direct URLs |
| News Search | `/v1/news/search` | News articles with source & date |
| Image Search | `/v1/images/search` | Images with thumbnails |
| Video Search | `/v1/videos/search` | Videos (YouTube, Vimeo, etc.) |
| Suggestions | `/v1/suggest/search` | Autocomplete suggestions |

## Parameters

All endpoints support:
- `q` or `query`: Search query (required)
- `count`: Number of results (1-20, default 10)
- `country`: 2-letter country code (e.g., "DE", "US")
- `search_lang`: Language code (e.g., "de", "en")
- `freshness`: Time filter ("pd"=past day, "pw"=past week, "pm"=past month)
- `safesearch`: "off", "moderate", or "strict" (videos)

## Examples

### Web Search
```bash
curl -s "http://localhost:8000/v1/web/search?q=SPS+Programmierung&count=5&country=DE&search_lang=de"
```

### News Search
```bash
curl -s "http://localhost:8000/v1/news/search?q=SPS+Programmierung&count=10&country=DE&search_lang=de&freshness=pm"
```

### Image Search
```bash
curl -s "http://localhost:8000/v1/images/search?q=raspberry+pi&count=5"
```

### Video Search
```bash
curl -s "http://localhost:8000/v1/videos/search?q=SPS+Programmierung&count=5&country=DE&search_lang=de"
```

### Suggestions
```bash
curl -s "http://localhost:8000/v1/suggest/search?q=raspberry"
```

## Usage

When the user asks for a web search, news, images, videos, or autocomplete:
1. Choose the appropriate endpoint
2. Call it using curl with the user's query
3. Parse the JSON response
4. Present results in a readable format:
   - **Web/News**: title + URL + source/date/snippet
   - **Images**: title + image_url + thumbnail
   - **Videos**: title + url + thumbnail + source
   - **Suggestions**: list of query strings

Always prefer German results when the user writes in German (use country=DE, search_lang=de).
