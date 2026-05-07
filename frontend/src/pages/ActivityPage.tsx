import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow, format } from "date-fns";
import {
  Trash2,
  AlertCircle,
  CheckCircle2,
  Download,
  Clock,
  Loader2,
  PackageCheck,
} from "lucide-react";
import clsx from "clsx";

import { api } from "../api/client";
import type { QueueItem } from "../api/types";

// ── helpers ────────────────────────────────────────────────────────────────

function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1_073_741_824) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  return `${(bytes / 1_073_741_824).toFixed(2)} GB`;
}

function detectQuality(title: string): string {
  const t = title.toLowerCase();
  if (t.includes("2160p") || t.includes("4k") || t.includes("uhd")) return "2160p";
  if (t.includes("1080p")) return "1080p";
  if (t.includes("720p")) return "720p";
  if (t.includes("480p")) return "480p";
  return "—";
}

function timeAgo(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true });
}

// ── status visuals ─────────────────────────────────────────────────────────

const STATUS_CFG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  grabbed: { icon: <Download size={13} />, label: "Grabbed", color: "text-accent" },
  downloading: { icon: <Loader2 size={13} className="animate-spin" />, label: "Downloading", color: "text-blue-400" },
  completed: { icon: <Clock size={13} />, label: "Processing", color: "text-yellow-400" },
  imported: { icon: <PackageCheck size={13} />, label: "Imported", color: "text-status-downloaded" },
  failed: { icon: <AlertCircle size={13} />, label: "Failed", color: "text-status-missing" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.grabbed;
  return (
    <span className={clsx("flex items-center gap-1 text-xs font-medium whitespace-nowrap", cfg.color)}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

function QualityBadge({ title }: { title: string }) {
  const q = detectQuality(title);
  if (q === "—") return <span className="text-xs text-text-dim">—</span>;
  return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-bg-elevated border border-border text-text-muted font-mono">
      {q}
    </span>
  );
}

// ── page ───────────────────────────────────────────────────────────────────

export default function ActivityPage() {
  const [tab, setTab] = useState<"queue" | "history">("queue");
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: queue = [], isLoading: qLoading } = useQuery({
    queryKey: ["queue"],
    queryFn: () => api.get<QueueItem[]>("/queue"),
    refetchInterval: 8_000,
  });

  const { data: history = [], isLoading: hLoading } = useQuery({
    queryKey: ["history"],
    queryFn: () => api.get<QueueItem[]>("/queue/history"),
    enabled: tab === "history",
    refetchInterval: tab === "history" ? 15_000 : false,
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
      <div>
        <h1 className="text-xl font-semibold text-text-bright">Activity</h1>
        <p className="text-sm text-text-muted">Downloads and import history</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        <TabBtn active={tab === "queue"} onClick={() => setTab("queue")}>
          Queue
          {queue.length > 0 && (
            <span className="ml-1.5 text-xs px-1.5 py-0.5 rounded-full bg-accent/20 text-accent font-medium">
              {queue.length}
            </span>
          )}
        </TabBtn>
        <TabBtn active={tab === "history"} onClick={() => setTab("history")}>
          History
        </TabBtn>
      </div>

      {/* Queue */}
      {tab === "queue" && (
        <>
          {qLoading && <p className="text-text-muted text-sm">Loading…</p>}
          {!qLoading && queue.length === 0 && (
            <div className="card p-12 text-center">
              <CheckCircle2 size={32} className="mx-auto text-text-dim mb-3" />
              <p className="text-text-muted">Queue is empty.</p>
              <p className="text-text-dim text-sm mt-1">
                Grabbed releases appear here while they download.
              </p>
            </div>
          )}
          {queue.length > 0 && (
            <div className="card overflow-hidden">
              <TableHeader cols="queue" />
              <div className="divide-y divide-border">
                {queue.map((item) => (
                  <QueueRow
                    key={item.id}
                    item={item}
                    onGoToEvent={() => navigate(`/events/${item.event_id}`)}
                    onRemove={() => removeItem.mutate(item.id)}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* History */}
      {tab === "history" && (
        <>
          {hLoading && <p className="text-text-muted text-sm">Loading…</p>}
          {!hLoading && history.length === 0 && (
            <div className="card p-12 text-center">
              <Clock size={32} className="mx-auto text-text-dim mb-3" />
              <p className="text-text-muted">No history yet.</p>
            </div>
          )}
          {history.length > 0 && (
            <div className="card overflow-hidden">
              <TableHeader cols="history" />
              <div className="divide-y divide-border">
                {history.map((item) => (
                  <HistoryRow
                    key={item.id}
                    item={item}
                    onGoToEvent={() => navigate(`/events/${item.event_id}`)}
                    onRemove={() => removeItem.mutate(item.id)}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── table header ───────────────────────────────────────────────────────────

function TableHeader({ cols }: { cols: "queue" | "history" }) {
  const base = "hidden md:flex px-4 py-2 border-b border-border text-xs font-semibold text-text-dim uppercase tracking-wider gap-3";
  return (
    <div className={base}>
      {cols === "queue" ? (
        <>
          <span className="flex-1">Release</span>
          <span className="w-16">Quality</span>
          <span className="w-16">Size</span>
          <span className="w-44">Progress</span>
          <span className="w-24">Indexer</span>
          <span className="w-24">Client</span>
          <span className="w-24">Status</span>
          <span className="w-8" />
        </>
      ) : (
        <>
          <span className="flex-1">Release</span>
          <span className="w-16">Quality</span>
          <span className="w-16">Size</span>
          <span className="w-36">Date</span>
          <span className="w-24">Indexer</span>
          <span className="w-24">Status</span>
          <span className="w-8" />
        </>
      )}
    </div>
  );
}

// ── queue row ──────────────────────────────────────────────────────────────

function QueueRow({
  item,
  onGoToEvent,
  onRemove,
}: {
  item: QueueItem;
  onGoToEvent: () => void;
  onRemove: () => void;
}) {
  const isFailed = item.status === "failed";

  return (
    <div className="group hover:bg-bg-elevated transition-colors">
      {/* Desktop */}
      <div className="hidden md:flex items-center gap-3 px-4 py-3">
        {/* Title */}
        <div className="flex-1 min-w-0">
          {item.event_title && (
            <button
              className="text-xs text-accent hover:underline block truncate text-left"
              onClick={onGoToEvent}
            >
              {item.event_title}
            </button>
          )}
          <p className="text-sm text-text truncate">{item.release_title}</p>
        </div>
        <div className="w-16 shrink-0"><QualityBadge title={item.release_title} /></div>
        <span className="w-16 shrink-0 text-sm text-text-muted">{formatBytes(item.release_size_bytes)}</span>
        {/* Progress */}
        <div className="w-44 flex items-center gap-2 shrink-0">
          <div className="flex-1 h-1.5 bg-bg-input rounded-full overflow-hidden">
            <div
              className={clsx("h-full rounded-full transition-all duration-500", isFailed ? "bg-status-missing" : "bg-accent")}
              style={{ width: `${Math.min(100, item.progress_percent)}%` }}
            />
          </div>
          <span className="text-xs text-text-muted w-8 text-right shrink-0">
            {item.progress_percent.toFixed(0)}%
          </span>
        </div>
        <span className="w-24 shrink-0 text-sm text-text-muted truncate">{item.indexer_name ?? "—"}</span>
        <span className="w-24 shrink-0 text-sm text-text-muted truncate">{item.download_client_name ?? "—"}</span>
        <div className="w-24 shrink-0"><StatusBadge status={item.status} /></div>
        <button
          className="w-8 opacity-0 group-hover:opacity-100 transition-opacity p-1 text-text-dim hover:text-status-missing rounded shrink-0"
          onClick={onRemove}
          title="Remove from queue"
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* Mobile */}
      <div className="md:hidden px-4 py-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            {item.event_title && (
              <button className="text-xs text-accent hover:underline block truncate text-left" onClick={onGoToEvent}>
                {item.event_title}
              </button>
            )}
            <p className="text-sm text-text truncate">{item.release_title}</p>
          </div>
          <StatusBadge status={item.status} />
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-bg-input rounded-full overflow-hidden">
            <div
              className={clsx("h-full rounded-full", isFailed ? "bg-status-missing" : "bg-accent")}
              style={{ width: `${Math.min(100, item.progress_percent)}%` }}
            />
          </div>
          <span className="text-xs text-text-muted shrink-0">{item.progress_percent.toFixed(0)}%</span>
        </div>
        <div className="flex items-center justify-between text-xs text-text-dim">
          <span>{formatBytes(item.release_size_bytes)} · {detectQuality(item.release_title)}</span>
          <button className="p-1 hover:text-status-missing" onClick={onRemove}><Trash2 size={12} /></button>
        </div>
      </div>

      {item.error_message && (
        <div className="px-4 pb-2 text-xs text-status-missing bg-status-missing/5 border-t border-status-missing/20">
          {item.error_message}
        </div>
      )}
    </div>
  );
}

// ── history row ────────────────────────────────────────────────────────────

function HistoryRow({
  item,
  onGoToEvent,
  onRemove,
}: {
  item: QueueItem;
  onGoToEvent: () => void;
  onRemove: () => void;
}) {
  const ts = item.completed_at ?? item.grabbed_at;
  const dateStr = ts ? format(new Date(ts), "MMM d, yyyy HH:mm") : "—";
  const ago = ts ? timeAgo(ts) : "";

  return (
    <div className="group hover:bg-bg-elevated transition-colors">
      {/* Desktop */}
      <div className="hidden md:flex items-center gap-3 px-4 py-3">
        <div className="flex-1 min-w-0">
          {item.event_title && (
            <button
              className="text-xs text-accent hover:underline block truncate text-left"
              onClick={onGoToEvent}
            >
              {item.event_title}
            </button>
          )}
          <p className="text-sm text-text truncate">{item.release_title}</p>
          {item.download_path && (
            <p className="text-xs text-text-dim truncate mt-0.5" title={item.download_path}>
              {item.download_path}
            </p>
          )}
          {item.error_message && (
            <p className="text-xs text-status-missing truncate mt-0.5">{item.error_message}</p>
          )}
        </div>
        <div className="w-16 shrink-0"><QualityBadge title={item.release_title} /></div>
        <span className="w-16 shrink-0 text-sm text-text-muted">{formatBytes(item.release_size_bytes)}</span>
        <div className="w-36 shrink-0">
          <p className="text-sm text-text-muted">{dateStr}</p>
          <p className="text-xs text-text-dim">{ago}</p>
        </div>
        <span className="w-24 shrink-0 text-sm text-text-muted truncate">{item.indexer_name ?? "—"}</span>
        <div className="w-24 shrink-0"><StatusBadge status={item.status} /></div>
        <button
          className="w-8 opacity-0 group-hover:opacity-100 transition-opacity p-1 text-text-dim hover:text-status-missing rounded shrink-0"
          onClick={onRemove}
          title="Remove from history"
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* Mobile */}
      <div className="md:hidden px-4 py-3 flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5">
            <StatusBadge status={item.status} />
          </div>
          {item.event_title && (
            <button className="text-xs text-accent hover:underline block truncate text-left" onClick={onGoToEvent}>
              {item.event_title}
            </button>
          )}
          <p className="text-sm text-text truncate">{item.release_title}</p>
          <p className="text-xs text-text-dim mt-0.5">{dateStr}</p>
          {item.download_path && (
            <p className="text-xs text-text-dim truncate mt-0.5">{item.download_path}</p>
          )}
        </div>
        <button className="p-1 text-text-dim hover:text-status-missing shrink-0" onClick={onRemove}>
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}

// ── tab button ─────────────────────────────────────────────────────────────

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "flex items-center px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
        active ? "border-accent text-text-bright" : "border-transparent text-text-muted hover:text-text",
      )}
    >
      {children}
    </button>
  );
}
