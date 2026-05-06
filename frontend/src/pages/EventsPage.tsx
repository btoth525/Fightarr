import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Search, Image } from "lucide-react";

import { api } from "../api/client";
import type { Event } from "../api/types";
import EventCard from "../components/EventCard";

type Filter = "all" | "upcoming" | "monitored";

export default function EventsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");

  const queryClient = useQueryClient();

  const { data: events = [], isLoading, error } = useQuery({
    queryKey: ["events"],
    queryFn: () => api.get<Event[]>("/event"),
    refetchInterval: 30_000,
  });

  const toggleMonitored = useMutation({
    mutationFn: (event: Event) =>
      api.put<Event>(`/event/${event.id}`, { monitored: !event.monitored }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["events"] }),
  });

  const refreshMetadata = useMutation({
    mutationFn: () => api.post("/command/refresh-metadata"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["events"] }),
  });

  const filtered = events.filter((e) => {
    if (filter === "monitored" && !e.monitored) return false;
    if (filter === "upcoming" && new Date(e.event_date) < new Date()) return false;
    if (query && !e.title.toLowerCase().includes(query.toLowerCase()))
      return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold text-text-bright">Events</h1>
          <p className="text-sm text-text-muted">
            {events.length} total · {events.filter((e) => e.monitored).length} monitored
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-dim"
            />
            <input
              className="input pl-8 w-56"
              placeholder="Search events…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          <div className="flex rounded border border-border overflow-hidden">
            {(["all", "upcoming", "monitored"] as Filter[]).map((f) => (
              <button
                key={f}
                className={`px-3 py-1.5 text-sm capitalize ${
                  filter === f
                    ? "bg-bg-elevated text-text-bright"
                    : "bg-bg-panel text-text-muted hover:text-text"
                }`}
                onClick={() => setFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>

          <button
            className="btn-secondary flex items-center gap-1.5 text-sm"
            onClick={() => refreshMetadata.mutate()}
            disabled={refreshMetadata.isPending}
            title="Fetch TMDB posters for events missing artwork"
          >
            <Image size={14} />
            {refreshMetadata.isPending ? "Fetching…" : "Fetch Art"}
          </button>
        </div>
      </div>

      {isLoading && <p className="text-text-muted">Loading…</p>}
      {error && (
        <div className="card p-4 border-status-missing/40 text-status-missing text-sm">
          Failed to load events: {(error as Error).message}
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-text-muted">
            No events yet. Hit{" "}
            <span className="text-text-bright font-medium">Refresh</span> in
            the top bar to fetch the schedule from Wikipedia.
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {filtered.map((event) => (
          <EventCard
            key={event.id}
            event={event}
            onToggleMonitored={(e) => toggleMonitored.mutate(e)}
            onMetadataRefresh={() => queryClient.invalidateQueries({ queryKey: ["events"] })}
          />
        ))}
      </div>
    </div>
  );
}
