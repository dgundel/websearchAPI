# Deployment

## Lokale Entwicklung

```bash
# Abhängigkeiten installieren
pip3 install --user -e ".[dev]"

# .env anlegen
cp .env.example .env

# Server mit Auto-Reload starten
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Produktion (systemd)

### Service-Datei

```ini
# /etc/systemd/system/ws-api.service
[Unit]
Description=ws-api Web Search Service
After=network.target

[Service]
Type=exec
User=dg
WorkingDirectory=/home/dg/ws_api
Environment="API_KEYS=secret1,secret2"
Environment="CACHE_DIR=/var/cache/ws-api"
Environment="CACHE_TTL=300"
Environment="RATE_LIMIT=60"
ExecStart=/usr/bin/python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now ws-api
sudo journalctl -u ws-api -f
```

### Multi-Worker

`diskcache` ist process-safe durch File-Locking — mehrere uvicorn-Worker können gleichzeitig den Cache nutzen ohne Race Conditions, kein Redis-Daemon nötig.

---

## Produktion (Docker)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e "."

COPY app/ ./app/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

```bash
docker build -t ws-api .
docker run -d \
  -p 8000:8000 \
  -e API_KEYS=secret1,secret2 \
  -e CACHE_DIR=/tmp/ws_api_cache \
  -v ws_api_cache:/tmp/ws_api_cache \
  ws-api
```

---

## Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name search.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 30s;
    }
}
```

`X-Forwarded-For` wird für IP-basiertes Rate-Limiting ausgewertet.

---

## Konfiguration via .env

```bash
# .env
API_KEYS=key1,key2,key3
CACHE_DIR=/var/cache/ws-api
CACHE_TTL=600
RATE_LIMIT=30
HTTP_TIMEOUT=15.0
```

---

## Überwachung

```bash
# Health-Check (kein Auth nötig)
curl http://localhost:8000/health

# Logs
journalctl -u ws-api -f

# Cache-Größe prüfen
du -sh /var/cache/ws-api
```

---

## Scraper-Ausfälle

Scheitert ein Scraper (CAPTCHA, Timeout, etc.), gibt er `[]` zurück und loggt eine Warning. Die Anfrage wird mit den Ergebnissen der verbleibenden Engines beantwortet — kein Hard-Fail.

```
WARNING:app.scrapers.google:[google] CAPTCHA detected
WARNING:app.scrapers.duckduckgo:[duckduckgo] VQD fetch failed: ...
```

Persistente CAPTCHA-Probleme deuten auf IP-Blocking hin. Mögliche Gegenmaßnahmen:
- HTTP-Timeout erhöhen (`HTTP_TIMEOUT`)
- Anfragerate drosseln (`RATE_LIMIT`)
- Hinter einem Proxy betreiben
