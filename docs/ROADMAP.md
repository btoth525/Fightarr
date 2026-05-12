# Fightarr Roadmap

Target: full feature and UX parity with Radarr, purpose-built for UFC events.

Legend: ✅ done · 🔨 in progress · ⬜ not started

---

## Phase 0 — Foundation ✅

Core infrastructure, UI shell, Wikipedia scraper, indexer client, all download client integrations. Done.

---

## Phase 1 — Core Search Loop ✅

| Feature | Status |
|---|---|
| Query builder — PPV by number, Fight Night by number + date + fighter names | ✅ |
| Newznab / Torznab search across all enabled indexers | ✅ |
| Release scorer — resolution, codec, source, size sanity | ✅ |
| Interactive search modal — quality profiles, prelims badge, grab button | ✅ |
| Auto-grab — monitored missing events searched every 30 min | ✅ |
| Event detail page — poster, metadata, history, search | ✅ |

---

## Phase 2 — Post-Processing ✅

| Feature | Status |
|---|---|
| SABnzbd queue polling — detects completion within 30 s | ✅ |
| SABnzbd history lookup by nzo_id (targeted, no scroll-off) | ✅ |
| Remote path mapping — auto-detected on download client Test click | ✅ |
| File import — async move (default) or hardlink, non-blocking | ✅ |
| Radarr-style rename — `{Title} ({Year}) {Quality}.{ext}` | ✅ |
| Poster download — `poster.jpg` into each event folder | ✅ |
| Plex + Jellyfin library refresh after import | ✅ |
| Auto-delete source files from SABnzbd after import | ✅ |
| Import failure handling — retry button, no false blocklist | ✅ |
| Blocklist + auto-retry on true download failures | ✅ |
| Webhook endpoint — SAB script triggers immediate import | ✅ |
| Docker multi-arch image (amd64 + arm64) on GHCR | ✅ |
| Unraid Community Applications template | ✅ |

---

## Phase 3 — Full Radarr UI Parity 🔨

| Feature | Status |
|---|---|
| Activity — Queue / History / Blocklist tabs | ✅ |
| System — Status / Tasks / Health / Logs tabs | ✅ |
| Settings — Media Management, Indexers, Download Clients, Connect, Metadata | ✅ |
| Wanted — Missing tab with Search All | ✅ |
| Quality profiles UI (cutoff model) | ⬜ |
| Wanted — Cutoff Unmet tab | ⬜ |
| Events page — table view toggle | ⬜ |
| Bulk actions — monitor/unmonitor/search selected | ⬜ |
| Keyboard shortcuts | ⬜ |
| Mobile layout | ⬜ |

---

## Phase 4 — Notifications & Quality of Life ⬜

| Feature | Status |
|---|---|
| Discord webhook — on grab / import / failure | ⬜ |
| Apprise integration | ⬜ |
| Tags system | ⬜ |
| Auth — form login + JWT | ⬜ |
| Settings backup / restore | ⬜ |
| Full fight card data (prelims structured) | ⬜ |

---

## Phase 5 — Beyond UFC ⬜

Boxing · WWE · AEW · ONE Championship · PFL

---

## Current version: v0.2.0 (Alpha)

The happy path works end-to-end: schedule sync → search → grab → SABnzbd → import → Plex.
