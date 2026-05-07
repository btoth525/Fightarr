import { useQuery } from "@tanstack/react-query";
import { format, parseISO, isToday, isTomorrow } from "date-fns";
import { Calendar as CalendarIcon, MapPin } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import type { Event } from "../api/types";
import StatusBadge from "../components/StatusBadge";

export default function CalendarPage() {
  const navigate = useNavigate();

  const { data: events = [], isLoading } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api.get<Event[]>("/calendar"),
  });

  const groups = events.reduce<Record<string, Event[]>>((acc, e) => {
    (acc[e.event_date] ??= []).push(e);
    return acc;
  }, {});

  const sortedDates = Object.keys(groups).sort();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-bright">Calendar</h1>
        <p className="text-sm text-text-muted">Next 30 days of UFC events</p>
      </div>

      {isLoading && <p className="text-text-muted">Loading…</p>}

      {!isLoading && sortedDates.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-text-muted">No upcoming events.</p>
        </div>
      )}

      <div className="space-y-3">
        {sortedDates.map((dateStr) => {
          const date = parseISO(dateStr);
          const label = isToday(date)
            ? "Today"
            : isTomorrow(date)
              ? "Tomorrow"
              : format(date, "EEEE, MMM d");

          return (
            <div key={dateStr} className="card overflow-hidden">
              <div className="px-4 py-2 bg-bg-elevated border-b border-border flex items-center gap-2">
                <CalendarIcon size={14} className="text-accent" />
                <span className="font-medium text-text-bright">{label}</span>
                <span className="text-xs text-text-muted">
                  · {format(date, "yyyy-MM-dd")}
                </span>
              </div>
              <div className="divide-y divide-border">
                {groups[dateStr].map((e) => (
                  <button
                    key={e.id}
                    onClick={() => navigate(`/events/${e.id}`)}
                    className="w-full text-left px-4 py-3 flex items-center gap-4 hover:bg-bg-elevated transition-colors cursor-pointer"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-text-bright truncate">{e.title}</div>
                      {e.location && (
                        <div className="text-xs text-text-muted mt-0.5 flex items-center gap-1">
                          <MapPin size={10} />
                          {e.venue ? `${e.venue} · ` : ""}
                          {e.location}
                        </div>
                      )}
                    </div>
                    {e.main_event && (
                      <span className="text-xs text-text-dim hidden sm:block shrink-0">
                        {e.main_event}
                      </span>
                    )}
                    <StatusBadge status={e.status} />
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
