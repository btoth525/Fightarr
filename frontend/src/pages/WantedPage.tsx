import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { Search, Zap, ListChecks } from "lucide-react";
import { toast } from "sonner";

import { api } from "../api/client";
import type { Event } from "../api/types";
import StatusBadge from "../components/StatusBadge";

export default function WantedPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: events = [], isLoading } = useQuery({
    queryKey: ["wanted"],
    queryFn: () => api.get<Event[]>("/wanted/missing"),
  });

  // Auto-search-and-grab a single event (Radarr's "Search Movie" button)
  const autoSearch = useMutation({
    mutationFn: (eventId: number) =>
      api.post<{ status: string; reason?: string; download_client?: string }>(
        `/event/${eventId}/auto-search`,
      ),
    onSuccess: (data, eventId) => {
      const ev = events.find((e) => e.id === eventId);
      const label = ev?.title ?? `event #${eventId}`;
      if (data.status === "grabbed") {
        toast.success(`Grabbed ${label}`, {
          description: `Sent to ${data.download_client}`,
        });
        queryClient.invalidateQueries({ queryKey: ["wanted"] });
        queryClient.invalidateQueries({ queryKey: ["queue"] });
      } else {
        toast.warning(`No grab for ${label}`, {
          description: data.reason ?? "No qualifying release found",
        });
      }
    },
    onError: (err) => {
      toast.error("Search failed", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    },
  });

  // Bulk: trigger the search_all_wanted scheduled task immediately
  const searchAll = useMutation({
    mutationFn: () => api.post(`/system/tasks/search_all_wanted/run-now`),
    onSuccess: () => {
      toast.success("Search All triggered", {
        description: `Searching ${events.length} wanted event${events.length !== 1 ? "s" : ""} in the background. Watch Activity for grabs.`,
      });
      // Refresh queue/wanted lists shortly after
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["queue"] });
        queryClient.invalidateQueries({ queryKey: ["wanted"] });
      }, 5000);
    },
    onError: () => {
      toast.error("Could not trigger Search All");
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text-bright">Wanted</h1>
          <p className="text-sm text-text-muted">
            Monitored events with no file yet
          </p>
        </div>
        {events.length > 0 && (
          <button
            className="btn-primary flex items-center gap-1.5 text-sm shrink-0"
            disabled={searchAll.isPending}
            onClick={() => searchAll.mutate()}
          >
            <ListChecks size={14} />
            {searchAll.isPending ? "Searching…" : `Search All (${events.length})`}
          </button>
        )}
      </div>

      {isLoading && <p className="text-text-muted">Loading…</p>}

      {!isLoading && events.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-text-muted">
            Nothing wanted — every monitored event has been downloaded.
          </p>
          <p className="text-text-dim text-xs mt-2">
            Toggle the monitor button on more events to add them here.
          </p>
        </div>
      )}

      <div className="card divide-y divide-border">
        {events.map((e) => {
          const isSearching = autoSearch.isPending && autoSearch.variables === e.id;
          return (
            <div
              key={e.id}
              className="px-4 py-3 flex items-center gap-3 hover:bg-bg-elevated transition-colors"
            >
              <div className="flex-1 min-w-0">
                <button
                  className="font-medium text-text-bright hover:text-accent text-left truncate w-full"
                  onClick={() => navigate(`/events/${e.id}`)}
                >
                  {e.title}
                </button>
                <div className="text-xs text-text-muted mt-0.5">
                  {format(parseISO(e.event_date), "EEE, MMM d, yyyy")}
                  {e.location && ` · ${e.location}`}
                </div>
              </div>
              <StatusBadge status={e.status} />
              <button
                className="btn flex items-center gap-1 text-xs"
                onClick={() => navigate(`/events/${e.id}`)}
                title="Interactive search"
              >
                <Search size={11} />
                Search
              </button>
              <button
                className="btn-primary flex items-center gap-1 text-xs"
                disabled={isSearching}
                onClick={() => autoSearch.mutate(e.id)}
                title="Auto-grab the best release"
              >
                <Zap size={11} className={isSearching ? "animate-pulse" : ""} />
                {isSearching ? "Grabbing…" : "Auto-Grab"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
