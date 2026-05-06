# Roadmap

Tracking what's done, what's next, and what's wishlist. Each unchecked box
is a candidate for an issue/PR. Pick one, open an issue saying you're on it,
and ship.

## Phase 0 — Foundation (mostly done)

- [x] Repo scaffold, Docker setup, CI-friendly layout
- [x] FastAPI backend skeleton with routers
- [x] SQLAlchemy models (Event, Indexer, QueueItem)
- [x] Wikipedia scraper for `{YEAR}_in_UFC` pages
- [x] Schedule sync service (idempotent upsert)
- [x] APScheduler wired up
- [x] React frontend shell with Radarr-styled dark theme
- [x] Pages: Events, Calendar, Activity, Wanted, Settings, System
- [ ] CI pipeline (GitHub Actions: lint + test backend, build frontend)
- [ ] Pre-commit hooks
- [ ] Replace LICENSE stub with full GPL-3.0 text

## Phase 1 — Searching and downloading (the core loop)

This is what makes Fightarr useful. Without it, we just have a pretty
schedule viewer.

- [ ] **Newznab client** — implement `search()` in `services/newznab.py`. Hit
      `{base}/api?t=search&q=...&apikey=...&cat=...`, parse XML response,
      return `NewznabRelease` list. Tests with a fixture XML response.
- [ ] **Query builder** — given an event, generate sensible search strings:
      - `UFC.300` and `UFC 300` for numbered
      - `UFC.Fight.Night.YYYY-MM-DD` for Fight Nights
      - Fall back to fighter names from `main_event` field
- [ ] **Release scorer** — score releases by quality profile:
      - Resolution preference (2160p > 1080p > 720p)
      - Codec preference (h265 > h264)
      - Size sanity (drop releases <500MB or >20GB)
      - Skip prelims/early prelims if user opted out
      - Penalty for duplicate-looking releases
- [ ] **Quality profiles model + UI** — Radarr-style profile editor
- [ ] **SABnzbd client** — implement `add_url()` and `queue_status()`. Push
      NZBs with our category, track returned `nzo_id` against QueueItem.
- [ ] **Search loop** — for each wanted event, search all enabled indexers,
      pick best release, push to SAB, create QueueItem
- [ ] **Manual search endpoint** — `POST /event/{id}/search` returns matched
      releases without auto-grabbing, for the UI's "Interactive Search" view

## Phase 2 — Post-processing

- [ ] **SAB completion webhook** — endpoint SAB calls after a download
      completes (or category-script integration)
- [ ] **Renamer** — given a downloaded file path and an event, rename to a
      Plex-friendly format:
      `UFC 300 - Pereira vs Hill (2024-04-13)/UFC.300.Pereira.vs.Hill.1080p.WEB-DL.mkv`
- [ ] **Library import** — move/hardlink to library root, update Event with
      `file_path` and `quality`, set status to `DOWNLOADED`
- [ ] **Plex notification** — POST to Plex `/library/sections/{id}/refresh`
      so the new file appears immediately

## Phase 3 — Polish

- [ ] **UFCStats fallback scraper** — when Wikipedia is missing details
- [ ] **Sherdog fallback scraper** — third source for resilience
- [ ] **Card structure** — parse main/co-main/prelims/early-prelims into the
      `card_data` JSON field, surface in UI
- [ ] **Poster art** — find/cache event posters (UFC.com? TMDB?)
- [ ] **Notifications** — Discord webhook, Apprise integration
- [ ] **Health dashboard** — show indexer uptime, last successful search,
      etc.
- [ ] **Settings persistence** — full DB-backed settings instead of env vars
- [ ] **Auth** — basic auth or API key for the UI/API

## Phase 4 — Beyond UFC

If the core works well, the architecture trivially extends to other PPVs
that Radarr also can't handle:

- [ ] Boxing PPVs
- [ ] WWE PLEs
- [ ] AEW PPVs
- [ ] PFL events

Each is mostly a new scraper and search-query-builder; the rest of the
pipeline is identical.
