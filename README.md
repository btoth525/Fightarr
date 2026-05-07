<div align="center">

<img src="frontend/public/logo.svg" width="80" alt="Fightarr logo" />

# Fightarr

**UFC event manager for Usenet and Plex**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-orange.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![Status](https://img.shields.io/badge/Status-Pre--Alpha-red.svg)](#status)

Radarr [explicitly won't support UFC](https://github.com/Radarr/Radarr/issues/9215). Fightarr does.

</div>

---

## The problem

UFC release names look like `UFC.300.Pereira.vs.Hill.1080p.WEB-DL.H264`. There is no `(YYYY)`. The event is not in TMDB. Radarr's parser requires both. The Radarr team closed the feature request as **Won't Fix** and the community has been duct-taping workarounds for years — manually adding each card as a fake movie, manually matching releases, manually renaming files.

Fightarr is a purpose-built sibling to Radarr that solves this correctly. It speaks directly to your Newznab indexers and SABnzbd, understands UFC event naming natively, and organizes your library the way Plex expects — without any of the Radarr-shaped hacks.

---

## Screenshots

<table>
<tr>
<td><b>Events</b> — 68 events tracked across the full 2026 schedule, scraped live from Wikipedia</td>
</tr>
<tr>
<td><img src="docs/screenshots/events.png" alt="Events page" /></td>
</tr>
<tr>
<td><b>Calendar</b> — upcoming events grouped by date with venue details</td>
</tr>
<tr>
<td><img src="docs/screenshots/calendar.png" alt="Calendar page" /></td>
</tr>
<tr>
<td><b>Wanted</b> — monitored events with no file, each with a manual Search trigger</td>
</tr>
<tr>
<td><img src="docs/screenshots/wanted.png" alt="Wanted page" /></td>
</tr>
<tr>
<td><b>Settings</b> — add Newznab-compatible indexers (NZBGeek, DrunkenSlug, NZBPlanet, etc.)</td>
</tr>
<tr>
<td><img src="docs/screenshots/settings.png" alt="Settings page" /></td>
</tr>
</table>

---

## What it does

| Feature | Status |
|---|---|
| Scrapes UFC schedule from Wikipedia (PPVs, Fight Nights, On ABC) | ✅ Working |
| Historical year sync (any year from 2001) + future year pre-load | ✅ Working |
| Cover art — Wikipedia REST API, zero config, no API key needed | ✅ Working |
| Newznab / Torznab indexer support + connection test | ✅ Working |
| Calendar view — next 30 days, grouped by date | ✅ Working |
| Wanted list — monitored events with no file | ✅ Working |
| Indexer CRUD + test button via Settings UI | ✅ Working |
| Download clients — SABnzbd, NZBGet, qBittorrent, Deluge, Transmission, Real-Debrid | ✅ Working |
| Download client CRUD + connection test via Settings UI | ✅ Working |
| Post-processing renamer — Radarr-style Plex folder/file naming | ✅ Working |
| Hardlink-first library import (copy fallback) | ✅ Working |
| Plex + Jellyfin library refresh notify | ✅ Working |
| Activity queue — live progress bars, status badges, auto-refresh | ✅ Working |
| History page — imported/failed downloads with file paths | ✅ Working |
| Live DB schema migrations on startup (no Alembic required) | ✅ Working |
| Event detail page — poster, metadata, history, interactive search | ✅ Working |
| Query builder — PPV by number, Fight Night by sequential number + date fallback, fighter surnames | ✅ Working |
| Interactive search — quality profiles (WEBDL-1080p), Prelims badge, sorted results | ✅ Working |
| Search diagnostics — indexer errors and queries tried shown in UI | ✅ Working |
| Monitor/unmonitor toggle — per-event and bulk unmonitor all | ✅ Working |
| Release scorer — resolution, codec, size, prelims filter | 🔧 In progress |
| Quality profiles UI (cutoff model) | 📋 Planned |
| Discord / Apprise notifications | 📋 Planned |
| Single-container Docker image for Unraid | 📋 Planned |
| Unraid Community Applications template | 📋 Planned |

Full roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)

---

## Quickstart

### Docker (recommended — single container)

```bash
docker run -d \
  --name fightarr \
  -p 7878:7878 \
  -v /your/config:/config \
  -v /your/ufc/media:/media \
  ghcr.io/btoth525/fightarr:latest
```

| URL | Purpose |
|---|---|
| http://localhost:7878 | Web UI |
| http://localhost:7878/api/v1 | REST API |
| http://localhost:7878/docs | Swagger |

> Port 7878 matches Radarr's default — no muscle-memory retraining required.

### Docker Compose (dev)

```bash
git clone https://github.com/btoth525/Fightarr
cd Fightarr
docker compose up --build
```

### Manual (development)

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7878
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## Architecture

```
┌──────────────┐   ┌────────────────────┐   ┌──────────┐   ┌──────┐
│  Wikipedia   │   │  Newznab indexers  │   │ SABnzbd  │   │ Plex │
│  (schedule)  │   │  (your provider)   │   │          │   │      │
└──────┬───────┘   └─────────┬──────────┘   └────┬─────┘   └──┬───┘
       │                     │                   ▲             ▲
       ▼                     ▼                   │             │
┌──────────────────────────────────────────────────────────────────┐
│                           Fightarr                               │
│                                                                  │
│  Scrapers → Event DB → Query builder → Newznab search            │
│                              ↓                                   │
│                        Release scorer → SABnzbd API              │
│                                              ↓                   │
│                                     Post-process renamer         │
└──────────────────────────────────────────────────────────────────┘
```

**Stack**

| Layer | Tech |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), SQLite, APScheduler |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Scraping | httpx, BeautifulSoup4, lxml |
| Indexer client | Newznab (lxml XML parser) |
| Download client | SABnzbd HTTP API |
| Container | Docker Compose (dev), single multi-stage image (prod/Unraid) |

---

## Unraid

Fightarr is built to live in your Unraid tower alongside Radarr, Sonarr, and SABnzbd. Pull it from GHCR and map two folders:

```yaml
# In Unraid → Docker → Add Container
Image: ghcr.io/btoth525/fightarr:latest
Port: 7878 → 7878

Volumes:
  /mnt/user/appdata/fightarr  →  /config   (stores the SQLite database)
  /mnt/user/media/ufc         →  /media    (your UFC library)

Environment (optional):
  FIGHTARR_TMDB_API_KEY  =  <your key if you want TMDB posters>
  FIGHTARR_LOG_LEVEL     =  INFO
```

A Community Applications template will be submitted once the search loop ships end-to-end.

---

## Docker image

Production images are published to GitHub Container Registry:

```bash
docker pull ghcr.io/btoth525/fightarr:latest
```

Multi-arch: `linux/amd64` and `linux/arm64` (covers Unraid on both Intel/AMD and ARM boards).

Tags follow `v0.x.y` semver. `:latest` always points to the most recent release.

---

## Contributing

Open-source from day one. PRs welcome.

- Read [CONTRIBUTING.md](CONTRIBUTING.md) for the ground rules
- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design decisions
- The [Radarr issue](https://github.com/Radarr/Radarr/issues/9215) is the canonical "why this exists" document

**Good first issues to pick up:**
- Query builder — given an `Event`, generate UFC-specific Newznab search strings
- Release scorer — rank results by resolution, codec, size, and user preferences
- SABnzbd client — fill in the `add_url` and `queue_status` stubs

```bash
# Run tests
cd backend && pytest -v

# Lint
ruff check . && black --check .
```

---

## License

[GPL-3.0](LICENSE) — same as Radarr, Sonarr, Lidarr, and the rest of the ecosystem. The *arr norms apply here too.
