import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { format } from "date-fns";
import { Trash2, AlertCircle, CheckCircle2, Download, Clock } from "lucide-react";
import clsx from "clsx";

import { api } from "../api/client";
import type { QueueItem } from "../api/types";

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  grabbed:      <Download size={13} className="text-accent" />,
  downloading:  <Download size={13} className="text-blue-400 animate-pulse" />,
  completed:    <CheckCircle2 size={13} className="text-yellow-400" />,
  imported:     <CheckCircle2 size={13} className="text-status-downloaded" />,
  failed:       <AlertCircle size={13} className="text-status-missing" />,
};

const STATUS_LABEL: Record<string, string> = {
  grabbed:     "Grabbed",
  downloading: "Downloading",
  completed:   "Processing",
  imported:    "Imported",
  failed:      "Failed",
};

export default function ActivityPage() {
  const [tab, setTab] = useState<"queue" | "history">("queue");
  const queryClient = useQueryClient();

  const { data: queue = [], isLoading: qLoading } = useQuery({
    queryKey: ["queue"],
    queryFn: () => api.get<QueueItem[]>("/queue"),
    refetchInterval: 8_000,
  });

  const { data: history = [], isLoading: hLoading } = useQuery({
    queryKey: ["history"],
    queryFn: () => api.get<QueueItem[]>("/queue/history"),
    enabled: tab === "history",
  });

  const removeItem = useMutation({
    mutationFn: (id: number) => api.delete(`/queue/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queue"] });
      queryClient.invalidateQueries({ queryKey: ["history"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-bright">Activity</h1>
          <p className="text-sm text-text-muted">Downloads and import history</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        {(["queue", "history"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors capitalize",
              tab === t
                ? "border-accent text-text-bright"
                : "border-transparent text-text-muted hover:text-text",
            )}
          >
            {t === "queue" ? `Queue (${queue.length})` : "History"}
          </button>
        ))}
      </div>

      {/* Queue */}
      {tab === "queue" && (
        <>
          {qLoading && <p className="text-text-muted text-sm">Loading…</p>}
          {!qLoading && queue.length === 0 && (
            <div className="card p-8 text-center">
              <p className="text-text-muted">Queue is empty.</p>
            </div>
          )}
          <div className="card divide-y divide-border">
            {queue.map((item) => (
              <QueueRow key={item.id} item={item} onRemove={() => removeItem.mutate(item.id)} />
            ))}
          </div>
        </>
      )}

      {/* History */}
      {tab === "history" && (
        <>
          {hLoading && <p className="text-text-muted text-sm">Loading…</p>}
          {!hLoading && history.length === 0 && (
            <div className="card p-8 text-center">
              <p className="text-text-muted">No history yet.</p>
            </div>
          )}
          <div className="card divide-y divide-border">
            {history.map((item) => (
              <HistoryRow key={item.id} item={item} onRemove={() => removeItem.mutate(item.id)} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function QueueRow({ item, onRemove }: { item: QueueItem; onRemove: () => void }) {
  return (
    <div className="px-4 py-3 group">
      <div className="flex items-center gap-3">
        <div className="shrink-0">{STATUS_ICON[item.status] ?? STATUS_ICON.grabbed}</div>

        <div className="flex-1 min-w-0">
          <div className="text-sm text-text-bright truncate">{item.release_title}</div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-xs text-text-muted">
              {STATUS_LABEL[item.status] ?? item.status}
            </span>
            {item.indexer_name && (
              <span className="text-xs text-text-dim">{item.indexer_name}</span>
            )}
            {item.release_size_bytes != null && (
              <span className="text-xs text-text-dim">{formatBytes(item.release_size_bytes)}</span>
            )}
          </div>
        </div>

        <div className="text-sm text-text-muted shrink-0 w-10 text-right">
          {item.progress_percent.toFixed(0)}%
        </div>

        <button
          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-text-dim hover:text-status-missing"
          onClick={onRemove}
          title="Remove from queue"
        >
          <Trash2 size={13} />
        </button>
      </div>

      <div className="mt-2 h-1 bg-bg-input rounded overflow-hidden">
        <div
          className={clsx(
            "h-full transition-all rounded",
            item.status === "failed" ? "bg-status-missing" : "bg-accent",
          )}
          style={{ width: `${item.progress_percent}%` }}
        />
      </div>
    </div>
  );
}

function HistoryRow({ item, onRemove }: { item: QueueItem; onRemove: () => void }) {
  return (
    <div className="px-4 py-3 flex items-center gap-3 group hover:bg-bg-elevated">
      <div className="shrink-0">{STATUS_ICON[item.status] ?? STATUS_ICON.grabbed}</div>

      <div className="flex-1 min-w-0">
        <div className="text-sm text-text-bright truncate">{item.release_title}</div>
        <div className="flex items-center gap-3 mt-0.5">
          <span
            className={clsx(
              "text-xs",
              item.status === "failed" ? "text-status-missing" : "text-status-downloaded",
            )}
          >
            {STATUS_LABEL[item.status] ?? item.status}
          </span>
          {item.indexer_name && (
            <span className="text-xs text-text-dim">{item.indexer_name}</span>
          )}
          {item.release_size_bytes != null && (
            <span className="text-xs text-text-dim">{formatBytes(item.release_size_bytes)}</span>
          )}
        </div>
        {item.error_message && (
          <p className="text-xs text-status-missing mt-1 truncate">{item.error_message}</p>
        )}
      </div>

      {item.completed_at && (
        <div className="flex items-center gap-1 text-xs text-text-dim shrink-0">
          <Clock size={11} />
          <span>{format(new Date(item.completed_at), "MMM d, HH:mm")}</span>
        </div>
      )}

      <button
        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-text-dim hover:text-status-missing"
        onClick={onRemove}
        title="Remove from history"
      >
        <Trash2 size={13} />
      </button>
    </div>
  );
}
