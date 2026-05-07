import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import {
  ArrowLeft,
  Search,
  RefreshCw,
  Download,
  MapPin,
  Calendar,
  ExternalLink,
  Clock,
  HardDrive,
} from "lucide-react";
import clsx from "clsx";

import { api } from "../api/client";
import type { Event, SearchRelease, HistoryItem } from "../api/types";
import StatusBadge from "../components/StatusBadge";

type Tab = "overview" | "search" | "history";

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [imgError, setImgError] = useState(false);

  const eventId = Number(id);

  const { data: event, isLoading } = useQuery({
    queryKey: ["event", eventId],
    queryFn: () => api.get<Event>(`/event/${eventId}`),
    enabled: !!eventId,
  });

  const { data: history = [] } = useQuery({
    queryKey: ["event-history", eventId],
    queryFn: () => api.get<HistoryItem[]>(`/event/${eventId}/history`),
    enabled: activeTab === "history" && !!eventId,
  });

  const toggleMonitored = useMutation({
    mutationFn: () =>
      api.put<Event>(`/event/${eventId}`, { monitored: !event?.monitored }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      queryClient.invalidateQueries({ queryKey: ["events"] });
    },
  });

  const refreshMetadata = useMutation({
    mutationFn: () => api.post<Event>(`/event/${eventId}/refresh-metadata`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["event", eventId] }),
  });

  const [searchResults, setSearchResults] = useState<SearchRelease[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const doSearch = useMutation({
    mutationFn: () => api.post<{ releases: SearchRelease[]; total: number; message?: string }>(`/event/${eventId}/search`),
    onSuccess: (data) => {
      setSearchResults(data.releases);
      setSearchError(data.message ?? null);
    },
    onError: (err) => setSearchError((err as Error).message),
  });

  const grab = useMutation({
    mutationFn: (release: SearchRelease) =>
      api.post(`/event/${eventId}/grab`, {
        nzb_url: release.nzb_url,
        release_title: release.title,
        size_bytes: release.size_bytes,
        indexer_name: release.indexer_name,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      queryClient.invalidateQueries({ queryKey: ["event-history", eventId] });
      setActiveTab("history");
    },
  });

  if (isLoading) {
    return <div className="p-8 text-text-muted">Loading…</div>;
  }
  if (!event) {
    return <div className="p-8 text-status-missing">Event not found.</div>;
  }

  const date = parseISO(event.event_date);
  const showPoster = event.poster_url && !imgError;

  return (
    <div className="space-y-0 max-w-5xl">
      {/* Back nav */}
      <button
        className="flex items-center gap-1.5 text-sm text-text-muted hover:text-text mb-4"
        onClick={() => navigate(-1)}
      >
        <ArrowLeft size={14} />
        Back to Events
      </button>

      {/* Hero section */}
      <div className="card p-0 overflow-hidden mb-6">
        <div className="flex gap-0">
          {/* Poster */}
          <div className="relative w-40 shrink-0 bg-gradient-to-br from-bg-elevated via-bg-panel to-bg-input flex items-center justify-center">
            {showPoster ? (
              <img
                src={event.poster_url!}
                alt={event.title}
                className="w-full h-full object-cover"
                style={{ minHeight: 240 }}
                onError={() => setImgError(true)}
              />
            ) : (
              <div className="text-center px-3 py-8">
                {event.event_number !== null ? (
                  <div className="text-6xl font-bold text-accent leading-none tracking-tighter">
                    {event.event_number}
                  </div>
                ) : (
                  <div className="text-xs text-text-dim uppercase tracking-widest font-semibold">
                    Fight Night
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className="flex-1 p-6 min-w-0">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <h1 className="text-2xl font-bold text-text-bright leading-tight">
                  {event.title}
                </h1>
                <div className="flex items-center gap-3 mt-1 text-sm text-text-muted flex-wrap">
                  <span className="flex items-center gap-1">
                    <Calendar size={13} />
                    {format(date, "EEEE, MMMM d, yyyy")}
                  </span>
                  {event.venue && (
                    <span className="flex items-center gap-1">
                      <MapPin size={13} />
                      {event.venue}
                      {event.location && `, ${event.location}`}
                    </span>
                  )}
                </div>
              </div>
              <StatusBadge status={event.status} />
            </div>

            {event.main_event && (
              <div className="mt-3">
                <span className="text-xs text-text-dim uppercase tracking-wider">Main Event</span>
                <p className="text-base font-semibold text-text-bright mt-0.5">{event.main_event}</p>
              </div>
            )}
            {event.co_main_event && (
              <div className="mt-2">
                <span className="text-xs text-text-dim uppercase tracking-wider">Co-Main</span>
                <p className="text-sm text-text mt-0.5">{event.co_main_event}</p>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex items-center gap-2 mt-5 flex-wrap">
              {/* Monitored toggle */}
              <button
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium border transition-colors",
                  event.monitored
                    ? "bg-accent/10 border-accent text-accent hover:bg-accent/20"
                    : "bg-bg-panel border-border text-text-muted hover:border-border-strong",
                )}
                onClick={() => toggleMonitored.mutate()}
                disabled={toggleMonitored.isPending}
              >
                <span>{event.monitored ? "●" : "○"}</span>
                {event.monitored ? "Monitored" : "Unmonitored"}
              </button>

              <button
                className="btn-primary flex items-center gap-1.5 text-sm"
                onClick={() => {
                  setActiveTab("search");
                  doSearch.mutate();
                }}
                disabled={doSearch.isPending}
              >
                <Search size={14} />
                {doSearch.isPending ? "Searching…" : "Search"}
              </button>

              <button
                className="btn-secondary flex items-center gap-1.5 text-sm"
                onClick={() => refreshMetadata.mutate()}
                disabled={refreshMetadata.isPending}
              >
                <RefreshCw size={14} className={refreshMetadata.isPending ? "animate-spin" : ""} />
                Refresh Art
              </button>

              {event.source_url && (
                <a
                  href={event.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary flex items-center gap-1.5 text-sm"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink size={14} />
                  Wikipedia
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border mb-4">
        <div className="flex gap-0">
          {(["overview", "search", "history"] as Tab[]).map((tab) => (
            <button
              key={tab}
              className={clsx(
                "px-4 py-2.5 text-sm capitalize border-b-2 -mb-px transition-colors",
                activeTab === tab
                  ? "border-accent text-text-bright font-medium"
                  : "border-transparent text-text-muted hover:text-text",
              )}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
              {tab === "history" && history.length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-bg-elevated rounded-full text-text-muted">
                  {history.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <OverviewTab event={event} />
      )}
      {activeTab === "search" && (
        <SearchTab
          results={searchResults}
          error={searchError}
          isSearching={doSearch.isPending}
          onSearch={() => doSearch.mutate()}
          onGrab={(r) => grab.mutate(r)}
          grabbingTitle={grab.isPending ? (grab.variables as SearchRelease)?.title : null}
        />
      )}
      {activeTab === "history" && (
        <HistoryTab items={history} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overview tab
// ---------------------------------------------------------------------------

function OverviewTab({ event }: { event: Event }) {
  const rows: Array<{ label: string; value: string | number | null | undefined }> = [
    { label: "Status", value: event.status },
    { label: "Event Type", value: event.event_type?.replace(/_/g, " ").toUpperCase() },
    { label: "Event Number", value: event.event_number ?? "—" },
    { label: "Date", value: format(parseISO(event.event_date), "MMMM d, yyyy") },
    { label: "Venue", value: event.venue ?? "—" },
    { label: "Location", value: event.location ?? "—" },
    { label: "Main Event", value: event.main_event ?? "—" },
    { label: "Co-Main Event", value: event.co_main_event ?? "—" },
    { label: "Quality", value: event.quality ?? "Unknown" },
  ];

  return (
    <div className="card p-0 divide-y divide-border">
      {rows.map(({ label, value }) => (
        <div key={label} className="flex items-center px-4 py-3 gap-8">
          <span className="w-36 shrink-0 text-sm text-text-muted">{label}</span>
          <span className="text-sm text-text-bright">{String(value ?? "—")}</span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Search tab
// ---------------------------------------------------------------------------

function SearchTab({
  results,
  error,
  isSearching,
  onSearch,
  onGrab,
  grabbingTitle,
}: {
  results: SearchRelease[] | null;
  error: string | null;
  isSearching: boolean;
  onSearch: () => void;
  onGrab: (r: SearchRelease) => void;
  grabbingTitle: string | null;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-muted">
          {results === null
            ? "Search all configured indexers for this event."
            : results.length === 0
            ? "No releases found."
            : `${results.length} release${results.length !== 1 ? "s" : ""} found.`}
        </p>
        <button
          className="btn-primary flex items-center gap-1.5 text-sm"
          onClick={onSearch}
          disabled={isSearching}
        >
          <Search size={14} />
          {isSearching ? "Searching…" : results === null ? "Search Indexers" : "Search Again"}
        </button>
      </div>

      {error && (
        <div className="card p-3 text-sm text-status-missing border-status-missing/30">
          {error}
        </div>
      )}

      {results !== null && results.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-bg-elevated">
                <th className="text-left px-4 py-2.5 text-xs text-text-muted font-medium uppercase tracking-wider">
                  Release
                </th>
                <th className="text-left px-4 py-2.5 text-xs text-text-muted font-medium uppercase tracking-wider">
                  Indexer
                </th>
                <th className="text-right px-4 py-2.5 text-xs text-text-muted font-medium uppercase tracking-wider">
                  Size
                </th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {results.map((r) => (
                <tr key={r.guid ?? r.title} className="hover:bg-bg-elevated/50 transition-colors">
                  <td className="px-4 py-3 text-text-bright max-w-xs">
                    <span className="line-clamp-1 font-mono text-xs">{r.title}</span>
                  </td>
                  <td className="px-4 py-3 text-text-muted text-xs">{r.indexer_name}</td>
                  <td className="px-4 py-3 text-text-muted text-xs text-right whitespace-nowrap">
                    {r.size_bytes ? formatBytes(r.size_bytes) : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="flex items-center gap-1 text-xs px-2.5 py-1 rounded bg-accent/10 border border-accent/40 text-accent hover:bg-accent/20 transition-colors disabled:opacity-40"
                      onClick={() => onGrab(r)}
                      disabled={grabbingTitle === r.title}
                    >
                      <Download size={11} />
                      {grabbingTitle === r.title ? "Grabbing…" : "Grab"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// History tab
// ---------------------------------------------------------------------------

function HistoryTab({ items }: { items: HistoryItem[] }) {
  if (items.length === 0) {
    return (
      <div className="card p-8 text-center text-text-muted text-sm">
        No download history for this event yet.
      </div>
    );
  }

  const statusColor: Record<string, string> = {
    grabbed: "text-status-upcoming",
    downloading: "text-status-airing",
    completed: "text-status-released",
    failed: "text-status-missing",
    imported: "text-status-downloaded",
  };

  return (
    <div className="card p-0 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-bg-elevated">
            <th className="text-left px-4 py-2.5 text-xs text-text-muted font-medium uppercase tracking-wider">
              Release
            </th>
            <th className="text-left px-4 py-2.5 text-xs text-text-muted font-medium uppercase tracking-wider">
              Indexer
            </th>
            <th className="text-left px-4 py-2.5 text-xs text-text-muted font-medium uppercase tracking-wider">
              Status
            </th>
            <th className="text-right px-4 py-2.5 text-xs text-text-muted font-medium uppercase tracking-wider">
              Size
            </th>
            <th className="text-right px-4 py-2.5 text-xs text-text-muted font-medium uppercase tracking-wider">
              Grabbed
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-bg-elevated/50 transition-colors">
              <td className="px-4 py-3 max-w-xs">
                <span className="line-clamp-1 font-mono text-xs text-text-bright">
                  {item.release_title}
                </span>
                {item.error_message && (
                  <p className="text-xs text-status-missing mt-0.5">{item.error_message}</p>
                )}
              </td>
              <td className="px-4 py-3 text-xs text-text-muted">{item.indexer_name ?? "—"}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <span className={clsx("text-xs font-medium capitalize", statusColor[item.status])}>
                    {item.status}
                  </span>
                  {item.status === "downloading" && item.progress_percent > 0 && (
                    <span className="text-xs text-text-dim">
                      {Math.round(item.progress_percent)}%
                    </span>
                  )}
                </div>
              </td>
              <td className="px-4 py-3 text-xs text-text-muted text-right whitespace-nowrap">
                <span className="flex items-center justify-end gap-1">
                  <HardDrive size={11} />
                  {item.release_size_bytes ? formatBytes(item.release_size_bytes) : "—"}
                </span>
              </td>
              <td className="px-4 py-3 text-xs text-text-muted text-right whitespace-nowrap">
                <span className="flex items-center justify-end gap-1">
                  <Clock size={11} />
                  {item.grabbed_at
                    ? format(new Date(item.grabbed_at), "MMM d, HH:mm")
                    : "—"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatBytes(bytes: number): string {
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(1)} GB`;
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(0)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}
