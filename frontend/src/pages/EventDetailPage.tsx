import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO, differenceInDays } from "date-fns";
import { toast } from "sonner";
import {
  RefreshCw,
  Search,
  History,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  MapPin,
  Calendar,
  HardDrive,
  Download,
  AlertTriangle,
  Zap,
} from "lucide-react";
import clsx from "clsx";

import { api } from "../api/client";
import type { Event, SearchRelease, HistoryItem } from "../api/types";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const eventId = Number(id);

  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchRelease[] | null>(null);
  const [searchMessage, setSearchMessage] = useState<string | null>(null);
  const [searchErrors, setSearchErrors] = useState<string[]>([]);
  const [queriesTried, setQueriesTried] = useState<string[]>([]);

  const { data: event, isLoading } = useQuery({
    queryKey: ["event", eventId],
    queryFn: () => api.get<Event>(`/event/${eventId}`),
    enabled: !!eventId,
  });

  // All events for prev/next navigation — already cached by EventsPage
  const { data: allEvents = [] } = useQuery({
    queryKey: ["events"],
    queryFn: () => api.get<Event[]>("/event"),
    staleTime: Infinity, // use whatever's cached
  });

  // Sort by date descending; find neighbors
  const sorted = [...allEvents].sort(
    (a, b) => new Date(b.event_date).getTime() - new Date(a.event_date).getTime(),
  );
  const idx = sorted.findIndex((e) => e.id === eventId);
  const prevEvent = idx > 0 ? sorted[idx - 1] : null;
  const nextEvent = idx < sorted.length - 1 ? sorted[idx + 1] : null;

  const { data: history = [] } = useQuery({
    queryKey: ["event-history", eventId],
    queryFn: () => api.get<HistoryItem[]>(`/event/${eventId}/history`),
    enabled: isHistoryOpen && !!eventId,
  });

  const toggleMonitored = useMutation({
    mutationFn: () =>
      api.put<Event>(`/event/${eventId}`, { monitored: !event?.monitored }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["wanted"] });
      if (updated.monitored && !updated.file_path) {
        toast.success("Monitoring enabled", {
          description: "Auto-search started in the background.",
        });
      } else {
        toast.success(updated.monitored ? "Monitoring enabled" : "Monitoring disabled");
      }
    },
    onError: () => toast.error("Could not update monitor status"),
  });

  const refreshMetadata = useMutation({
    mutationFn: () => api.post<Event>(`/event/${eventId}/refresh-metadata`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      toast.success("Metadata refreshed");
    },
    onError: () => toast.error("Refresh failed"),
  });

  const autoSearch = useMutation({
    mutationFn: () =>
      api.post<{ status: string; reason?: string; download_client?: string }>(
        `/event/${eventId}/auto-search`,
      ),
    onSuccess: (data) => {
      if (data.status === "grabbed") {
        toast.success("Auto-grabbed best release", {
          description: `Sent to ${data.download_client}`,
        });
        queryClient.invalidateQueries({ queryKey: ["event", eventId] });
        queryClient.invalidateQueries({ queryKey: ["event-history", eventId] });
        queryClient.invalidateQueries({ queryKey: ["queue"] });
      } else {
        toast.warning("No grab", {
          description: data.reason ?? "No qualifying release found",
        });
      }
    },
    onError: (err) =>
      toast.error("Auto-search failed", {
        description: err instanceof Error ? err.message : undefined,
      }),
  });

  const doSearch = useMutation({
    mutationFn: () =>
      api.post<{
        releases: SearchRelease[];
        total: number;
        message?: string;
        errors?: string[];
        queries_tried?: string[];
      }>(`/event/${eventId}/search`),
    onSuccess: (data) => {
      setSearchResults(data.releases);
      setSearchMessage(data.message ?? null);
      setSearchErrors(data.errors ?? []);
      setQueriesTried(data.queries_tried ?? []);
    },
  });

  const grab = useMutation({
    mutationFn: (release: SearchRelease) =>
      api.post<{ download_client: string; job_id: string }>(`/event/${eventId}/grab`, {
        nzb_url: release.nzb_url,
        release_title: release.title,
        size_bytes: release.size_bytes,
        indexer_name: release.indexer_name,
        protocol: release.protocol,
      }),
    onSuccess: (data, release) => {
      queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      queryClient.invalidateQueries({ queryKey: ["event-history", eventId] });
      queryClient.invalidateQueries({ queryKey: ["queue"] });
      setIsSearchOpen(false);
      setIsHistoryOpen(true);
      toast.success("Release grabbed", {
        description: `${release.title.substring(0, 60)}${release.title.length > 60 ? "…" : ""} → ${data.download_client}`,
      });
    },
    onError: (err) => {
      toast.error("Grab failed", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    },
  });

  // Keyboard navigation (left/right arrows)
  const handleKeyUp = useCallback(
    (e: KeyboardEvent) => {
      if (isSearchOpen || isHistoryOpen) return;
      if (e.composedPath && e.composedPath().length === 4) {
        if (e.key === "ArrowLeft" && prevEvent) navigate(`/events/${prevEvent.id}`);
        if (e.key === "ArrowRight" && nextEvent) navigate(`/events/${nextEvent.id}`);
      }
    },
    [isSearchOpen, isHistoryOpen, prevEvent, nextEvent, navigate],
  );

  useEffect(() => {
    window.addEventListener("keyup", handleKeyUp);
    return () => window.removeEventListener("keyup", handleKeyUp);
  }, [handleKeyUp]);

  function handleOpenSearch() {
    setIsSearchOpen(true);
    if (searchResults === null) doSearch.mutate();
  }

  if (isLoading) return <div className="p-8 text-text-muted">Loading…</div>;
  if (!event) return <div className="p-8 text-status-missing">Event not found.</div>;

  const date = parseISO(event.event_date);
  const showPoster = event.poster_url && !imgError;

  return (
    <div className="-m-6 flex flex-col min-h-full">
      {/* ── Toolbar ── */}
      <div className="flex items-center justify-between px-6 py-2.5 border-b border-border bg-bg-panel shrink-0">
        <div className="flex items-center gap-1">
          <ToolbarBtn
            icon={<RefreshCw size={14} className={refreshMetadata.isPending ? "animate-spin" : ""} />}
            label="Refresh & Scan"
            onClick={() => refreshMetadata.mutate()}
            disabled={refreshMetadata.isPending}
          />
          <ToolbarBtn
            icon={<Search size={14} />}
            label="Interactive Search"
            onClick={handleOpenSearch}
          />
          <ToolbarBtn
            icon={<Zap size={14} className={autoSearch.isPending ? "animate-pulse" : ""} />}
            label={autoSearch.isPending ? "Auto-Searching…" : "Auto-Search"}
            onClick={() => autoSearch.mutate()}
            disabled={autoSearch.isPending}
          />
          <div className="w-px h-5 bg-border mx-1" />
          <ToolbarBtn
            icon={<History size={14} />}
            label="History"
            onClick={() => setIsHistoryOpen(true)}
          />
        </div>

        {/* Prev / Next navigation */}
        <div className="flex items-center gap-3">
          {prevEvent && (
            <button
              className="flex items-center gap-1 text-xs text-text-dim hover:text-text-bright transition-colors max-w-[180px]"
              onClick={() => navigate(`/events/${prevEvent.id}`)}
              title={prevEvent.title}
            >
              <ChevronLeft size={14} className="shrink-0" />
              <span className="truncate">{prevEvent.title}</span>
            </button>
          )}
          {nextEvent && (
            <button
              className="flex items-center gap-1 text-xs text-text-dim hover:text-text-bright transition-colors max-w-[180px]"
              onClick={() => navigate(`/events/${nextEvent.id}`)}
              title={nextEvent.title}
            >
              <span className="truncate">{nextEvent.title}</span>
              <ChevronRight size={14} className="shrink-0" />
            </button>
          )}
        </div>
      </div>

      {/* ── Backdrop header ── */}
      <div className="relative overflow-hidden shrink-0" style={{ height: 340 }}>
        {/* Blurred poster as backdrop */}
        {showPoster && (
          <div
            className="absolute inset-0 bg-center bg-cover"
            style={{
              backgroundImage: `url(${event.poster_url})`,
              filter: "blur(28px)",
              transform: "scale(1.15)",
              opacity: 0.35,
            }}
          />
        )}
        {/* Gradient overlay — darkens toward bottom so content is readable */}
        <div className="absolute inset-0 bg-gradient-to-t from-bg via-bg/70 to-bg/10" />

        {/* Header content */}
        <div className="relative h-full flex items-end gap-6 px-8 pb-5">
          {/* Poster — floats down 40px into content */}
          <div
            className="w-40 shrink-0 rounded-lg overflow-hidden shadow-2xl border border-white/10"
            style={{ marginBottom: -56, zIndex: 10 }}
          >
            {showPoster ? (
              <img
                src={event.poster_url!}
                alt={event.title}
                className="w-full"
                onError={() => setImgError(true)}
              />
            ) : (
              <div className="aspect-[2/3] bg-bg-elevated flex items-center justify-center">
                {event.event_number !== null ? (
                  <span className="text-5xl font-bold text-accent">{event.event_number}</span>
                ) : (
                  <span className="text-xs text-text-dim uppercase tracking-widest">Fight Night</span>
                )}
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className="flex-1 pb-1 min-w-0">
            {/* Monitor toggle + title */}
            <div className="flex items-center gap-3">
              <button
                className={clsx(
                  "w-8 h-8 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors",
                  event.monitored
                    ? "bg-accent border-accent text-black"
                    : "bg-transparent border-border/60 text-text-dim hover:border-border",
                )}
                onClick={() => toggleMonitored.mutate()}
                title={event.monitored ? "Monitored — click to unmonitor" : "Unmonitored — click to monitor"}
              >
                <span className="text-sm leading-none">{event.monitored ? "●" : "○"}</span>
              </button>
              <h1 className="text-2xl font-bold text-white leading-tight truncate">
                {event.title}
              </h1>
            </div>

            {/* Date / venue */}
            <div className="flex items-center gap-4 mt-1.5 text-sm text-text-muted flex-wrap">
              <span className="flex items-center gap-1.5">
                <Calendar size={13} />
                {format(date, "EEEE, MMMM d, yyyy")}
              </span>
              {event.venue && (
                <span className="flex items-center gap-1.5">
                  <MapPin size={13} />
                  {event.venue}{event.location && `, ${event.location}`}
                </span>
              )}
            </div>

            {/* Badges */}
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              <StatusBadge status={event.status} />
              {event.quality && (
                <span className="px-2 py-0.5 text-xs bg-bg-elevated/80 border border-border rounded text-text-muted">
                  {event.quality}
                </span>
              )}
              <span className="px-2 py-0.5 text-xs bg-bg-elevated/80 border border-border rounded text-text-dim uppercase tracking-wider">
                {event.event_type?.replace(/_/g, " ")}
              </span>
            </div>

            {/* Main event fighters */}
            {event.main_event && (
              <p className="mt-3 text-lg font-semibold text-white/90">
                {event.main_event}
                {event.co_main_event && (
                  <span className="text-text-muted font-normal text-sm ml-3">
                    | {event.co_main_event}
                  </span>
                )}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* ── Content body (below poster overlap) ── */}
      <div className="flex-1 px-8 pt-20 pb-8 space-y-6">
        {/* Details section */}
        <SectionCard title="Event Details">
          <div className="grid grid-cols-2 gap-0 divide-y divide-border">
            <InfoRow label="Status" value={<StatusBadge status={event.status} />} />
            <InfoRow label="Monitored" value={event.monitored ? "Yes" : "No"} />
            <InfoRow label="Event Type" value={event.event_type?.replace(/_/g, " ").toUpperCase() ?? "—"} />
            <InfoRow label="Event Number" value={event.event_number ?? "—"} />
            <InfoRow label="Date" value={format(date, "MMMM d, yyyy")} />
            <InfoRow label="Venue" value={event.venue ?? "—"} />
            <InfoRow label="Location" value={event.location ?? "—"} />
            <InfoRow label="Quality" value={event.quality ?? "Unknown"} />
            {event.source_url && (
              <InfoRow
                label="Source"
                value={
                  <a
                    href={event.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-accent hover:underline"
                  >
                    Wikipedia <ExternalLink size={11} />
                  </a>
                }
              />
            )}
          </div>
        </SectionCard>

        {/* File section */}
        {event.file_path && (
          <SectionCard title="File">
            <div className="px-4 py-3 flex items-center gap-3 text-sm">
              <HardDrive size={14} className="text-text-dim" />
              <span className="font-mono text-text-bright text-xs">{event.file_path}</span>
            </div>
          </SectionCard>
        )}
      </div>

      {/* ── History Modal ── */}
      <Modal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        title={`History — ${event.title}`}
        size="xl"
      >
        <HistoryModalContent items={history} />
      </Modal>

      {/* ── Interactive Search Modal ── */}
      <Modal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        title={`Interactive Search — ${event.title}`}
        size="xxl"
      >
        <InteractiveSearchContent
          results={searchResults}
          message={searchMessage}
          errors={searchErrors}
          queriesTried={queriesTried}
          isSearching={doSearch.isPending}
          onSearch={() => doSearch.mutate()}
          onGrab={(r) => grab.mutate(r)}
          grabbingTitle={grab.isPending ? (grab.variables as SearchRelease)?.title : null}
        />
      </Modal>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toolbar button
// ---------------------------------------------------------------------------

function ToolbarBtn({
  icon,
  label,
  onClick,
  disabled = false,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs text-text-muted hover:text-text-bright hover:bg-bg-elevated transition-colors disabled:opacity-40"
      onClick={onClick}
      disabled={disabled}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Section card
// ---------------------------------------------------------------------------

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-xs font-semibold text-text-dim uppercase tracking-widest mb-2">
        {title}
      </h2>
      <div className="card p-0 overflow-hidden">{children}</div>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-6 px-4 py-2.5 col-span-1">
      <span className="w-32 shrink-0 text-sm text-text-muted">{label}</span>
      <span className="text-sm text-text-bright">{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Interactive Search modal content — mirrors Radarr's InteractiveSearch table
// ---------------------------------------------------------------------------

function InteractiveSearchContent({
  results,
  message,
  errors,
  queriesTried,
  isSearching,
  onSearch,
  onGrab,
  grabbingTitle,
}: {
  results: SearchRelease[] | null;
  message: string | null;
  errors: string[];
  queriesTried: string[];
  isSearching: boolean;
  onSearch: () => void;
  onGrab: (r: SearchRelease) => void;
  grabbingTitle: string | null;
}) {
  const [showDiag, setShowDiag] = useState(false);

  return (
    <div>
      {/* Sub-header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-bg-elevated/40">
        <p className="text-xs text-text-muted">
          {isSearching
            ? "Searching indexers…"
            : results === null
            ? "Click Search to query all configured indexers."
            : results.length === 0
            ? "No releases found."
            : `${results.length} release${results.length !== 1 ? "s" : ""} found across all indexers.`}
        </p>
        <button
          className="btn-primary flex items-center gap-1.5 text-xs px-3 py-1.5"
          onClick={onSearch}
          disabled={isSearching}
        >
          <Search size={12} />
          {isSearching ? "Searching…" : "Search"}
        </button>
      </div>

      {message && (
        <div className="mx-4 mt-3 p-2.5 text-xs text-status-missing bg-status-missing/10 border border-status-missing/30 rounded">
          {message}
        </div>
      )}

      {/* Indexer errors */}
      {!isSearching && errors.length > 0 && (
        <div className="mx-4 mt-3 p-2.5 text-xs bg-status-missing/10 border border-status-missing/30 rounded space-y-1">
          <p className="font-semibold text-status-missing flex items-center gap-1.5">
            <AlertTriangle size={12} />
            {errors.length} indexer error{errors.length !== 1 ? "s" : ""}
          </p>
          {errors.map((e, i) => (
            <p key={i} className="text-status-missing/80 font-mono text-[10px] pl-4">{e}</p>
          ))}
        </div>
      )}

      {isSearching && (
        <div className="p-8 text-center text-text-muted text-sm">
          <Search size={24} className="mx-auto mb-3 animate-pulse opacity-40" />
          Querying indexers…
        </div>
      )}

      {!isSearching && results !== null && results.length === 0 && (
        <div className="p-8 text-center text-text-muted text-sm">
          <AlertTriangle size={24} className="mx-auto mb-3 opacity-40" />
          <p>No releases found.</p>
          <p className="text-xs mt-1 text-text-dim">
            Fightarr searches without a year tag — queries use the event number or date.
          </p>
          {errors.length === 0 && queriesTried.length > 0 && (
            <p className="text-xs mt-2 text-text-dim">
              Indexer returned 0 results for the queries below.
            </p>
          )}
        </div>
      )}

      {/* Diagnostic: queries tried */}
      {!isSearching && results !== null && queriesTried.length > 0 && (
        <div className="border-t border-border">
          <button
            className="w-full px-4 py-2 text-xs text-text-dim hover:text-text-muted flex items-center gap-1.5 transition-colors"
            onClick={() => setShowDiag((v) => !v)}
          >
            <span>{showDiag ? "▾" : "▸"}</span>
            Search details ({queriesTried.length} quer{queriesTried.length !== 1 ? "ies" : "y"})
          </button>
          {showDiag && (
            <div className="px-4 pb-3 space-y-1">
              <p className="text-[10px] text-text-dim italic mb-1.5">
                URLs are shown with apikey redacted. Paste into a browser (with your real apikey) to verify the indexer response.
              </p>
              {queriesTried.map((q, i) => (
                <p key={i} className="text-[10px] font-mono text-text-dim break-all leading-relaxed">{q}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {results !== null && results.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-bg-elevated/60">
                {["Source", "Age", "Title", "Quality", "Indexer", "Size", ""].map((h) => (
                  <th
                    key={h}
                    className="text-left px-3 py-2 text-text-dim font-medium uppercase tracking-wider whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sortReleases(results).map((r) => (
                <SearchResultRow
                  key={r.guid ?? r.title}
                  release={r}
                  onGrab={() => onGrab(r)}
                  isGrabbing={grabbingTitle === r.title}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SearchResultRow({
  release,
  onGrab,
  isGrabbing,
}: {
  release: SearchRelease;
  onGrab: () => void;
  isGrabbing: boolean;
}) {
  const ageDays = release.pub_date
    ? Math.abs(differenceInDays(new Date(), new Date(release.pub_date)))
    : null;

  const quality = detectQuality(release.title);
  const isPrelims = /prelim/i.test(release.title);
  const isTorrent = release.protocol === "torrent";

  return (
    <tr className="hover:bg-bg-elevated/40 transition-colors group">
      {/* Source / Protocol */}
      <td className="px-3 py-2.5 whitespace-nowrap">
        <span
          className={clsx(
            "px-1.5 py-0.5 rounded text-[10px] font-medium bg-bg-elevated border uppercase",
            isTorrent
              ? "border-blue-500/40 text-blue-400"
              : "border-accent/40 text-accent",
          )}
        >
          {isTorrent ? "Torrent" : "NZB"}
        </span>
      </td>
      {/* Age */}
      <td className="px-3 py-2.5 text-text-muted whitespace-nowrap">
        {ageDays !== null ? `${ageDays}d` : "—"}
      </td>
      {/* Title */}
      <td className="px-3 py-2.5 max-w-xs">
        <div className="flex items-center gap-1.5 flex-wrap">
          {isPrelims && (
            <span className="px-1 py-0.5 rounded text-[10px] font-medium bg-blue-500/15 border border-blue-500/30 text-blue-400 shrink-0">
              Prelims
            </span>
          )}
          <span className="font-mono text-text-bright line-clamp-1" title={release.title}>
            {release.title}
          </span>
        </div>
      </td>
      {/* Quality */}
      <td className="px-3 py-2.5 whitespace-nowrap">
        {quality ? (
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-bg-elevated border border-border text-text-muted font-mono">
            {quality}
          </span>
        ) : (
          <span className="text-text-dim">—</span>
        )}
      </td>
      {/* Indexer */}
      <td className="px-3 py-2.5 text-text-muted whitespace-nowrap">{release.indexer_name}</td>
      {/* Size */}
      <td className="px-3 py-2.5 text-text-muted whitespace-nowrap">
        {release.size_bytes ? formatBytes(release.size_bytes) : "—"}
      </td>
      {/* Grab */}
      <td className="px-3 py-2.5 text-right whitespace-nowrap">
        <button
          className="flex items-center gap-1 px-2.5 py-1 rounded bg-accent text-black text-xs font-medium hover:bg-accent/90 transition-colors disabled:opacity-40"
          onClick={onGrab}
          disabled={isGrabbing}
        >
          <Download size={11} />
          {isGrabbing ? "Grabbing…" : "Grab"}
        </button>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// History modal content
// ---------------------------------------------------------------------------

function HistoryModalContent({ items }: { items: HistoryItem[] }) {
  if (items.length === 0) {
    return (
      <div className="p-8 text-center text-text-muted text-sm">
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
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b border-border bg-bg-elevated/60">
          {["Source", "Age", "Title", "Indexer", "Status", "Size"].map((h) => (
            <th
              key={h}
              className="text-left px-3 py-2 text-text-dim font-medium uppercase tracking-wider whitespace-nowrap"
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-border">
        {items.map((item) => {
          const ageDays = item.grabbed_at
            ? Math.abs(differenceInDays(new Date(), new Date(item.grabbed_at)))
            : null;
          return (
            <tr key={item.id} className="hover:bg-bg-elevated/40 transition-colors">
              <td className="px-3 py-2.5">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-bg-elevated border border-border text-text-muted uppercase">
                  NZB
                </span>
              </td>
              <td className="px-3 py-2.5 text-text-muted whitespace-nowrap">
                {ageDays !== null ? `${ageDays}d` : "—"}
              </td>
              <td className="px-3 py-2.5 max-w-xs">
                <span
                  className="font-mono text-text-bright line-clamp-1"
                  title={item.release_title}
                >
                  {item.release_title}
                </span>
                {item.error_message && (
                  <p className="text-status-missing mt-0.5 flex items-center gap-1">
                    <AlertTriangle size={10} /> {item.error_message}
                  </p>
                )}
              </td>
              <td className="px-3 py-2.5 text-text-muted whitespace-nowrap">
                {item.indexer_name ?? "—"}
              </td>
              <td className="px-3 py-2.5 whitespace-nowrap">
                <span className={clsx("font-medium capitalize", statusColor[item.status])}>
                  {item.status}
                </span>
                {item.status === "downloading" && item.progress_percent > 0 && (
                  <span className="text-text-dim ml-1">
                    {Math.round(item.progress_percent)}%
                  </span>
                )}
              </td>
              <td className="px-3 py-2.5 text-text-muted whitespace-nowrap">
                <span className="flex items-center gap-1">
                  <HardDrive size={10} />
                  {item.release_size_bytes ? formatBytes(item.release_size_bytes) : "—"}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
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

function detectQuality(title: string): string | null {
  const t = title.toUpperCase();

  let res = "";
  if (t.includes("2160P") || t.includes("4K") || t.includes("UHD")) res = "2160p";
  else if (t.includes("1080P")) res = "1080p";
  else if (t.includes("720P")) res = "720p";
  else if (t.includes("480P")) res = "480p";

  let src = "";
  if (t.includes("WEB-DL") || t.includes("WEBDL") || t.includes("WEB DL")) src = "WEBDL";
  else if (t.includes("WEBRIP") || t.includes("WEB-RIP") || t.includes("WEB RIP")) src = "WEBRip";
  else if (t.includes("BLURAY") || t.includes("BLU-RAY") || t.includes("BLU RAY")) src = "Bluray";
  else if (t.includes("HDTV")) src = "HDTV";

  if (src && res) return `${src}-${res}`;
  if (res) return res;
  if (src) return src;
  return null;
}

const QUALITY_ORDER: Record<string, number> = {
  "WEBDL-2160p": 0, "WEBRip-2160p": 1, "Bluray-2160p": 2,
  "WEBDL-1080p": 3, "WEBRip-1080p": 4, "Bluray-1080p": 5, "HDTV-1080p": 6,
  "WEBDL-720p": 7, "WEBRip-720p": 8, "Bluray-720p": 9, "HDTV-720p": 10,
  "2160p": 11, "1080p": 12, "720p": 13, "480p": 14,
};

function sortReleases(releases: SearchRelease[]): SearchRelease[] {
  return [...releases].sort((a, b) => {
    const aPrelims = /prelim/i.test(a.title);
    const bPrelims = /prelim/i.test(b.title);
    if (aPrelims !== bPrelims) return aPrelims ? 1 : -1;
    const aQ = QUALITY_ORDER[detectQuality(a.title) ?? ""] ?? 99;
    const bQ = QUALITY_ORDER[detectQuality(b.title) ?? ""] ?? 99;
    if (aQ !== bQ) return aQ - bQ;
    return (b.size_bytes ?? 0) - (a.size_bytes ?? 0);
  });
}
