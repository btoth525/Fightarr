# Contributing to Fightarr

Welcome. This project is small and early — everything is still up for discussion.

## Quick orientation

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy + SQLite. Lives in `backend/`.
- **Frontend:** React 18 + Vite + TypeScript + Tailwind. Lives in `frontend/`.
- **Container:** Single Docker image runs both. `docker compose up` and go.

## Local dev (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7878
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to `localhost:7878`, so the two run side-by-side.

## How to pick something to work on

Look in `docs/ROADMAP.md` — it lists every chunk of work, sized so each is a reasonable PR. Open an issue saying "I'm taking X" before starting so we don't double up.

## Code style

- **Python:** `ruff` + `black` (run `make lint` from the repo root). Type hints everywhere new.
- **TypeScript:** `eslint` + `prettier`. Strict mode is on; don't loosen it.
- Commit messages: imperative mood, short. "Add Wikipedia scraper", not "Added Wikipedia scraper" or "Adding Wikipedia scraper".

## Testing

- Backend: `pytest` from `backend/`. New code needs at least one happy-path test.
- Frontend: `vitest` from `frontend/`. Component tests for anything with non-trivial logic.

## PR rules

1. Branch off `main`. Name it `feat/something` or `fix/something`.
2. One logical change per PR. If it's getting big, split it.
3. Update `docs/ROADMAP.md` checkbox when done.
4. CI must be green.

## Questions

Open a discussion. Nothing is too small — better to ask than build the wrong thing.
