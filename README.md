# Link Shortener

URL shortening service with FastAPI + SQLite backend and HTML/JS frontend.

## Features

- **POST /shorten** — Submit a URL, get a short code back
- **GET /{short_code}** — 302 redirect to the original URL
- **GET /stats/{short_code}** — Click count and creation timestamp
- **Web UI** — Form to shorten URLs and look up stats

## Tech Stack

- FastAPI + Uvicorn
- SQLAlchemy + SQLite
- Vanilla HTML/CSS/JS frontend
- pytest test suite

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
