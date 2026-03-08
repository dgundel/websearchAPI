# Installation & systemd-Setup

## 1. Voraussetzungen

```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip git
```

## 2. Repository klonen

```bash
git clone https://github.com/dgundel/websearchAPI.git /home/dg/websearchAPI
cd /home/dg/websearchAPI
```

## 3. Abhängigkeiten installieren

```bash
pip3 install --user --break-system-packages -e "."
```

> Falls du kein `python3-venv` installiert hast, verwende `--break-system-packages`.
> Alternativ: `pip3 install --user -e "."` (ohne Flag, falls pip es erlaubt).

## 4. Konfiguration

```bash
cp .env.example .env
```

`.env` anpassen:

```bash
# Komma-separierte API-Keys (leer = Dev-Modus, kein Auth)
API_KEYS=geheimer-schluessel-1,schluessel-2

# Cache
CACHE_DIR=/var/cache/websearchAPI
CACHE_TTL=300

# Rate-Limiting (Anfragen/Minute pro Key)
RATE_LIMIT=60

# HTTP-Timeout in Sekunden
HTTP_TIMEOUT=10.0
```

Cache-Verzeichnis anlegen:

```bash
sudo mkdir -p /var/cache/websearchAPI
sudo chown $USER:$USER /var/cache/websearchAPI
```

## 5. Manuell testen

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Health-Check
curl http://localhost:8000/health

# Video-Suche (Dev-Modus ohne Auth)
curl "http://localhost:8000/v1/videos/search?q=python+tutorial&count=5"

# Mit API-Key
curl -H "X-API-Key: geheimer-schluessel-1" \
  "http://localhost:8000/v1/web/search?q=fastapi"
```

## 6. systemd Service einrichten

### Service-Datei erstellen

```bash
sudo nano /etc/systemd/system/websearchAPI.service
```

Inhalt (Pfade und User ggf. anpassen):

```ini
[Unit]
Description=websearchAPI Web Search Service
After=network.target

[Service]
Type=exec
User=dg
Group=dg
WorkingDirectory=/home/dg/websearchAPI

# Umgebungsvariablen direkt oder via EnvironmentFile
EnvironmentFile=/home/dg/websearchAPI/.env

ExecStart=/home/dg/.local/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2

Restart=on-failure
RestartSec=5

# Sicherheitshärtung (optional, empfohlen)
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

> **Hinweis:** `uvicorn` liegt nach `pip3 install --user` unter `~/.local/bin/uvicorn`.
> Pfad prüfen: `which uvicorn` oder `python3 -m uvicorn` als ExecStart verwenden:
> ```
> ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
> ```

### Service aktivieren und starten

```bash
sudo systemctl daemon-reload
sudo systemctl enable websearchAPI      # Autostart beim Boot
sudo systemctl start websearchAPI

# Status prüfen
sudo systemctl status websearchAPI

# Logs live verfolgen
sudo journalctl -u websearchAPI -f
```

### Service verwalten

```bash
sudo systemctl stop websearchAPI        # Stoppen
sudo systemctl restart websearchAPI     # Neustarten (z.B. nach .env-Änderung)
sudo systemctl disable websearchAPI     # Autostart deaktivieren
```

## 7. Nginx Reverse Proxy (optional)

```bash
sudo apt-get install nginx
sudo nano /etc/nginx/sites-available/websearchAPI
```

```nginx
server {
    listen 80;
    server_name search.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 30s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/websearchAPI /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 8. Verfügbare Endpoints

| Method | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/v1/web/search` | Web-Suche (Google + Bing + DuckDuckGo) |
| `GET` | `/v1/images/search` | Bildsuche (Bing Images) |
| `GET` | `/v1/news/search` | Nachrichtensuche (Bing News) |
| `GET` | `/v1/videos/search` | Videosuche (Bing Videos) |
| `GET` | `/v1/suggest/search` | Autocomplete (Google) |
| `GET` | `/health` | Health-Check |

Vollständige Parameter-Referenz: [api-reference.md](api-reference.md)
