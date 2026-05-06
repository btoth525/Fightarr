# Fightarr — Claude Code Context

This file is the authoritative project brief for any Claude Code session.
Read it fully before writing any code.

---

## What Fightarr Is

Fightarr is an open-source UFC event manager for Usenet and Plex.
It fills the gap Radarr explicitly refuses to fill (Radarr issue #9215, "Won't Fix"):
automated search, grab, rename, and import of UFC fight cards.

The goal is full feature and UX parity with the *arr suite — specifically Radarr —
but purpose-built for UFC events. If it doesn't feel like a first-class *arr app,
it isn't done.

**GitHub**: https://github.com/btoth525/Fightarr
**Image registry**: ghcr.io/btoth525/fightarr:latest
**Default port**: 7878 (same as Radarr — makes Unraid templates familiar)

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, APScheduler, httpx |
| Database | SQLite via aiosqlite (single-file, zero-config, Unraid-friendly) |
| Frontend | React 18, TypeScript, Vite, TailwindCSS, TanStack Query v5, React Router v6 |
| Container | Docker multi-stage, GHCR push via GitHub Actions |
| Tests | pytest-asyncio (`asyncio_mode=auto`), unittest.mock |
| Lint/fmt | ruff, black |

---

## Repository Layout

```
fightarr/
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI routers (one file per resource)
│   │   │   ├── events.py      # /event, /calendar, /wanted, /command/*
│   │   │   ├── indexers.py    # /indexer CRUD
│   │   │   ├── download_clients.py  # /downloadclient CRUD + /test
│   │   │   ├── queue.py       # /queue
│   │   │   ├── settings_api.py
│   │   │   └── health.py
│   │   ├── core/
│   │   │   ├── config.py      # pydantic-settings; env prefix FIGHTARR_
│   │   │   ├── database.py    # AsyncEngine, AsyncSessionLocal, init_db()
│   │   │   └── scheduler.py   # APScheduler jobs
│   │   ├── models/            # SQLAlchemy ORM models
│   │   │   ├── event.py       # Event, EventStatus, EventType
│   │   │   ├── indexer.py     # Indexer, IndexerType (newznab | torznab)
│   │   │   ├── download_client.py  # DownloadClient, DownloadClientType
│   │   │   └── queue_item.py  # QueueItem
│   │   ├── scrapers/
│   │   │   └── wikipedia.py   # Scrapes {YEAR}_in_UFC, returns ScrapedEvent list
│   │   └── services/
│   │       ├── newznab.py     # Newznab/Torznab XML search client
│   │       ├── tmdb.py        # Poster art: Wikipedia REST API (no key) + optional TMDB
│   │       ├── schedule_sync.py  # Wikipedia → DB upsert + poster backfill
│   │       ├── indexer_search.py # Stub: search all enabled indexers
│   │       ├── sabnzbd.py     # Legacy stub (superseded by download_clients/)
│   │       └── download_clients/
│   │           ├── base.py       # DownloadClientProtocol (typing.Protocol)
│   │           ├── factory.py    # build_client(DownloadClient) dispatcher
│   │           ├── sabnzbd.py    # SABnzbd REST API
│   │           ├── nzbget.py     # NZBGet JSON-RPC
│   │           ├── qbittorrent.py  # qBit WebUI + session cookie
│   │           ├── transmission.py # JSON-RPC + 409 CSRF token retry
│   │           ├── deluge.py      # Deluge Web JSON-RPC
│   │           └── real_debrid.py # Premium debrid: addMagnet → selectFiles → unrestrict
│   ├── tests/
│   │   ├── fixtures/          # newznab_search.xml, newznab_error.xml
│   │   ├── test_newznab.py    # 5 tests (parse, error, HTTP mock)
│   │   └── test_wikipedia_scraper.py  # 6 tests
│   └── pyproject.toml         # ruff ignore: E501, B008; black target: py312
├── frontend/
│   ├── public/
│   │   └── logo.svg           # UFC octagon + glove-bump SVG logo
│   └── src/
│       ├── api/
│       │   ├── client.ts      # Thin fetch wrapper: api.get/post/put/delete
│       │   └── types.ts       # Event, Indexer, DownloadClient, QueueItem
│       ├── components/
│       │   ├── Sidebar.tsx    # Nav: Events / Calendar / Activity / Wanted / Settings / System
│       │   ├── TopBar.tsx     # Page title + Refresh button
│       │   ├── EventCard.tsx  # Poster card with TMDB/Wikipedia art, monitor toggle, ↻ refresh
│       │   └── StatusBadge.tsx
│       ├── pages/
│       │   ├── EventsPage.tsx   # Grid of EventCards, filter bar, Fetch Art button
│       │   ├── CalendarPage.tsx # Month calendar of upcoming events
│       │   ├── ActivityPage.tsx # Queue / history stub
│       │   ├── WantedPage.tsx   # Missing + cutoff-unmet events
│       │   ├── SettingsPage.tsx # Indexers + Download Clients + Metadata sections
│       │   └── SystemPage.tsx   # System info stub
│       └── App.tsx            # Router shell
├── docs/
│   ├── ROADMAP.md
│   └── ARCHITECTURE.md
├── README.md
├── CONTRIBUTING.md
└── CLAUDE.md                  ← you are here
```

---

## Data Model

### Event
Core entity. One row = one UFC fight card.

| Column | Type | Notes |
|--------|------|-------|
| id | int PK | |
| slug | str unique | e.g. `ufc-300`, `ufc-fight-night-2024-04-06` |
| title | str | e.g. `UFC 300: Pereira vs Hill` |
| event_number | int? | 300 for UFC 300; null for Fight Nights |
| event_type | EventType | ppv / fight_night / on_abc / tuf_finale / other |
| event_date | date | |
| venue | str? | |
| location | str? | |
| main_event | str? | e.g. `Pereira vs Hill` |
| co_main_event | str? | |
| card_data | text? | JSON blob of full card |
| status | EventStatus | announced → upcoming → airing → released → downloaded / missing |
| monitored | bool | default true |
| file_path | text? | set after import |
| quality | str? | e.g. `1080p WEB-DL` |
| source_url | text? | Wikipedia article URL |
| tmdb_id | int? | set if TMDB match found |
| poster_url | text? | Wikipedia art (default) or TMDB art |
| created_at / updated_at | datetime | |

### Indexer
Newznab or Torznab sources (NZBGeek, NZBPlanet, DrunkenSlug, Prowlarr, Jackett).

### DownloadClient
SABnzbd · NZBGet · qBittorrent · Deluge · Transmission · Real-Debrid

### QueueItem
Active downloads. Links Event → DownloadClient job.

---

## API Endpoints (current)

```
GET    /api/v1/health
GET    /api/v1/event                       # list, filter by monitored/upcoming
GET    /api/v1/event/{id}
PUT    /api/v1/event/{id}                  # toggle monitored
POST   /api/v1/event/{id}/refresh-metadata # fetch TMDB/Wikipedia poster
GET    /api/v1/calendar                    # events in date range
GET    /api/v1/wanted/missing
POST   /api/v1/command/refresh-schedule    # trigger Wikipedia sync
POST   /api/v1/command/refresh-metadata    # bulk poster backfill

GET    /api/v1/indexer
POST   /api/v1/indexer
PUT    /api/v1/indexer/{id}
DELETE /api/v1/indexer/{id}

GET    /api/v1/downloadclient
POST   /api/v1/downloadclient
PUT    /api/v1/downloadclient/{id}
DELETE /api/v1/downloadclient/{id}
POST   /api/v1/downloadclient/{id}/test    # test_connection()

GET    /api/v1/queue
GET    /api/v1/settings/downloadclient
GET    /api/v1/settings/metadata
POST   /api/v1/settings/metadata/test     # validate TMDB key
```

---

## Key Services

### `services/newznab.py`
- `NewznabClient.search(query, categories="5070,5080")` — async httpx GET
- `parse_search_response(xml_bytes, indexer_name)` — pure parser, testable
- Handles `{http://www.newznab.com/DTD/2010/feeds/attributes/}attr` namespace
- `NewznabError(code, description)` for API-level errors

### `services/tmdb.py` (also handles Wikipedia)
- `fetch_event_poster(title, year, api_key, source_url)` — Wikipedia first, TMDB optional
- Wikipedia REST API: `https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}`
- No API key required for Wikipedia path
- `test_connection(api_key)` — validates optional TMDB key

### `services/schedule_sync.py`
- `sync_schedule(years)` — scrapes Wikipedia, upserts events, then calls `_backfill_posters()`
- Runs every 6 hours via APScheduler

### `scrapers/wikipedia.py`
- Fetches `https://en.wikipedia.org/wiki/{YEAR}_in_UFC`
- Parses HTML table with BeautifulSoup + lxml
- Returns `list[ScrapedEvent]`

### `services/download_clients/`
- `DownloadClientProtocol`: `add_download(url, name, category) -> str`, `get_queue() -> list[dict]`, `test_connection() -> bool`
- `build_client(dc: DownloadClient) -> DownloadClientProtocol` in `factory.py`

---

## Frontend Conventions

- **TailwindCSS** with custom design tokens in `tailwind.config.js`:
  - Colors: `bg`, `bg-panel`, `bg-elevated`, `bg-input`
  - Text: `text`, `text-bright`, `text-muted`, `text-dim`
  - `accent` = UFC orange (#e8820c)
  - `border`, `border-strong`
  - Status colors: `status-announced`, `status-upcoming`, `status-airing`, `status-released`, `status-downloaded`, `status-missing`
- **TanStack Query**: `useQuery` for fetches, `useMutation` for writes, always `invalidateQueries` on success
- **API client**: `api.get<T>()`, `api.post<T>()`, `api.put<T>()`, `api.delete<T>()` in `src/api/client.ts`
- Vite proxies `/api/v1` → `http://localhost:8000/api/v1` in dev

---

## Dev Setup

```bash
# Backend
cd backend
pip install -r requirements.txt   # or: pip install greenlet  if missing
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev   # → http://localhost:5173

# Tests
cd backend && python3.12 -m pytest tests/ -q
# Lint
python3.12 -m ruff check app/ --fix -q && python3.12 -m black app/ -q
```

---

## Ground Rules

1. **Tests**: every new service function gets a test. Use `unittest.mock` for HTTP,
   fixtures in `tests/fixtures/` for XML/HTML payloads.
2. **Async**: all DB and HTTP calls are async. Never use sync SQLAlchemy calls.
3. **No comments** unless the WHY is genuinely non-obvious.
4. **No extra abstractions** beyond what the current task requires.
5. **Lint clean**: `ruff` + `black` must pass. ruff ignores: `E501`, `B008`.
6. **Radarr parity**: every UI feature should feel identical to Radarr. If it
   wouldn't fit in the Radarr UI language, rethink it.
7. **No TMDB key required**: poster art works out of the box via Wikipedia.
   TMDB is an optional upgrade.

---

## Environment Variables (`FIGHTARR_` prefix)

| Var | Default | Purpose |
|-----|---------|---------|
| `FIGHTARR_DB_PATH` | `./fightarr.db` | SQLite file path |
| `FIGHTARR_LOG_LEVEL` | `INFO` | |
| `FIGHTARR_TMDB_API_KEY` | `` | Optional — better poster art |
| `FIGHTARR_CORS_ORIGINS` | localhost:5173,7878 | |
| `FIGHTARR_SCHEDULE_REFRESH_INTERVAL` | 21600 | seconds (6h) |
| `FIGHTARR_INDEXER_SEARCH_INTERVAL` | 1800 | seconds (30m) |

Download client credentials are stored in the database (Settings UI), not env vars.

---

## What's NOT Done Yet (priorities in order)

See `docs/ROADMAP.md` for the full breakdown. The top priorities:

1. **Search loop** — query builder → Newznab search → release scorer → grab → QueueItem
2. **Event detail page** — poster, full card, interactive search, history tab
3. **Quality profiles** — model + UI (cutoff, allowed qualities)
4. **Post-processing** — SAB webhook → rename → library import → Plex notify
5. **Settings tabs** — full Radarr-style settings with proper sub-navigation
6. **Notifications** — Discord webhook minimum
7. **Docker + CI** — multi-arch GHCR build, GitHub Actions lint+test
