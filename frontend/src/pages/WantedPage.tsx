import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { format, parseISO } from "date-fns";
import { Search } from "lucide-react";

import { api } from "../api/client";
import type { Event } from "../api/types";
import StatusBadge from "../components/StatusBadge";

export default function WantedPage() {
  const [searching, setSearching] = useState<number | null>(null);
  const [searchResult, setSearchResult] = useState<Record<number, string>>({});

  const { data: events = [], isLoading } = useQuery({
    queryKey: ["wanted"],
    queryFn: () => api.get<Event[]>("/wanted/missing"),
  });

  async function handleSearch(eventId: number) {
    setSearching(eventId);
    try {
      const result = await api.post<{ releases: unknown[] }>(`/event/${eventId}/search`);
      const count = result.releases?.length ?? 0;
      setSearchResult((prev) => ({
        ...prev,
        [eventId]: count > 0 ? `${count} release${count !== 1 ? "s" : ""} found` : "No releases found",
      }));
    } catch {
      setSearchResult((prev) => ({ ...prev, [eventId]: "Search failed" }));
    } finally {
      setSearching(null);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-bright">Wanted</h1>
        <p className="text-sm text-text-muted">
          Monitored events with no file yet
        </p>
      </div>

      {isLoading && <p className="text-text-muted">Loading…</p>}

      {!isLoading && events.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-text-muted">
            Nothing wanted — every monitored event has been downloaded.
          </p>
        </div>
      )}

      <div className="card divide-y divide-border">
        {events.map((e) => (
          <div
            key={e.id}
            className="px-4 py-3 flex items-center gap-4 hover:bg-bg-elevated"
          >
            <div className="flex-1 min-w-0">
              <div className="font-medium text-text-bright">{e.title}</div>
              <div className="text-xs text-text-muted mt-0.5">
                {format(parseISO(e.event_date), "MMM d, yyyy")}
                {e.location && ` · ${e.location}`}
              </div>
              {searchResult[e.id] && (
                <div className="text-xs text-accent mt-0.5">{searchResult[e.id]}</div>
              )}
            </div>
            <StatusBadge status={e.status} />
            <button
              className="btn btn-primary text-xs flex items-center gap-1"
              disabled={searching === e.id}
              onClick={() => handleSearch(e.id)}
            >
              <Search size={11} className={searching === e.id ? "animate-pulse" : ""} />
              {searching === e.id ? "Searching…" : "Search"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
