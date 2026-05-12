<div align="center">

<img src="frontend/public/logo.svg" width="80" alt="Fightarr logo" />

# Fightarr

**UFC event manager for Usenet and Plex**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-orange.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![Status](https://img.shields.io/badge/Status-Alpha-yellow.svg)](#status)
[![GHCR](https://img.shields.io/badge/GHCR-latest-blue.svg)](https://github.com/btoth525/Fightarr/pkgs/container/fightarr)

Radarr [explicitly won't support UFC](https://github.com/Radarr/Radarr/issues/9215). Fightarr does.

</div>

---

## What it does

Fightarr is a purpose-built sibling to Radarr for UFC events. It scrapes the full UFC schedule from Wikipedia, searches your Newznab indexers automatically, sends downloads to SABnzbd, and imports the finished file directly into your Plex/Jellyfin library — renamed, poster included, source copy deleted.

| Feature | Status |
|---|---|
| Full UFC schedule from Wikipedia (PPVs, Fight Nights, On ABC) | ✅ |
| Poster art via Wikipedia REST API — no API key needed | ✅ |
| Newznab / Torznab indexer support + connection test | ✅ |
| SABnzbd, NZBGet, qBittorrent, Deluge, Transmission, Real-Debrid | ✅ |
| Interactive search — quality profiles, prelims badge, grab button | ✅ |
| Auto-grab — monitored events searched every 30 min | ✅ |
| Post-processing — move file, rename Radarr-style, download poster | ✅ |
| Auto path mapping — detects SAB/Fightarr mount mismatch on Test click | ✅ |
| Plex + Jellyfin library refresh after import | ✅ |
| Auto-delete source files from SAB after successful import | ✅ |
| Activity queue — live progress, history, blocklist | ✅ |
| Blocklist + auto-retry on download failure | ✅ |
| Event detail page — poster, card, interactive search, history | ✅ |
| Calendar view | ✅ |
| Wanted list — missing monitored events with Search All | ✅ |
| System page — status, tasks, health, logs, download logs | ✅ |
| Unraid Community Applications template | ✅ |
| Multi-arch Docker image (amd64 + arm64) on GHCR | ✅ |
| Quality profiles UI + cutoff | 📋 Planned |
| Discord / Apprise notifications | 📋 Planned |

---

## Screenshots

<table>
<tr>
<td><b>Events</b> — full UFC schedule with poster art, monitor toggle, status badges</td>
</tr>
<tr>
<td><img src="docs/screenshots/events.png" alt="Events page" /></td>
</tr>
<tr>
<td><b>Activity</b> — live download queue, history, blocklist</td>
</tr>
<tr>
<td><img src="docs/screenshots/activity.png" alt="Activity page" /></td>
</tr>
<tr>
<td><b>Settings</b> — indexers, download clients, media management, connect</td>
</tr>
<tr>
<td><img src="docs/screenshots/settings.png" alt="Settings page" /></td>
</tr>
</table>

---

## Quickstart — Unraid

1. In Unraid **Apps**, search for **Fightarr** or add the template manually from:
   `https://raw.githubusercontent.com/btoth525/Fightarr/main/docs/unraid-template.xml`
2. Set your **Downloads** path (same share SABnzbd writes to) and **Media** path (your Plex/Jellyfin library folder)
3. Start the container — open `http://[IP]:7878`
4. Go to **Settings → Download Clients**, add SABnzbd and click **Test** — Fightarr auto-detects the path mapping
5. Go to **Settings → Indexers**, add your Newznab indexer
6. Go to **Settings → Media Management**, confirm the Root Folder path
7. Find an event on the **Events** page, click the search icon to grab it

> **Path tip:** your Downloads mount and Media mount can be any path on your Unraid shares. Edit the container paths in Unraid's Docker UI — they will stick permanently (TemplateURL has been removed so Force Update won't reset them).

### Docker (non-Unraid)

```bash
docker run -d \
  --name fightarr \
  -p 7878:7878 \
  -v /your/config:/config \
  -v /your/downloads:/downloads \
  -v /your/media:/media \
  -e PUID=1000 -e PGID=1000 -e TZ=America/New_York \
  ghcr.io/btoth525/fightarr:latest
```

| URL | Purpose |
|---|---|
| `http://localhost:7878` | Web UI |
| `http://localhost:7878/api/v1` | REST API |
| `http://localhost:7878/docs` | Swagger |

---

## Path mapping

Fightarr and SABnzbd often run in separate Docker containers and see the same NAS share under different paths (SAB uses `/data/complete/`, Fightarr mounts it as `/downloads/`). When you click **Test** on a SABnzbd download client, Fightarr automatically queries SAB's config, detects the mismatch, and saves a Remote Path Mapping — no manual setup needed.

You can also manage mappings manually under **Settings → Download Clients → Remote Path Mappings**.

---

## Library output

```
{media_root}/
├── UFC 300 - Pereira vs. Hill (2024)/
│   ├── UFC 300 - Pereira vs. Hill (2024) WEBDL-1080p.mkv
│   └── poster.jpg
└── UFC Fight Night - Strickland vs. Hernandez (2026)/
    ├── UFC Fight Night - Strickland vs. Hernandez (2026) WEBDL-1080p.mkv
    └── poster.jpg
```

Plex picks up the folder name, quality tag, and poster automatically. No TMDB match required.

---

## Security note

Fightarr has no built-in authentication. Run it on your LAN or behind a VPN/reverse proxy. API keys and download client credentials are stored in SQLite — back up `fightarr.db` before updating.

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```bash
cd backend && pytest -v        # run tests
ruff check . && black --check . # lint
```

[GPL-3.0](LICENSE) — same as Radarr, Sonarr, Lidarr.
