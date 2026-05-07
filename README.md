<div align="center">

<img src="frontend/public/logo.svg" width="80" alt="Fightarr logo" />

# Fightarr

**UFC event manager for Usenet and Plex**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-orange.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![Status](https://img.shields.io/badge/Status-Pre--Alpha-red.svg)](#status)
[![Vibe Coded](https://img.shields.io/badge/Vibe--Coded-AI--Assisted-purple.svg)](#-vibe-coded--read-this-before-you-deploy)

Radarr [explicitly won't support UFC](https://github.com/Radarr/Radarr/issues/9215). Fightarr does.

</div>

---

## ⚠️ Vibe-coded — read this before you deploy

Fightarr is **vibe-coded**: a human owner directing an AI coding assistant in conversational, iterative passes rather than a traditional spec → design → review → implement workflow. The features are real, the tests pass, the production build is clean — but you should treat the codebase the same way you'd treat any unaudited OSS app you found on GitHub last week.

**Specifically:**

- **No security audit yet.** Don't expose this to the public internet without a reverse proxy + auth in front of it. There is no built-in authentication. Run it on your LAN or behind a VPN/Tailscale/Cloudflare Tunnel.
- **Stores secrets in SQLite.** API keys (indexer, Plex, Jellyfin, Discord webhooks) and download-client passwords live in `fightarr.db`. They are *not* encrypted at rest — protect that file the same way you'd protect a `.env` with the same secrets.
- **Talks to your indexers and download clients on your behalf.** Misconfigured priority ordering or quality scoring could grab releases you didn't want. Start with monitor-by-default *off* (it is) and grab a few events manually before turning on bulk auto-search.
- **Schema migrations are best-effort additive.** New columns are auto-added on startup, but column type changes or destructive renames will require a manual `sqlite3` step. Back up `fightarr.db` before pulling a new version.
- **The disk side-effects are real.** The importer hardlinks/copies files into your media root, downloads `poster.jpg` into each event folder, and triggers Plex/Jellyfin library scans. Test against a scratch directory first.
- **Production-ready means "the happy path works end-to-end."** It does not mean every error case has been thought through. File a GitHub issue when you find one.

If you'd rather wait for a human-reviewed v1.0.0 cut, watch the repo and check back when there's a versioned tag without `pre-alpha` on it.

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

## Library output (Plex-ready)

When a download completes, Fightarr renames and organizes files exactly the way Plex expects:

```
{media_root}/
├── UFC 300 - Pereira vs. Hill (2024)/
│   ├── UFC 300 - Pereira vs. Hill (2024) WEBDL-1080p.mkv
│   └── poster.jpg
├── UFC Fight Night - Strickland vs. Hernandez (2026)/
│   ├── UFC Fight Night - Strickland vs. Hernandez (2026) WEBDL-1080p.mkv
│   └── poster.jpg
└── ...
```

- **Folder format**: `{Title} ({Year})` — Radarr-compatible, Plex Movie agent picks it up automatically
- **Filename format**: `{Folder} {Quality}.{ext}` with full quality profile (`WEBDL-1080p`, `Bluray-2160p`, `WEBRip-720p`, `HDTV-720p`)
- **Poster art**: `poster.jpg` is downloaded into each event folder — Plex's Local Media Assets agent uses it as the cover even without a TMDB match
- **Hardlinks-first**: imports use `os.link()` so the original NZB stays seedable; falls back to copy across filesystems
- **Sample skipping**: anything under 100 MB or with "sample" in the name is ignored

### SAB / NZBGet category setup

Fightarr sends every download with a `cat=` param (default: `ufc`). Configure your downloader to put that category somewhere Fightarr can read:

**SABnzbd**: Settings → Categories → Add a category named `ufc`. Set the folder to whatever incomplete/complete path you use (e.g. `/downloads/ufc`). That's it — Fightarr's queue monitor watches SAB history, finds the largest video file, renames it, and moves it into your media root.

**NZBGet**: Settings → Categories → Add `ufc` with a destination dir. Same flow as SAB.

You don't need post-processing scripts. Fightarr handles renaming, poster art, and Plex/Jellyfin notification on its own — same model as Radarr.

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
