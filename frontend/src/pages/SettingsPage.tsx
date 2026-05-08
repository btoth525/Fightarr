import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Plus,
  Trash2,
  Wifi,
  Film,
  HardDrive,
  Link2,
  Save,
  Check,
  X,
  Rss,
  Cloud,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";

import { api } from "../api/client";
import type {
  DownloadClient,
  DownloadClientType,
  Indexer,
  IndexerType,
  PathMapping,
} from "../api/types";

// ─── Tab navigation ───────────────────────────────────────────────────────────

const TABS = [
  { slug: "media", label: "Media Management", icon: HardDrive },
  { slug: "indexers", label: "Indexers", icon: Rss },
  { slug: "downloadclients", label: "Download Clients", icon: Cloud },
  { slug: "connect", label: "Connect", icon: Link2 },
  { slug: "metadata", label: "Metadata", icon: Film },
] as const;

type TabSlug = (typeof TABS)[number]["slug"];

function activeTabFromPath(pathname: string): TabSlug {
  const m = pathname.match(/\/settings\/([a-z]+)/);
  const found = m ? TABS.find((t) => t.slug === m[1]) : null;
  return found ? found.slug : "media";
}

// ─── App settings shape (from GET /settings) ─────────────────────────────────

interface AppSettings {
  media_root: string;
  use_hardlinks: boolean;
  tmdb_api_key: string;
  plex_host: string;
  plex_token: string;
  plex_section_id: string;
  jellyfin_host: string;
  jellyfin_token: string;
  jellyfin_library_id: string;
  webhook_url: string;
  webhook_events: string;
}

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

type SaveStatus = "idle" | "saving" | "saved" | "error";
type TestStatus = "idle" | "testing" | "ok" | "fail";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = activeTabFromPath(location.pathname);

  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/settings"),
  });

  return (
    <div className="flex gap-6 -m-6 h-full">
      {/* Left tab nav (Radarr-style) */}
      <aside className="w-56 shrink-0 border-r border-border bg-bg-panel/40 py-6 px-3 overflow-y-auto">
        <h1 className="text-lg font-semibold text-text-bright px-3 mb-3">Settings</h1>
        <nav className="space-y-0.5">
          {TABS.map(({ slug, label, icon: Icon }) => (
            <button
              key={slug}
              onClick={() => navigate(`/settings/${slug}`)}
              className={clsx(
                "w-full flex items-center gap-2.5 px-3 py-2 rounded text-sm text-left transition-colors",
                activeTab === slug
                  ? "bg-bg-elevated text-text-bright border-l-2 border-accent -ml-0.5"
                  : "text-text hover:bg-bg-elevated hover:text-text-bright",
              )}
            >
              <Icon size={14} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </aside>

      {/* Tab body */}
      <div className="flex-1 py-6 pr-6 max-w-3xl overflow-y-auto">
        {isLoading || !settings ? (
          <p className="text-text-muted text-sm">Loading…</p>
        ) : (
          <div className="space-y-6">
            {activeTab === "media" && <MediaSection settings={settings} />}
            {activeTab === "indexers" && <IndexersSection />}
            {activeTab === "downloadclients" && (
              <>
                <DownloadClientsSection />
                <PathMappingsSection />
              </>
            )}
            {activeTab === "connect" && (
              <>
                <PlexSection settings={settings} />
                <JellyfinSection settings={settings} />
                <NotificationsSection settings={settings} />
              </>
            )}
            {activeTab === "metadata" && <MetadataSection settings={settings} />}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Save button helper ───────────────────────────────────────────────────────

function SaveBtn({ status, onClick }: { status: SaveStatus; onClick: () => void }) {
  return (
    <button
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded border text-sm transition-colors ${
        status === "saved"
          ? "border-status-downloaded text-status-downloaded"
          : status === "error"
          ? "border-status-missing text-status-missing"
          : "btn"
      }`}
      onClick={onClick}
      disabled={status === "saving"}
    >
      {status === "saving" ? (
        <Save size={13} className="animate-pulse" />
      ) : status === "saved" ? (
        <Check size={13} />
      ) : status === "error" ? (
        <X size={13} />
      ) : (
        <Save size={13} />
      )}
      {status === "saving" ? "Saving…" : status === "saved" ? "Saved" : status === "error" ? "Failed" : "Save"}
    </button>
  );
}

function useSaveStatus(): [SaveStatus, (p: Promise<unknown>) => void] {
  const [status, setStatus] = useState<SaveStatus>("idle");
  const run = (p: Promise<unknown>) => {
    setStatus("saving");
    p.then(() => {
      setStatus("saved");
      setTimeout(() => setStatus("idle"), 2000);
    }).catch(() => {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    });
  };
  return [status, run];
}

// ─── Media Management ─────────────────────────────────────────────────────────

function MediaSection({ settings }: { settings: AppSettings }) {
  const qc = useQueryClient();
  const [mediaRoot, setMediaRoot] = useState(settings.media_root);
  const [hardlinks, setHardlinks] = useState(settings.use_hardlinks);
  const [saveStatus, runSave] = useSaveStatus();

  useEffect(() => {
    setMediaRoot(settings.media_root);
    setHardlinks(settings.use_hardlinks);
  }, [settings.media_root, settings.use_hardlinks]);

  function save() {
    runSave(
      api
        .put("/settings/media", { media_root: mediaRoot, use_hardlinks: hardlinks })
        .then(() => qc.invalidateQueries({ queryKey: ["settings"] })),
    );
  }

  return (
    <section className="card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Media Management</h2>
          <p className="text-xs text-text-muted mt-0.5">Library root folder and import settings</p>
        </div>
        <HardDrive size={16} className="text-text-dim" />
      </div>

      <div className="border-t border-border pt-4 space-y-3">
        <div>
          <label className="block text-sm text-text-bright mb-1">Root Folder</label>
          <input
            className="input w-full"
            value={mediaRoot}
            onChange={(e) => setMediaRoot(e.target.value)}
            placeholder="/media"
          />
          <p className="text-xs text-text-dim mt-1">Where imported UFC events are stored</p>
        </div>

        <div className="flex items-center justify-between py-1">
          <div>
            <div className="text-sm text-text-bright">Use Hardlinks</div>
            <div className="text-xs text-text-muted mt-0.5">
              {hardlinks
                ? "Hardlink — original stays in downloads (keeps NZB seedable)"
                : "Move — file is moved out of downloads into your library (default)"}
            </div>
          </div>
          <button
            onClick={() => setHardlinks((v) => !v)}
            className={`relative w-10 h-5 rounded-full transition-colors ${
              hardlinks ? "bg-accent" : "bg-bg-input border border-border"
            }`}
          >
            <span
              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                hardlinks ? "translate-x-5" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>

        <div className="pt-1">
          <p className="text-xs text-text-dim">
            Naming:{" "}
            <code className="bg-bg-input px-1 rounded font-mono">
              UFC 300 - Pereira vs Hill (2024-04-13) [WEBDL-1080p].mkv
            </code>
          </p>
        </div>

        <div className="flex justify-end">
          <SaveBtn status={saveStatus} onClick={save} />
        </div>
      </div>
    </section>
  );
}

// ─── Indexers ─────────────────────────────────────────────────────────────────

function IndexersSection() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [testing, setTesting] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<Record<number, { ok: boolean; message: string }>>({});

  const { data: indexers = [] } = useQuery({
    queryKey: ["indexers"],
    queryFn: () => api.get<Indexer[]>("/indexer"),
  });

  const createIndexer = useMutation({
    mutationFn: (data: Omit<Indexer, "id">) => api.post<Indexer>("/indexer", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["indexers"] });
      setShowAdd(false);
      toast.success("Indexer added");
    },
    onError: (err: unknown) =>
      toast.error("Failed to add indexer", {
        description: err instanceof Error ? err.message : "Unknown error",
      }),
  });

  const deleteIndexer = useMutation({
    mutationFn: (id: number) => api.delete(`/indexer/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["indexers"] });
      toast.success("Indexer removed");
    },
    onError: () => toast.error("Failed to remove indexer"),
  });

  const reorder = useMutation({
    mutationFn: (ordered: Indexer[]) =>
      api.put<Indexer[]>("/indexer/reorder", ordered.map((ix, i) => ({ id: ix.id, priority: i + 1 }))),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["indexers"] }),
    onError: () => {
      qc.invalidateQueries({ queryKey: ["indexers"] });
      toast.error("Priority update failed — list refreshed");
    },
  });

  const sorted = [...indexers].sort((a, b) => a.priority - b.priority);

  function moveUp(idx: Indexer) {
    const i = sorted.findIndex((x) => x.id === idx.id);
    if (i <= 0) return;
    const next = [...sorted];
    [next[i - 1], next[i]] = [next[i], next[i - 1]];
    reorder.mutate(next);
  }

  function moveDown(idx: Indexer) {
    const i = sorted.findIndex((x) => x.id === idx.id);
    if (i < 0 || i >= sorted.length - 1) return;
    const next = [...sorted];
    [next[i], next[i + 1]] = [next[i + 1], next[i]];
    reorder.mutate(next);
  }

  const testIndexer = async (id: number) => {
    setTesting(id);
    const ix = indexers.find((i) => i.id === id);
    try {
      const r = await api.post<{ ok: boolean; message: string }>(`/indexer/${id}/test`);
      setTestResult((prev) => ({ ...prev, [id]: r }));
      if (r.ok) {
        toast.success(`${ix?.name ?? "Indexer"} connected`, { description: r.message });
      } else {
        toast.error(`${ix?.name ?? "Indexer"} failed`, { description: r.message });
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Request failed";
      setTestResult((prev) => ({ ...prev, [id]: { ok: false, message: msg } }));
      toast.error(`${ix?.name ?? "Indexer"} unreachable`, { description: msg });
    } finally {
      setTesting(null);
    }
  };

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
          No indexers configured. Add a Newznab indexer (NZBGeek, DrunkenSlug, NZBPlanet)
          or a Torznab source via Prowlarr / Jackett.
        </p>
      )}

      <div className="divide-y divide-border">
        {sorted.map((idx, i) => {
          const tested = testResult[idx.id];
          const isFirst = i === 0;
          const isLast = i === sorted.length - 1;
          return (
            <div key={idx.id} className="py-2.5 space-y-1">
              <div className="flex items-center gap-3">
                <div className="flex flex-col shrink-0">
                  <button
                    className="text-text-dim hover:text-text disabled:opacity-20 disabled:hover:text-text-dim"
                    disabled={isFirst || reorder.isPending}
                    onClick={() => moveUp(idx)}
                    title="Move up (higher priority — searched first)"
                  >
                    <ArrowUp size={11} />
                  </button>
                  <button
                    className="text-text-dim hover:text-text disabled:opacity-20 disabled:hover:text-text-dim"
                    disabled={isLast || reorder.isPending}
                    onClick={() => moveDown(idx)}
                    title="Move down (lower priority)"
                  >
                    <ArrowDown size={11} />
                  </button>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
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
                    {tested !== undefined && (
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          tested.ok
                            ? "bg-green-900/40 text-green-300"
                            : "bg-red-900/40 text-red-400"
                        }`}
                      >
                        {tested.ok ? "Connected" : "Failed"}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-text-muted truncate">{idx.url}</div>
                </div>
                <span className="text-xs text-text-muted shrink-0 font-mono">#{idx.priority}</span>
                <button
                  className="btn"
                  disabled={testing === idx.id}
                  onClick={() => testIndexer(idx.id)}
                  title="Test connection"
                >
                  <Wifi size={12} className={testing === idx.id ? "animate-pulse" : ""} />
                </button>
                <button className="btn" onClick={() => deleteIndexer.mutate(idx.id)}>
                  <Trash2 size={12} />
                </button>
              </div>
              {tested !== undefined && !tested.ok && (
                <p className="text-xs text-status-missing px-1 ml-7">{tested.message}</p>
              )}
            </div>
          );
        })}
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
        <button className="btn" onClick={onCancel}>Cancel</button>
        <button
          className="btn btn-primary"
          onClick={() => onSubmit({ name, indexer_type: type, url, api_key: apiKey, enabled: true, priority: 25, categories })}
        >
          Save
        </button>
      </div>
    </div>
  );
}

// ─── Download Clients ─────────────────────────────────────────────────────────

function DownloadClientsSection() {
  const qc = useQueryClient();
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
      qc.invalidateQueries({ queryKey: ["downloadclients"] });
      setShowAdd(false);
      toast.success("Download client added");
    },
    onError: (err: unknown) =>
      toast.error("Failed to add download client", {
        description: err instanceof Error ? err.message : "Unknown error",
      }),
  });

  const deleteClient = useMutation({
    mutationFn: (id: number) => api.delete(`/downloadclient/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["downloadclients"] });
      toast.success("Download client removed");
    },
    onError: () => toast.error("Failed to remove download client"),
  });

  const updatePriority = useMutation({
    mutationFn: ({ dc, newPriority }: { dc: DownloadClient; newPriority: number }) =>
      api.put<DownloadClient>(`/downloadclient/${dc.id}`, { ...dc, priority: newPriority }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["downloadclients"] }),
    onError: () => {
      qc.invalidateQueries({ queryKey: ["downloadclients"] });
      toast.error("Priority update failed — list refreshed");
    },
  });

  const sortedClients = [...clients].sort((a, b) => a.priority - b.priority);

  function moveClientUp(dc: DownloadClient) {
    const i = sortedClients.findIndex((x) => x.id === dc.id);
    if (i <= 0) return;
    const target = sortedClients[i - 1];
    updatePriority.mutate({ dc, newPriority: target.priority });
    updatePriority.mutate({ dc: target, newPriority: dc.priority });
  }

  function moveClientDown(dc: DownloadClient) {
    const i = sortedClients.findIndex((x) => x.id === dc.id);
    if (i < 0 || i >= sortedClients.length - 1) return;
    const target = sortedClients[i + 1];
    updatePriority.mutate({ dc, newPriority: target.priority });
    updatePriority.mutate({ dc: target, newPriority: dc.priority });
  }

  const testClient = async (id: number) => {
    setTesting(id);
    const dc = clients.find((c) => c.id === id);
    try {
      const result = await api.post<{ success: boolean }>(`/downloadclient/${id}/test`);
      setTestResult((prev) => ({ ...prev, [id]: result.success }));
      if (result.success) {
        toast.success(`${dc?.name ?? "Client"} connected`);
      } else {
        toast.error(`${dc?.name ?? "Client"} connection failed`);
      }
    } catch (e: unknown) {
      setTestResult((prev) => ({ ...prev, [id]: false }));
      toast.error(`${dc?.name ?? "Client"} unreachable`, {
        description: e instanceof Error ? e.message : undefined,
      });
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
          No download clients configured.
        </p>
      )}

      <div className="divide-y divide-border">
        {sortedClients.map((dc, i) => {
          const protocol = CLIENT_PROTOCOL[dc.client_type];
          const tested = testResult[dc.id];
          const isFirst = i === 0;
          const isLast = i === sortedClients.length - 1;
          return (
            <div key={dc.id} className="py-2.5 flex items-center gap-3">
              <div className="flex flex-col shrink-0">
                <button
                  className="text-text-dim hover:text-text disabled:opacity-20 disabled:hover:text-text-dim"
                  disabled={isFirst || updatePriority.isPending}
                  onClick={() => moveClientUp(dc)}
                  title="Move up (used first within protocol)"
                >
                  <ArrowUp size={11} />
                </button>
                <button
                  className="text-text-dim hover:text-text disabled:opacity-20 disabled:hover:text-text-dim"
                  disabled={isLast || updatePriority.isPending}
                  onClick={() => moveClientDown(dc)}
                  title="Move down"
                >
                  <ArrowDown size={11} />
                </button>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-text-bright">{dc.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wide ${PROTOCOL_BADGE[protocol]}`}>
                    {CLIENT_LABELS[dc.client_type]}
                  </span>
                  {tested !== undefined && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${tested ? "bg-green-900/40 text-green-300" : "bg-red-900/40 text-red-400"}`}>
                      {tested ? "Connected" : "Failed"}
                    </span>
                  )}
                </div>
                <div className="text-xs text-text-muted truncate">{dc.host}</div>
              </div>
              <span className="text-xs text-text-muted shrink-0 font-mono">#{dc.priority}</span>
              <button className="btn" disabled={testing === dc.id} onClick={() => testClient(dc.id)} title="Test connection">
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
        <input className="input col-span-2" placeholder="Name (e.g. SABnzbd Local)" value={name} onChange={(e) => setName(e.target.value)} />
        <select className="input col-span-2" value={clientType} onChange={(e) => setClientType(e.target.value as DownloadClientType)}>
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
        <input className="input w-full" placeholder="Host (e.g. http://localhost:8080)" value={host} onChange={(e) => setHost(e.target.value)} />
      )}
      {(isNzb || isDebrid) && (
        <input className="input w-full" type="password" placeholder={isDebrid ? "Real-Debrid API key" : "API key"} value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
      )}
      {(isTorrent || clientType === "nzbget") && (
        <div className="grid grid-cols-2 gap-2">
          {clientType !== "deluge" && (
            <input className="input" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
          )}
          <input className={`input ${clientType === "deluge" ? "col-span-2" : ""}`} type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
      )}
      {!isDebrid && (
        <input className="input w-full" placeholder="Category / label (default: ufc)" value={category} onChange={(e) => setCategory(e.target.value)} />
      )}

      <div className="flex gap-2 justify-end pt-1">
        <button className="btn" onClick={onCancel}>Cancel</button>
        <button className="btn btn-primary" onClick={() => onSubmit({ name, client_type: clientType, host, api_key: apiKey || null, username: username || null, password: password || null, category: category || "ufc", enabled: true, priority: 25 })}>Save</button>
      </div>
    </div>
  );
}

// ─── Remote Path Mappings ─────────────────────────────────────────────────────

function PathMappingsSection() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [host, setHost] = useState("");
  const [remotePath, setRemotePath] = useState("");
  const [localPath, setLocalPath] = useState("");

  const { data: mappings = [] } = useQuery({
    queryKey: ["pathmappings"],
    queryFn: () => api.get<PathMapping[]>("/pathmapping"),
  });

  const create = useMutation({
    mutationFn: (data: { host: string; remote_path: string; local_path: string }) =>
      api.post<PathMapping>("/pathmapping", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pathmappings"] });
      setShowAdd(false);
      setHost("");
      setRemotePath("");
      setLocalPath("");
      toast.success("Path mapping added");
    },
    onError: (err) =>
      toast.error("Could not save mapping", {
        description: err instanceof Error ? err.message : undefined,
      }),
  });

  const del = useMutation({
    mutationFn: (id: number) => api.delete(`/pathmapping/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pathmappings"] });
      toast.success("Path mapping removed");
    },
  });

  return (
    <section className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Remote Path Mappings</h2>
          <p className="text-xs text-text-muted mt-0.5">
            Translate paths when Fightarr and your download client see different filesystems
          </p>
        </div>
        <button className="btn" onClick={() => setShowAdd(!showAdd)}>
          <Plus size={14} />
          Add
        </button>
      </div>

      {mappings.length === 0 && !showAdd && (
        <div className="text-xs text-text-muted py-2 space-y-1">
          <p>
            <span className="text-text-bright">Skip this section</span> if Fightarr and your download
            client (SABnzbd / NZBGet / qBit) mount the same host folder at the same path inside their
            containers — the recommended TRaSH-Guides setup.
          </p>
          <p>
            Add a mapping only if SAB reports a path like{" "}
            <code className="bg-bg-input px-1 rounded">/downloads/complete/ufc</code> but Fightarr sees
            it as <code className="bg-bg-input px-1 rounded">/data/usenet/complete/ufc</code>.
          </p>
        </div>
      )}

      {mappings.length > 0 && (
        <div className="divide-y divide-border">
          {mappings.map((m) => (
            <div key={m.id} className="py-2.5 flex items-center gap-3">
              <div className="flex-1 min-w-0 grid grid-cols-2 gap-3 text-xs">
                <div className="min-w-0">
                  <div className="text-text-dim uppercase tracking-wide text-[10px] mb-0.5">
                    Remote (download client sees)
                  </div>
                  <code className="text-text-bright font-mono truncate block">{m.remote_path}</code>
                </div>
                <div className="min-w-0">
                  <div className="text-text-dim uppercase tracking-wide text-[10px] mb-0.5">
                    Local (Fightarr sees)
                  </div>
                  <code className="text-accent font-mono truncate block">{m.local_path}</code>
                </div>
              </div>
              {m.host && <span className="text-xs text-text-muted shrink-0">{m.host}</span>}
              <button className="btn" onClick={() => del.mutate(m.id)}>
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <div className="border-t border-border pt-3 space-y-2">
          <input
            className="input w-full"
            placeholder="Host (optional, e.g. 192.168.1.10) — for documentation only"
            value={host}
            onChange={(e) => setHost(e.target.value)}
          />
          <input
            className="input w-full"
            placeholder="Remote path: how the download client sees it (e.g. /downloads/complete)"
            value={remotePath}
            onChange={(e) => setRemotePath(e.target.value)}
          />
          <input
            className="input w-full"
            placeholder="Local path: how Fightarr sees it (e.g. /data/usenet/complete)"
            value={localPath}
            onChange={(e) => setLocalPath(e.target.value)}
          />
          <div className="flex gap-2 justify-end pt-1">
            <button className="btn" onClick={() => setShowAdd(false)}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              disabled={!remotePath.trim() || !localPath.trim() || create.isPending}
              onClick={() =>
                create.mutate({
                  host: host.trim(),
                  remote_path: remotePath.trim(),
                  local_path: localPath.trim(),
                })
              }
            >
              Save
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

// ─── Plex ─────────────────────────────────────────────────────────────────────

function PlexSection({ settings }: { settings: AppSettings }) {
  const qc = useQueryClient();
  const [host, setHost] = useState(settings.plex_host);
  const [token, setToken] = useState(settings.plex_token);
  const [sectionId, setSectionId] = useState(settings.plex_section_id);
  const [saveStatus, runSave] = useSaveStatus();
  const [testStatus, setTestStatus] = useState<TestStatus>("idle");

  useEffect(() => {
    setHost(settings.plex_host);
    setToken(settings.plex_token);
    setSectionId(settings.plex_section_id);
  }, [settings.plex_host, settings.plex_token, settings.plex_section_id]);

  function save() {
    runSave(
      api
        .put("/settings/connect/plex", { plex_host: host, plex_token: token, plex_section_id: sectionId })
        .then(() => qc.invalidateQueries({ queryKey: ["settings"] })),
    );
  }

  async function test() {
    setTestStatus("testing");
    try {
      const r = await api.post<{ success: boolean }>("/settings/connect/plex/test");
      setTestStatus(r.success ? "ok" : "fail");
    } catch {
      setTestStatus("fail");
    }
    setTimeout(() => setTestStatus("idle"), 3000);
  }

  return (
    <section className="card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Plex Media Server</h2>
          <p className="text-xs text-text-muted mt-0.5">Library refresh after import</p>
        </div>
        <Link2 size={16} className="text-text-dim" />
      </div>

      <div className="border-t border-border pt-4 space-y-3">
        <div>
          <label className="block text-sm text-text-bright mb-1">Host</label>
          <input className="input w-full" placeholder="http://192.168.1.10:32400" value={host} onChange={(e) => setHost(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm text-text-bright mb-1">Token</label>
          <input className="input w-full" type="password" placeholder={settings.plex_token === "***" ? "Token configured — enter new value to change" : "X-Plex-Token"} value={token} onChange={(e) => setToken(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm text-text-bright mb-1">Library Section ID</label>
          <input className="input w-full" placeholder="Leave blank to refresh all libraries" value={sectionId} onChange={(e) => setSectionId(e.target.value)} />
        </div>
        <div className="flex gap-2 justify-end pt-1">
          <TestBtn status={testStatus} onClick={test} />
          <SaveBtn status={saveStatus} onClick={save} />
        </div>
      </div>
    </section>
  );
}

// ─── Jellyfin ─────────────────────────────────────────────────────────────────

function JellyfinSection({ settings }: { settings: AppSettings }) {
  const qc = useQueryClient();
  const [host, setHost] = useState(settings.jellyfin_host);
  const [token, setToken] = useState(settings.jellyfin_token);
  const [libraryId, setLibraryId] = useState(settings.jellyfin_library_id);
  const [saveStatus, runSave] = useSaveStatus();
  const [testStatus, setTestStatus] = useState<TestStatus>("idle");

  useEffect(() => {
    setHost(settings.jellyfin_host);
    setToken(settings.jellyfin_token);
    setLibraryId(settings.jellyfin_library_id);
  }, [settings.jellyfin_host, settings.jellyfin_token, settings.jellyfin_library_id]);

  function save() {
    runSave(
      api
        .put("/settings/connect/jellyfin", { jellyfin_host: host, jellyfin_token: token, jellyfin_library_id: libraryId })
        .then(() => qc.invalidateQueries({ queryKey: ["settings"] })),
    );
  }

  async function test() {
    setTestStatus("testing");
    try {
      const r = await api.post<{ success: boolean }>("/settings/connect/jellyfin/test");
      setTestStatus(r.success ? "ok" : "fail");
    } catch {
      setTestStatus("fail");
    }
    setTimeout(() => setTestStatus("idle"), 3000);
  }

  return (
    <section className="card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Jellyfin</h2>
          <p className="text-xs text-text-muted mt-0.5">Library refresh after import</p>
        </div>
        <Link2 size={16} className="text-text-dim" />
      </div>

      <div className="border-t border-border pt-4 space-y-3">
        <div>
          <label className="block text-sm text-text-bright mb-1">Host</label>
          <input className="input w-full" placeholder="http://192.168.1.10:8096" value={host} onChange={(e) => setHost(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm text-text-bright mb-1">API Key</label>
          <input className="input w-full" type="password" placeholder={settings.jellyfin_token === "***" ? "Token configured — enter new value to change" : "Jellyfin API key"} value={token} onChange={(e) => setToken(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm text-text-bright mb-1">Library ID</label>
          <input className="input w-full" placeholder="Leave blank to refresh all libraries" value={libraryId} onChange={(e) => setLibraryId(e.target.value)} />
        </div>
        <div className="flex gap-2 justify-end pt-1">
          <TestBtn status={testStatus} onClick={test} />
          <SaveBtn status={saveStatus} onClick={save} />
        </div>
      </div>
    </section>
  );
}

// ─── Notifications (Discord-compatible webhook) ───────────────────────────────

function NotificationsSection({ settings }: { settings: AppSettings }) {
  const qc = useQueryClient();
  const [url, setUrl] = useState(settings.webhook_url);
  const [events, setEvents] = useState(settings.webhook_events);
  const [saveStatus, runSave] = useSaveStatus();
  const [testStatus, setTestStatus] = useState<TestStatus>("idle");

  useEffect(() => {
    setUrl(settings.webhook_url);
    setEvents(settings.webhook_events);
  }, [settings.webhook_url, settings.webhook_events]);

  const allEvents = ["grab", "import", "failed", "health"];
  const enabled = new Set(events.split(",").map((s) => s.trim()).filter(Boolean));

  function toggleEvent(name: string) {
    const next = new Set(enabled);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setEvents(Array.from(next).join(","));
  }

  function save() {
    runSave(
      api
        .put("/settings/connect/webhook", { webhook_url: url, webhook_events: events })
        .then(() => qc.invalidateQueries({ queryKey: ["settings"] })),
    );
  }

  async function test() {
    setTestStatus("testing");
    try {
      const r = await api.post<{ success: boolean; message: string }>(
        "/settings/connect/webhook/test",
      );
      setTestStatus(r.success ? "ok" : "fail");
      if (r.success) toast.success("Webhook test sent", { description: r.message });
      else toast.error("Webhook test failed", { description: r.message });
    } catch (e) {
      setTestStatus("fail");
      toast.error("Webhook test failed", {
        description: e instanceof Error ? e.message : undefined,
      });
    }
    setTimeout(() => setTestStatus("idle"), 3000);
  }

  return (
    <section className="card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Notifications</h2>
          <p className="text-xs text-text-muted mt-0.5">
            Discord-compatible webhook · pings on grab / import / failure / health alerts
          </p>
        </div>
        <Link2 size={16} className="text-text-dim" />
      </div>

      <div className="border-t border-border pt-4 space-y-3">
        <div>
          <label className="block text-sm text-text-bright mb-1">Webhook URL</label>
          <input
            className="input w-full"
            type="password"
            placeholder={
              settings.webhook_url === "***"
                ? "Webhook configured — enter new URL to change"
                : "https://discord.com/api/webhooks/…"
            }
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <p className="text-xs text-text-dim mt-1">
            Discord, Slack-compatible, or any endpoint that accepts Discord embed JSON.
          </p>
        </div>

        <div>
          <label className="block text-sm text-text-bright mb-2">Events</label>
          <div className="flex flex-wrap gap-2">
            {allEvents.map((name) => {
              const on = enabled.has(name);
              return (
                <button
                  key={name}
                  onClick={() => toggleEvent(name)}
                  className={`px-3 py-1 rounded text-xs font-medium border transition-colors ${
                    on
                      ? "bg-accent/20 border-accent text-accent"
                      : "bg-bg-elevated border-border text-text-muted hover:text-text"
                  }`}
                >
                  {name}
                </button>
              );
            })}
          </div>
          <p className="text-xs text-text-dim mt-2">
            <span className="text-text-muted">grab</span> = release sent to client ·{" "}
            <span className="text-text-muted">import</span> = file moved to library ·{" "}
            <span className="text-text-muted">failed</span> = download/import failure ·{" "}
            <span className="text-text-muted">health</span> = indexer/client offline
          </p>
        </div>

        <div className="flex gap-2 justify-end pt-1">
          <TestBtn status={testStatus} onClick={test} />
          <SaveBtn status={saveStatus} onClick={save} />
        </div>
      </div>
    </section>
  );
}

// ─── Metadata (TMDB) ──────────────────────────────────────────────────────────

function MetadataSection({ settings }: { settings: AppSettings }) {
  const qc = useQueryClient();
  const [apiKey, setApiKey] = useState(settings.tmdb_api_key);
  const [saveStatus, runSave] = useSaveStatus();
  const [testStatus, setTestStatus] = useState<TestStatus>("idle");

  useEffect(() => {
    setApiKey(settings.tmdb_api_key);
  }, [settings.tmdb_api_key]);

  function save() {
    runSave(
      api
        .put("/settings/tmdb", { tmdb_api_key: apiKey })
        .then(() => qc.invalidateQueries({ queryKey: ["settings"] })),
    );
  }

  async function test() {
    setTestStatus("testing");
    try {
      const r = await api.post<{ success: boolean }>("/settings/metadata/test");
      setTestStatus(r.success ? "ok" : "fail");
    } catch {
      setTestStatus("fail");
    }
    setTimeout(() => setTestStatus("idle"), 3000);
  }

  return (
    <section className="card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-bright">Metadata</h2>
          <p className="text-xs text-text-muted mt-0.5">Poster art sources</p>
        </div>
        <Film size={16} className="text-text-dim" />
      </div>

      <div className="border-t border-border pt-4 space-y-4">
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
              Poster art from each event's Wikipedia article. Works out of the box.
            </p>
          </div>
        </div>

        {/* TMDB — optional */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-bright">TMDB</span>
            <span className="px-1.5 py-0.5 text-[10px] rounded bg-yellow-900/40 text-yellow-300 uppercase tracking-wide font-medium">
              Optional
            </span>
          </div>
          <p className="text-xs text-text-muted">
            Higher quality promotional posters. Free key at{" "}
            <a href="https://www.themoviedb.org/settings/api" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
              themoviedb.org
            </a>
            .
          </p>
          <input
            className="input w-full"
            type="password"
            placeholder={settings.tmdb_api_key === "***" ? "API key configured — enter new value to change" : "TMDB API key (optional)"}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <div className="flex gap-2 justify-end">
            <TestBtn status={testStatus} onClick={test} />
            <SaveBtn status={saveStatus} onClick={save} />
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Shared test button ───────────────────────────────────────────────────────

function TestBtn({ status, onClick }: { status: TestStatus; onClick: () => void }) {
  return (
    <button
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded border text-sm ${
        status === "ok"
          ? "border-status-downloaded text-status-downloaded"
          : status === "fail"
          ? "border-status-missing text-status-missing"
          : "border-border text-text-muted hover:text-text"
      }`}
      onClick={onClick}
      disabled={status === "testing"}
    >
      <Wifi size={13} className={status === "testing" ? "animate-pulse" : ""} />
      {status === "testing" ? "Testing…" : status === "ok" ? "Connected" : status === "fail" ? "Failed" : "Test"}
    </button>
  );
}
