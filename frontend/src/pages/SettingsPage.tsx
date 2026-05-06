import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { api } from "../api/client";
import type { Indexer } from "../api/types";

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold text-text-bright">Settings</h1>
        <p className="text-sm text-text-muted">
          Configure indexers and download client
        </p>
      </div>

      <IndexersSection />
      <DownloadClientSection />
    </div>
  );
}

function IndexersSection() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  const { data: indexers = [] } = useQuery({
    queryKey: ["indexers"],
    queryFn: () => api.get<Indexer[]>("/indexer"),
  });

  const createIndexer = useMutation({
    mutationFn: (data: Omit<Indexer, "id">) =>
      api.post<Indexer>("/indexer", data),
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
        <h2 className="font-semibold text-text-bright">Indexers</h2>
        <button className="btn" onClick={() => setShowAdd(!showAdd)}>
          <Plus size={14} />
          Add
        </button>
      </div>

      {indexers.length === 0 && !showAdd && (
        <p className="text-sm text-text-muted py-4">
          No indexers configured. Add a Newznab-compatible indexer (NZBGeek,
          DrunkenSlug, NZBPlanet, etc.) to enable searching.
        </p>
      )}

      <div className="divide-y divide-border">
        {indexers.map((idx) => (
          <div key={idx.id} className="py-2 flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <div className="text-sm text-text-bright">{idx.name}</div>
              <div className="text-xs text-text-muted truncate">{idx.url}</div>
            </div>
            <span className="text-xs text-text-muted">
              priority {idx.priority}
            </span>
            <button
              className="btn"
              onClick={() => deleteIndexer.mutate(idx.id)}
            >
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
  const [url, setUrl] = useState("");
  const [apiKey, setApiKey] = useState("");

  return (
    <div className="border-t border-border pt-3 space-y-2">
      <input
        className="input w-full"
        placeholder="Name (e.g. NZBGeek)"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
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
      <div className="flex gap-2 justify-end">
        <button className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button
          className="btn btn-primary"
          onClick={() =>
            onSubmit({
              name,
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

function DownloadClientSection() {
  return (
    <section className="card p-4 space-y-3">
      <h2 className="font-semibold text-text-bright">Download Client</h2>
      <p className="text-sm text-text-muted">
        SABnzbd configuration. UI editing coming in a follow-up — for now, set
        via env vars{" "}
        <code className="text-xs bg-bg-input px-1.5 py-0.5 rounded">
          FIGHTARR_SABNZBD_URL
        </code>{" "}
        and{" "}
        <code className="text-xs bg-bg-input px-1.5 py-0.5 rounded">
          FIGHTARR_SABNZBD_APIKEY
        </code>
        .
      </p>
    </section>
  );
}
