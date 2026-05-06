# Fightarr Roadmap

Target: full feature and UX parity with Radarr, purpose-built for UFC events.
Every item below maps to a concrete Radarr feature. If Radarr has it, Fightarr needs it.

Legend: ✅ done · 🔨 in progress · ⬜ not started

---

## Phase 0 — Foundation ✅

| # | Feature | Status |
|---|---------|--------|
| 0.1 | Repo scaffold, Docker layout | ✅ |
| 0.2 | FastAPI backend skeleton | ✅ |
| 0.3 | SQLAlchemy 2.0 async ORM + SQLite | ✅ |
| 0.4 | Event model (slug, title, status, monitored, poster_url…) | ✅ |
| 0.5 | Wikipedia scraper — `{YEAR}_in_UFC` | ✅ |
| 0.6 | Schedule sync service (idempotent upsert + poster backfill) | ✅ |
| 0.7 | APScheduler wired (6h schedule refresh, 30m search) | ✅ |
| 0.8 | React + TypeScript + Vite + Tailwind dark theme | ✅ |
| 0.9 | Pages: Events, Calendar, Activity, Wanted, Settings, System | ✅ |
| 0.10 | Sidebar with logo + active-link accent | ✅ |
| 0.11 | EventCard grid with poster art (Wikipedia/TMDB, no key required) | ✅ |
| 0.12 | Newznab/Torznab client + 11 unit tests | ✅ |
| 0.13 | DownloadClient model + CRUD API | ✅ |
| 0.14 | SABnzbd · NZBGet · qBittorrent · Deluge · Transmission · Real-Debrid clients | ✅ |
| 0.15 | Settings: Indexers + Download Clients + Metadata sections | ✅ |
| 0.16 | UFC octagon + glove-bump SVG logo + favicon | ✅ |

---

## Phase 1 — Core Search Loop 🔨

This is what makes Fightarr useful. Everything else is polish on top.

### 1.1 Query Builder ⬜
**Radarr equivalent**: movie title + year → search string
- PPV numbered:  `UFC.300`, `UFC 300`, `UFC.300.Pereira.vs.Hill`
- Fight Night:   `UFC.Fight.Night.2024.04.06`, `UFC.Fight.Night.Hill.vs.Pereira`
- Fighter names from `main_event` field as third-pass fallback
- Returns `list[str]` of queries to try in order

### 1.2 Release Scorer ⬜
**Radarr equivalent**: custom format score + quality profile cutoff
- Resolution score: 2160p=100 · 1080p=80 · 720p=60 · 480p=20
- Codec bonus: HEVC/x265 +10 · H264 +5
- Source bonus: WEB-DL +15 · WEBRip +10 · HDTV 0
- Size sanity: reject <500MB (too small) or >20GB (insane)
- Skip prelims/early-prelims flag (user configurable)
- Duplicate penalty: if two releases score the same, prefer smaller file
- Returns scored `list[ScoredRelease]` sorted descending

### 1.3 Quality Profiles Model + API ⬜
**Radarr equivalent**: Settings > Profiles
- `QualityProfile` model: name, cutoff (min quality to stop searching), allowed qualities list
- Default profiles: "Any", "HD-1080p", "HD-720p", "Ultra-HD"
- `GET/POST/PUT/DELETE /qualityprofile`
- Event model gets `quality_profile_id` FK

### 1.4 Search Loop ⬜
**Radarr equivalent**: automatic + RSS search
- For each monitored event in `MISSING` or `RELEASED` status:
  1. Build queries via query builder
  2. Search all enabled indexers (Newznab + Torznab)
  3. Score all releases
  4. Pick best release above quality profile cutoff
  5. `add_download()` to highest-priority enabled download client
  6. Create `QueueItem` row with `client_id`, `release_title`, `external_id`
- Runs on APScheduler every 30 min (already wired, just needs implementation)
- `POST /command/EventSearch` — manual trigger for a single event

### 1.5 Manual / Interactive Search ⬜
**Radarr equivalent**: Movie detail → Interactive Search tab
- `GET /event/{id}/search` — returns all scored releases without grabbing
- Frontend: modal showing release table with columns:
  Indexer · Title · Size · Age · Peers/Seeds · Quality · Score · Grab button
- Grab button: `POST /event/{id}/grab` with `{ release_guid, indexer_id }`

### 1.6 Event Detail Page ⬜
**Radarr equivalent**: Movie detail overlay/page
- Route: `/events/{id}`
- Poster (large) + metadata panel
- Tabs: Overview · History · Search (interactive search)
- Overview: title, date, venue, location, main event, co-main, status badge, quality
- History tab: all QueueItems for this event (grabbed, downloaded, failed, imported)
- Manual search trigger button ("Search")
- Edit monitored / quality profile inline

---

## Phase 2 — Post-Processing ⬜

### 2.1 SABnzbd Completion Webhook ⬜
**Radarr equivalent**: Settings > Download Clients > Completed Download Handling
- `POST /api/v1/webhook/sabnzbd` — receives SAB post-process notification
- Match `nzo_id` against QueueItem, get file path, trigger rename

### 2.2 File Renamer ⬜
**Radarr equivalent**: Settings > Media Management > Movie Naming
- Naming format (configurable): `UFC {number} - {main_event} ({date})`
- File: `UFC.{number}.{main_event}.{quality}.{codec}.mkv`
- Handles Fight Night format: `UFC.Fight.Night.{date}.{main_event}.1080p.WEB-DL.mkv`
- `POST /api/v1/command/RenameFiles` with event_id

### 2.3 Library Import ⬜
**Radarr equivalent**: Manual import + auto-import
- Move or hardlink file to `FIGHTARR_MEDIA_ROOT/{event_folder}/`
- Update `Event.file_path`, `Event.quality`, `Event.status = DOWNLOADED`
- `POST /api/v1/command/ManualImport`

### 2.4 Plex / Jellyfin Notification ⬜
**Radarr equivalent**: Settings > Connect > Plex Media Server
- `POST http://{plex_host}:32400/library/sections/{section_id}/refresh?X-Plex-Token={token}`
- Config: `plex_host`, `plex_token`, `plex_section_id` in settings

---

## Phase 3 — Full Radarr UI Parity ⬜

### 3.1 Settings Page — Full Tab Navigation ⬜
**Radarr equivalent**: Settings with sidebar tabs
Tabs to implement:
- **Media Management** — naming format, root folders, recycle bin, permissions
- **Profiles** — quality profiles editor (cutoff + ordered quality list)
- **Quality** — quality definitions (min/max size per quality)
- **Indexers** — existing (expand with caps/test/RSS support)
- **Download Clients** — existing (expand with remote path mappings)
- **Import Lists** — stub for future expansion
- **Connect** — Plex, Jellyfin, Discord, Apprise
- **Metadata** — existing (Wikipedia + optional TMDB)
- **General** — host, port, base URL, log level, auth, analytics opt-out
- **UI** — theme, date format, language

### 3.2 Events Page — Table View Toggle ⬜
**Radarr equivalent**: Movies → toggle grid/table view
- Table columns: Poster · Title · Date · Status · Quality · Size · Actions
- Sortable columns (click header)
- Sticky header
- Bulk select + bulk actions (monitor/unmonitor, search, delete)

### 3.3 Proper Modal Dialogs ⬜
**Radarr equivalent**: Add Movie modal, Edit Movie modal
- Replace inline form expansion in Settings with proper portal modals
- Backdrop blur + escape-to-close + focus trap
- Shared `<Modal>` component

### 3.4 Toast / Notification System ⬜
**Radarr equivalent**: Top-right toast notifications
- Success (green), warning (yellow), error (red) toasts
- Auto-dismiss after 4s
- `useToast()` hook used throughout mutations
- `react-hot-toast` or build a simple custom implementation

### 3.5 Activity Page — Full Queue + History ⬜
**Radarr equivalent**: Activity > Queue + Activity > History
- **Queue tab**: active downloads with progress bars, ETA, size, status badges
  - Columns: Event · Client · Title · Status · Progress · Size · Time Left · Actions
  - Actions: Force check · Remove from queue (+ blacklist option)
  - Auto-refresh every 10s
- **History tab**: completed/failed downloads
  - Columns: Event · Source title · Date · Quality · Action (grabbed/imported/failed)
  - Filter by event or status

### 3.6 Wanted Page — Full Implementation ⬜
**Radarr equivalent**: Wanted > Missing + Wanted > Cutoff Unmet
- **Missing tab**: monitored events that aired but have no file
  - Columns: Title · Date · Quality Profile · Last Search · Actions
  - "Search All" button → bulk search
- **Cutoff Unmet tab**: have a file but it's below quality cutoff
  - Columns: Title · Date · Current Quality · Profile Cutoff · Actions

### 3.7 System Page ⬜
**Radarr equivalent**: System > Status / Tasks / Logs / Backup / Updates
- **Status tab**: app version, DB size, start time, memory, platform
- **Tasks tab**: list scheduled tasks with next-run time + manual trigger
- **Logs tab**: tail log output (last 500 lines), level filter, download logs
- **Backup tab**: create + download DB backup
- **Updates tab**: GitHub Releases API — show current vs latest

### 3.8 Keyboard Shortcuts ⬜
**Radarr equivalent**: `?` shows shortcut overlay
- `G` then `M` → Events (Movies)
- `G` then `C` → Calendar
- `G` then `A` → Activity
- `G` then `W` → Wanted
- `G` then `S` → Settings

---

## Phase 4 — Quality of Life ⬜

### 4.1 Tags System ⬜
**Radarr equivalent**: Tags on movies + indexers + download clients
- `Tag` model (id, label)
- Events, indexers, download clients all support multiple tags
- Tags filter on Events page

### 4.2 Notifications / Connect ⬜
**Radarr equivalent**: Settings > Connect
- Discord webhook: `POST {webhook_url}` on grab / import / failure
- Apprise integration for 50+ notification providers
- Minimum viable: Discord + ntfy

### 4.3 UFCStats Scraper ⬜
- When Wikipedia is missing fight card details, fall back to ufcstats.com
- Adds co-main, prelims, and fighter records to `card_data`

### 4.4 Full Card Data ⬜
- Parse main / co-main / prelims / early prelims into structured `card_data` JSON
- Surface on Event detail page as fight-by-fight card

### 4.5 Settings Persistence (DB-backed) ⬜
**Radarr equivalent**: all settings in DB, not env vars
- `Setting` model: `key`, `value`, `type`
- Settings API: `GET/PUT /api/v1/config/{key}`
- Download client credentials stay in DB (already done)
- Move naming format, root folder, quality profiles, notification webhooks → DB

### 4.6 Auth ⬜
**Radarr equivalent**: Settings > General > Authentication
- Form login with username/password
- JWT session token
- Optional: API key for external apps
- Dev mode can disable auth

---

## Phase 5 — Container & CI ⬜

### 5.1 Multi-stage Dockerfile ⬜
```
Stage 1 (builder): node:20-alpine → npm ci && npm run build
Stage 2 (backend): python:3.12-slim → pip install, copy frontend dist into /static
Stage 3 (final): copy from backend, set PUID/PGID/TZ, EXPOSE 7878
```
- FastAPI serves `/` from the bundled frontend static files
- Single container, single port — Unraid-friendly

### 5.2 GitHub Actions CI ⬜
- On every push/PR:
  - `ruff check` + `black --check` backend
  - `pytest` backend
  - `tsc --noEmit` + `npm run build` frontend
- On push to `main`:
  - Build multi-arch Docker image (`linux/amd64`, `linux/arm64`)
  - Push to `ghcr.io/btoth525/fightarr:latest` + `ghcr.io/btoth525/fightarr:{sha}`

### 5.3 Unraid Community Applications Template ⬜
- XML template in `unraid/fightarr.xml`
- Variables: `FIGHTARR_DB_PATH`, `FIGHTARR_TMDB_API_KEY` (optional), `PUID`, `PGID`, `TZ`
- Volume: `/config` → database + logs
- Network: `bridge`, port 7878

---

## Phase 6 — Beyond UFC ⬜

If the core works well, the architecture trivially extends to other live sports PPVs
that Radarr also can't handle. Each needs only a new scraper + query builder.

- [ ] **Boxing** — BoxRec event list, ESPN PPV
- [ ] **WWE** — Wikipedia `{YEAR}_in_WWE`, match card
- [ ] **AEW** — Wikipedia `List_of_AEW_pay-per-view_events`
- [ ] **PFL** — Professional Fighters League season events
- [ ] **ONE Championship** — Singapore-based MMA

---

## Definition of "Looks and Works Like Radarr"

A feature is done when it passes this checklist:
- [ ] Dark theme matches Radarr's palette (near-black bg, subtle borders, accent highlight)
- [ ] Grid and table views both work on the main content page
- [ ] Every action has a loading state (spinner or disabled button)
- [ ] Every mutation shows a toast on success and on error
- [ ] Modals have backdrop, escape-to-close, and focus trap
- [ ] Settings page has tab navigation in a sidebar (not all on one page)
- [ ] Connection test buttons exist for every external service
- [ ] Keyboard navigation works (at minimum tab order is logical)
- [ ] Mobile layout doesn't break (sidebar collapses, cards reflow)
- [ ] No placeholder text that says "TODO" or "stub" visible to the user
