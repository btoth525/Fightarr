# Architecture

## Why not fork Radarr?

Radarr is ~500k lines of C# wrapped around assumptions that fight Fightarr's
job: every entity must match TMDB, every release must parse to `Title (YYYY)`,
quality profiles assume movie runtimes. The maintainers closed the UFC feature
request as **Won't Fix** ([#9215](https://github.com/Radarr/Radarr/issues/9215)).
Forking means inheriting all those assumptions plus a forever-merge burden
on upstream changes.

So Fightarr is a fresh build that **looks** like Radarr (familiar UI patterns,
similar API shape, GPL-3.0) but doesn't carry Radarr's TMDB-shaped baggage.

## Components

### Backend (`backend/`)

- **FastAPI** — async-first, OpenAPI out of the box (handy for future
  integrations like Overseerr-style request apps)
- **SQLAlchemy 2.0 + aiosqlite** — single-file SQLite, async sessions
- **APScheduler** — periodic jobs (schedule refresh, indexer search)
- **httpx** — async HTTP for scrapers, indexer calls, SAB API
- **BeautifulSoup + lxml** — HTML parsing for Wikipedia

The backend is intentionally small and modular. Each external integration
(Wikipedia, Newznab, SABnzbd, Plex) lives in its own module under
`app/scrapers/` or `app/services/` and is independently testable with
fixture data.

### Frontend (`frontend/`)

- **React 18 + TypeScript** — strict mode
- **Vite** — fast dev server, proxies `/api/*` to the backend
- **TanStack Query** — server state, polling, cache invalidation
- **Tailwind** — Radarr-inspired dark palette in `tailwind.config.js`
- **lucide-react** — consistent icons

Each page is a thin component that calls TanStack Query against the typed
API client in `src/api/`.

## Data flow

```
                ┌──────────────────┐
                │  Wikipedia       │  scraped every 6h
                │  {YEAR}_in_UFC   │
                └────────┬─────────┘
                         ▼
              ┌──────────────────────┐
              │  schedule_sync       │  upsert by slug
              └──────────┬───────────┘
                         ▼
                   ┌──────────┐
                   │ events   │
                   │ (sqlite) │
                   └────┬─────┘
                        │ wanted = monitored AND no file
                        ▼
              ┌──────────────────────┐
              │  indexer_search      │  every 30min
              └──────────┬───────────┘
                         │ best release
                         ▼
                  ┌──────────────┐
                  │   SABnzbd    │
                  └──────┬───────┘
                         │ download complete
                         ▼
              ┌──────────────────────┐
              │  post-process        │
              │  rename + move       │
              └──────────┬───────────┘
                         ▼
                    ┌─────────┐
                    │  Plex   │
                    └─────────┘
```

## Why bypass Radarr entirely?

Going through Radarr means fighting its parser at every step:
- UFC releases lack `(YYYY)` → parsed as invalid
- UFC isn't in TMDB the way movies are → can't match metadata
- Sports PPV categorization (Newznab cat 5070) isn't a movie category

Talking to SABnzbd directly is two HTTP calls and skips every one of those
problems. The tradeoff: we re-implement the small slice of Radarr we need
(scheduling, search, scoring, post-processing). The skipped 90% of Radarr
is the part that doesn't apply to us.

## State that lives where

- **SQLite** (`/data/fightarr.db`): events, indexers, queue items, future
  settings table
- **Filesystem** (`/data/library`): downloaded fight cards, organized for Plex
- **SABnzbd**: in-flight downloads (we mirror status into our queue table)
- **Plex**: nothing — Plex is a consumer, not a source of truth

## Testing strategy

- **Scrapers**: fixture HTML files, no network in tests
- **Newznab/SAB clients**: fixture XML/JSON responses
- **API endpoints**: `httpx.AsyncClient` against the FastAPI app, in-memory
  SQLite
- **Integration**: a single end-to-end test that scrapes a fixture, seeds an
  indexer with a fixture release, and verifies SAB receives the right call
