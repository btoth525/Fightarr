import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus, Trash2, Wifi, Film, HardDrive, Link2 } from "lucide-react";

import { api } from "../api/client";
import type { DownloadClient, DownloadClientType, Indexer, IndexerType } from "../api/types";

// ─── Labels ──────────────────────────────────────────────────────────────────

const CLIENT_LABELS: Record<DownloadClientType, string> = {
  sabnzbd: "SABnzbd",
  nzbget: "NZBGet",
  qbittorrent: "qBittorrent",
  deluge: "Deluge",
  transmission: "Transmission",
  real_debrid: "Real-Debrid",
};

const CLIENT_PROTOCOL: Record<DownloadClientType, "nzb" | "torrent" | "debrid"> = {
  sabnzbd: "nzb",
  nzbget: "nzb",
  qbittorrent: "torrent",
  deluge: "torrent",
  transmission: "torrent",
  real_debrid: "debrid",
};

const PROTOCOL_BADGE: Record<string, string> = {
  nzb: "bg-blue-900/40 text-blue-300",
  torrent: "bg-green-900/40 text-green-300",
  debrid: "bg-purple-900/40 text-purple-300",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold text-text-bright">Settings</h1>
        <p className="text-sm text-text-muted">
          Configure indexers, download clients, media management, and connections
        </p>
      </div>
      <MediaManagementSection />
      <IndexersSection />
      <DownloadClientsSection />
      <ConnectSection />
      <MetadataSection />
    </div>
  );
}

// ─── Indexers ─────────────────────────────────────────────────────────────────

function IndexersSection() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  const { data: indexers = [] } = useQuery({
    queryKey: ["indexers"],
    queryFn: () => api.get<Indexer[]>("/indexer"),
  });

  const createIndexer = useMutation({
    mutationFn: (data: Omit<Indexer, "id">) => api.post<Indexer>("/indexer", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indexers"] });
      setShowAdd(false);
    },
  });

  const deleteIndexer = useMutation({
    mutationFn: (id: number) => api.delete(`/indexer/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["indexers"] }),
  });

  return (
    <section className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Indexers</h2>
          <p className="text-xs text-text-muted mt-0.5">
            Newznab (NZB) and Torznab (torrent) sources
          </p>
        </div>
        <button className="btn" onClick={() => setShowAdd(!showAdd)}>
          <Plus size={14} />
          Add
        </button>
      </div>

      {indexers.length === 0 && !showAdd && (
        <p className="text-sm text-text-muted py-4">
          No indexers configured. Add a Newznab indexer (NZBGeek, DrunkenSlug,
          NZBPlanet) or a Torznab source via Prowlarr / Jackett.
        </p>
      )}

      <div className="divide-y divide-border">
        {indexers.map((idx) => (
          <div key={idx.id} className="py-2.5 flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm text-text-bright">{idx.name}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wide ${
                    idx.indexer_type === "torznab"
                      ? "bg-green-900/40 text-green-300"
                      : "bg-blue-900/40 text-blue-300"
                  }`}
                >
                  {idx.indexer_type}
                </span>
              </div>
              <div className="text-xs text-text-muted truncate">{idx.url}</div>
            </div>
            <span className="text-xs text-text-muted shrink-0">
              pri {idx.priority}
            </span>
            <button className="btn" onClick={() => deleteIndexer.mutate(idx.id)}>
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </div>

      {showAdd && (
        <IndexerForm
          onCancel={() => setShowAdd(false)}
          onSubmit={(data) => createIndexer.mutate(data)}
        />
      )}
    </section>
  );
}

function IndexerForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: Omit<Indexer, "id">) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [type, setType] = useState<IndexerType>("newznab");
  const [url, setUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [categories, setCategories] = useState("5070,5080");

  return (
    <div className="border-t border-border pt-3 space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <input
          className="input col-span-2"
          placeholder="Name (e.g. NZBGeek)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select
          className="input"
          value={type}
          onChange={(e) => setType(e.target.value as IndexerType)}
        >
          <option value="newznab">Newznab (NZB)</option>
          <option value="torznab">Torznab (Torrent)</option>
        </select>
        <input
          className="input"
          placeholder="Categories (e.g. 5070,5080)"
          value={categories}
          onChange={(e) => setCategories(e.target.value)}
        />
      </div>
      <input
        className="input w-full"
        placeholder="URL (e.g. https://api.nzbgeek.info)"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />
      <input
        className="input w-full"
        type="password"
        placeholder="API key"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
      />
      <div className="flex gap-2 justify-end pt-1">
        <button className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button
          className="btn btn-primary"
          onClick={() =>
            onSubmit({
              name,
              indexer_type: type,
              url,
              api_key: apiKey,
              enabled: true,
              priority: 25,
              categories,
            })
          }
        >
          Save
        </button>
      </div>
    </div>
  );
}

// ─── Download Clients ─────────────────────────────────────────────────────────

function DownloadClientsSection() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [testing, setTesting] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<Record<number, boolean>>({});

  const { data: clients = [] } = useQuery({
    queryKey: ["downloadclients"],
    queryFn: () => api.get<DownloadClient[]>("/downloadclient"),
  });

  const createClient = useMutation({
    mutationFn: (data: Omit<DownloadClient, "id">) =>
      api.post<DownloadClient>("/downloadclient", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["downloadclients"] });
      setShowAdd(false);
    },
  });

  const deleteClient = useMutation({
    mutationFn: (id: number) => api.delete(`/downloadclient/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["downloadclients"] }),
  });

  const testClient = async (id: number) => {
    setTesting(id);
    try {
      const result = await api.post<{ success: boolean }>(`/downloadclient/${id}/test`);
      setTestResult((prev) => ({ ...prev, [id]: result.success }));
    } finally {
      setTesting(null);
    }
  };

  return (
    <section className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Download Clients</h2>
          <p className="text-xs text-text-muted mt-0.5">
            SABnzbd · NZBGet · qBittorrent · Deluge · Transmission · Real-Debrid
          </p>
        </div>
        <button className="btn" onClick={() => setShowAdd(!showAdd)}>
          <Plus size={14} />
          Add
        </button>
      </div>

      {clients.length === 0 && !showAdd && (
        <p className="text-sm text-text-muted py-4">
          No download clients configured. Add SABnzbd or NZBGet for NZB downloads,
          a torrent client for magnet/torrent grabs, or Real-Debrid for premium
          link resolution.
        </p>
      )}

      <div className="divide-y divide-border">
        {clients.map((dc) => {
          const protocol = CLIENT_PROTOCOL[dc.client_type];
          const tested = testResult[dc.id];
          return (
            <div key={dc.id} className="py-2.5 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-text-bright">{dc.name}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wide ${PROTOCOL_BADGE[protocol]}`}
                  >
                    {CLIENT_LABELS[dc.client_type]}
                  </span>
                  {tested !== undefined && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                        tested
                          ? "bg-green-900/40 text-green-300"
                          : "bg-red-900/40 text-red-400"
                      }`}
                    >
                      {tested ? "Connected" : "Failed"}
                    </span>
                  )}
                </div>
                <div className="text-xs text-text-muted truncate">{dc.host}</div>
              </div>
              <button
                className="btn"
                disabled={testing === dc.id}
                onClick={() => testClient(dc.id)}
                title="Test connection"
              >
                <Wifi size={12} className={testing === dc.id ? "animate-pulse" : ""} />
              </button>
              <button className="btn" onClick={() => deleteClient.mutate(dc.id)}>
                <Trash2 size={12} />
              </button>
            </div>
          );
        })}
      </div>

      {showAdd && (
        <DownloadClientForm
          onCancel={() => setShowAdd(false)}
          onSubmit={(data) => createClient.mutate(data)}
        />
      )}
    </section>
  );
}

function DownloadClientForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: Omit<DownloadClient, "id">) => void;
  onCancel: () => void;
}) {
  const [clientType, setClientType] = useState<DownloadClientType>("sabnzbd");
  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [category, setCategory] = useState("ufc");

  const protocol = CLIENT_PROTOCOL[clientType];
  const isDebrid = protocol === "debrid";
  const isNzb = protocol === "nzb";
  const isTorrent = protocol === "torrent";

  return (
    <div className="border-t border-border pt-3 space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <input
          className="input col-span-2"
          placeholder="Name (e.g. SABnzbd Local)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select
          className="input col-span-2"
          value={clientType}
          onChange={(e) => setClientType(e.target.value as DownloadClientType)}
        >
          <optgroup label="NZB clients">
            <option value="sabnzbd">SABnzbd</option>
            <option value="nzbget">NZBGet</option>
          </optgroup>
          <optgroup label="Torrent clients">
            <option value="qbittorrent">qBittorrent</option>
            <option value="deluge">Deluge</option>
            <option value="transmission">Transmission</option>
          </optgroup>
          <optgroup label="Premium / Debrid">
            <option value="real_debrid">Real-Debrid</option>
          </optgroup>
        </select>
      </div>

      {!isDebrid && (
        <input
          className="input w-full"
          placeholder={
            isNzb
              ? "Host (e.g. http://localhost:8080)"
              : isTorrent
              ? "Host (e.g. http://localhost:8080)"
              : "Host"
          }
          value={host}
          onChange={(e) => setHost(e.target.value)}
        />
      )}

      {(isNzb || isDebrid) && (
        <input
          className="input w-full"
          type="password"
          placeholder={isDebrid ? "Real-Debrid API key" : "API key"}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
      )}

      {(isTorrent || clientType === "nzbget") && (
        <div className="grid grid-cols-2 gap-2">
          {clientType !== "deluge" && (
            <input
              className="input"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          )}
          <input
            className={`input ${clientType === "deluge" ? "col-span-2" : ""}`}
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
      )}

      {!isDebrid && (
        <input
          className="input w-full"
          placeholder="Category / label (default: ufc)"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
      )}

      <div className="flex gap-2 justify-end pt-1">
        <button className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button
          className="btn btn-primary"
          onClick={() =>
            onSubmit({
              name,
              client_type: clientType,
              host,
              api_key: apiKey || null,
              username: username || null,
              password: password || null,
              category: category || "ufc",
              enabled: true,
              priority: 25,
            })
          }
        >
          Save
        </button>
      </div>
    </div>
  );
}

// ─── Metadata ─────────────────────────────────────────────────────────────────

function MetadataSection() {
  const [tmdbStatus, setTmdbStatus] = useState<"idle" | "testing" | "ok" | "fail">("idle");

  async function handleTmdbTest() {
    setTmdbStatus("testing");
    try {
      const r = await api.post<{ success: boolean }>("/settings/metadata/test");
      setTmdbStatus(r.success ? "ok" : "fail");
    } catch {
      setTmdbStatus("fail");
    }
    setTimeout(() => setTmdbStatus("idle"), 3000);
  }

  return (
    <section className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Metadata</h2>
          <p className="text-xs text-text-muted mt-0.5">Poster art sources</p>
        </div>
        <Film size={16} className="text-text-dim" />
      </div>

      <div className="border-t border-border pt-3 space-y-3">
        {/* Wikipedia — always active */}
        <div className="flex items-start gap-3">
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-text-bright">Wikipedia</span>
              <span className="px-1.5 py-0.5 text-[10px] rounded bg-green-900/40 text-green-300 uppercase tracking-wide font-medium">
                Active · No key needed
              </span>
            </div>
            <p className="text-xs text-text-muted">
              Poster art from each event's Wikipedia article. Works out of the box —
              no configuration required.
            </p>
          </div>
        </div>

        {/* TMDB — optional */}
        <div className="flex items-start gap-3">
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-text-bright">TMDB</span>
              <span className="px-1.5 py-0.5 text-[10px] rounded bg-yellow-900/40 text-yellow-300 uppercase tracking-wide font-medium">
                Optional
              </span>
            </div>
            <p className="text-xs text-text-muted">
              Official promotional posters from The Movie Database. Higher quality
              for numbered PPVs. Set{" "}
              <code className="text-text font-mono text-[11px] bg-bg-input px-1 rounded">
                FIGHTARR_TMDB_API_KEY
              </code>{" "}
              to enable — free key at{" "}
              <a
                href="https://www.themoviedb.org/settings/api"
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent hover:underline"
              >
                themoviedb.org
              </a>
              .
            </p>
          </div>

          <button
            className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded border text-sm ${
              tmdbStatus === "ok"
                ? "border-status-downloaded text-status-downloaded"
                : tmdbStatus === "fail"
                ? "border-status-missing text-status-missing"
                : "border-border text-text-muted hover:text-text"
            }`}
            onClick={handleTmdbTest}
            disabled={tmdbStatus === "testing"}
          >
            <Wifi size={13} className={tmdbStatus === "testing" ? "animate-pulse" : ""} />
            {tmdbStatus === "testing"
              ? "Testing…"
              : tmdbStatus === "ok"
              ? "Connected"
              : tmdbStatus === "fail"
              ? "No key"
              : "Test"}
          </button>
        </div>

        <p className="text-xs text-text-dim bg-bg-input rounded p-2">
          Posters are fetched automatically after a schedule refresh. Use the{" "}
          <span className="text-text font-medium">Fetch Art</span> button on the Events page to
          backfill missing artwork, or hover a card and click the{" "}
          <span className="text-text font-medium">↻</span> icon to refresh a single event.
        </p>
      </div>
    </section>
  );
}

// ─── Media Management ─────────────────────────────────────────────────────────

function MediaManagementSection() {
  const { data } = useQuery({
    queryKey: ["settings-media"],
    queryFn: () => api.get<{ media_root: string; use_hardlinks: boolean }>("/settings/media"),
  });

  return (
    <section className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Media Management</h2>
          <p className="text-xs text-text-muted mt-0.5">Library root folder and import settings</p>
        </div>
        <HardDrive size={16} className="text-text-dim" />
      </div>

      <div className="border-t border-border pt-3 space-y-3">
        <div className="flex items-center justify-between py-2">
          <div>
            <div className="text-sm text-text-bright">Root Folder</div>
            <div className="text-xs text-text-muted mt-0.5">
              Where imported UFC events are stored
            </div>
          </div>
          <code className="text-xs bg-bg-input px-2 py-1 rounded text-text font-mono">
            {data?.media_root ?? "./media"}
          </code>
        </div>

        <div className="flex items-center justify-between py-2 border-t border-border">
          <div>
            <div className="text-sm text-text-bright">Use Hardlinks</div>
            <div className="text-xs text-text-muted mt-0.5">
              Hardlink instead of copying — preserves download seeding
            </div>
          </div>
          <span
            className={`px-2 py-0.5 text-xs rounded font-medium ${
              data?.use_hardlinks
                ? "bg-green-900/40 text-green-300"
                : "bg-bg-input text-text-dim"
            }`}
          >
            {data?.use_hardlinks ? "Enabled" : "Disabled"}
          </span>
        </div>

        <div className="border-t border-border pt-3">
          <p className="text-xs text-text-dim">
            Naming format:{" "}
            <code className="bg-bg-input px-1 rounded font-mono">
              UFC 300 - Pereira vs Hill (2024-04-13) [WEBDL-1080p].mkv
            </code>
          </p>
          <p className="text-xs text-text-dim mt-1">
            Set root folder via{" "}
            <code className="bg-bg-input px-1 rounded font-mono">FIGHTARR_MEDIA_ROOT</code> · hardlinks via{" "}
            <code className="bg-bg-input px-1 rounded font-mono">FIGHTARR_USE_HARDLINKS</code>
          </p>
        </div>
      </div>
    </section>
  );
}

// ─── Connect ──────────────────────────────────────────────────────────────────

type TestStatus = "idle" | "testing" | "ok" | "fail";

function ConnectSection() {
  const [plexStatus, setPlexStatus] = useState<TestStatus>("idle");
  const [jellyfinStatus, setJellyfinStatus] = useState<TestStatus>("idle");

  const { data: plexData } = useQuery({
    queryKey: ["settings-plex"],
    queryFn: () => api.get<{ host: string; token_set: boolean; section_id: string }>("/settings/connect/plex"),
  });
  const { data: jellyfinData } = useQuery({
    queryKey: ["settings-jellyfin"],
    queryFn: () => api.get<{ host: string; token_set: boolean; library_id: string }>("/settings/connect/jellyfin"),
  });

  async function testPlex() {
    setPlexStatus("testing");
    try {
      const r = await api.post<{ success: boolean }>("/settings/connect/plex/test");
      setPlexStatus(r.success ? "ok" : "fail");
    } catch {
      setPlexStatus("fail");
    }
    setTimeout(() => setPlexStatus("idle"), 3000);
  }

  async function testJellyfin() {
    setJellyfinStatus("testing");
    try {
      const r = await api.post<{ success: boolean }>("/settings/connect/jellyfin/test");
      setJellyfinStatus(r.success ? "ok" : "fail");
    } catch {
      setJellyfinStatus("fail");
    }
    setTimeout(() => setJellyfinStatus("idle"), 3000);
  }

  return (
    <section className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Connect</h2>
          <p className="text-xs text-text-muted mt-0.5">Media server notifications after import</p>
        </div>
        <Link2 size={16} className="text-text-dim" />
      </div>

      <div className="border-t border-border pt-3 space-y-3">
        {/* Plex */}
        <ConnectRow
          name="Plex Media Server"
          badge="plex"
          badgeClass="bg-orange-900/40 text-orange-300"
          host={plexData?.host ?? ""}
          configured={!!plexData?.host && !!plexData?.token_set}
          envHost="FIGHTARR_PLEX_HOST"
          envToken="FIGHTARR_PLEX_TOKEN"
          envExtra="FIGHTARR_PLEX_SECTION_ID"
          status={plexStatus}
          onTest={testPlex}
        />

        {/* Jellyfin */}
        <ConnectRow
          name="Jellyfin"
          badge="jellyfin"
          badgeClass="bg-violet-900/40 text-violet-300"
          host={jellyfinData?.host ?? ""}
          configured={!!jellyfinData?.host && !!jellyfinData?.token_set}
          envHost="FIGHTARR_JELLYFIN_HOST"
          envToken="FIGHTARR_JELLYFIN_TOKEN"
          envExtra="FIGHTARR_JELLYFIN_LIBRARY_ID"
          status={jellyfinStatus}
          onTest={testJellyfin}
        />

        <p className="text-xs text-text-dim bg-bg-input rounded p-2">
          After a successful import, Fightarr POSTs a library refresh to configured media servers
          so the event appears immediately without waiting for a scheduled scan.
        </p>
      </div>
    </section>
  );
}

function ConnectRow({
  name, badge, badgeClass, host, configured,
  envHost, envToken, envExtra, status, onTest,
}: {
  name: string;
  badge: string;
  badgeClass: string;
  host: string;
  configured: boolean;
  envHost: string;
  envToken: string;
  envExtra: string;
  status: TestStatus;
  onTest: () => void;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-bright">{name}</span>
          <span className={`px-1.5 py-0.5 text-[10px] rounded uppercase tracking-wide font-medium ${badgeClass}`}>
            {badge}
          </span>
          {configured && (
            <span className="px-1.5 py-0.5 text-[10px] rounded bg-green-900/40 text-green-300 uppercase tracking-wide font-medium">
              Configured
            </span>
          )}
        </div>
        {host ? (
          <p className="text-xs text-text-muted font-mono">{host}</p>
        ) : (
          <p className="text-xs text-text-muted">
            Set via{" "}
            <code className="bg-bg-input px-1 rounded font-mono text-[11px]">{envHost}</code>
            {" · "}
            <code className="bg-bg-input px-1 rounded font-mono text-[11px]">{envToken}</code>
            {" · "}
            <code className="bg-bg-input px-1 rounded font-mono text-[11px]">{envExtra}</code>
          </p>
        )}
      </div>

      <button
        className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded border text-sm ${
          status === "ok"
            ? "border-status-downloaded text-status-downloaded"
            : status === "fail"
            ? "border-status-missing text-status-missing"
            : "border-border text-text-muted hover:text-text"
        }`}
        onClick={onTest}
        disabled={status === "testing"}
      >
        <Wifi size={13} className={status === "testing" ? "animate-pulse" : ""} />
        {status === "testing" ? "Testing…" : status === "ok" ? "Connected" : status === "fail" ? "Failed" : "Test"}
      </button>
    </div>
  );
}
