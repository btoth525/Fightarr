import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus, Trash2, Wifi } from "lucide-react";

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
          Configure indexers and download clients
        </p>
      </div>
      <IndexersSection />
      <DownloadClientsSection />
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
          defaultValue="5070,5080"
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
              categories: "5070,5080",
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
