import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Search, Image, CheckSquare, X } from "lucide-react";

import { api } from "../api/client";
import type { Event } from "../api/types";
import EventCard from "../components/EventCard";

type Filter = "all" | "upcoming" | "monitored";

export default function EventsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());

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
    if (query && !e.title.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  function toggleSelect(event: Event) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(event.id)) next.delete(event.id);
      else next.add(event.id);
      return next;
    });
  }

  function selectAll() {
    setSelected(new Set(filtered.map((e) => e.id)));
  }

  function clearSelection() {
    setSelected(new Set());
  }

  async function bulkSetMonitored(monitored: boolean) {
    const targets = events.filter((e) => selected.has(e.id));
    await Promise.all(
      targets.map((e) => api.put(`/event/${e.id}`, { monitored }))
    );
    queryClient.invalidateQueries({ queryKey: ["events"] });
    clearSelection();
  }

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold text-text-bright">Events</h1>
          <p className="text-sm text-text-muted">
            {events.length} total · {events.filter((e) => e.monitored).length} monitored
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-dim" />
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

          {selected.size === 0 && (
            <button
              className="btn-secondary flex items-center gap-1.5 text-sm"
              onClick={selectAll}
              title="Select all visible events"
            >
              <CheckSquare size={14} />
              Select All
            </button>
          )}

          <button
            className="btn-secondary flex items-center gap-1.5 text-sm"
            onClick={() => refreshMetadata.mutate()}
            disabled={refreshMetadata.isPending}
            title="Fetch poster art for events missing artwork"
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
            No events yet — the schedule syncs automatically on startup and every 6 hours.
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
            selected={selected.has(event.id)}
            onSelect={toggleSelect}
          />
        ))}
      </div>

      {/* Bulk action toolbar — floats at bottom when items are selected */}
      {selected.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-bg-elevated border border-border-strong rounded-lg px-5 py-2.5 shadow-2xl">
          <span className="text-sm text-text-muted">
            {selected.size} selected
          </span>
          <div className="w-px h-4 bg-border" />
          <button
            className="text-sm text-accent hover:text-accent/80 font-medium"
            onClick={() => bulkSetMonitored(true)}
          >
            Monitor
          </button>
          <button
            className="text-sm text-text hover:text-text-bright font-medium"
            onClick={() => bulkSetMonitored(false)}
          >
            Unmonitor
          </button>
          <div className="w-px h-4 bg-border" />
          <button
            className="text-text-dim hover:text-text transition-colors"
            onClick={clearSelection}
            title="Clear selection"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
