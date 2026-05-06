import { format, parseISO } from "date-fns";
import { MapPin, Calendar as CalendarIcon } from "lucide-react";
import clsx from "clsx";

import type { Event } from "../api/types";
import StatusBadge from "./StatusBadge";

interface Props {
  event: Event;
  onToggleMonitored?: (event: Event) => void;
}

export default function EventCard({ event, onToggleMonitored }: Props) {
  const date = parseISO(event.event_date);

  return (
    <div className="card p-0 overflow-hidden flex flex-col hover:border-border-strong transition-colors">
      {/* Poster placeholder — replace with actual UFC card art when we have a metadata source */}
      <div className="relative aspect-[2/3] bg-gradient-to-br from-bg-elevated via-bg-panel to-bg-input flex items-center justify-center">
        <div className="text-center px-3">
          {event.event_number !== null ? (
            <div className="text-5xl font-bold text-accent leading-none tracking-tighter">
              {event.event_number}
            </div>
          ) : (
            <div className="text-xs text-text-dim uppercase tracking-widest font-semibold">
              Fight Night
            </div>
          )}
          <div className="mt-2 text-[10px] text-text-muted uppercase tracking-wider">
            {format(date, "MMM d, yyyy")}
          </div>
        </div>

        <div className="absolute top-2 right-2">
          <StatusBadge status={event.status} />
        </div>

        <button
          className={clsx(
            "absolute top-2 left-2 w-6 h-6 rounded-full border flex items-center justify-center text-xs",
            event.monitored
              ? "bg-accent border-accent text-black"
              : "bg-bg-panel border-border text-text-dim",
          )}
          onClick={(e) => {
            e.stopPropagation();
            onToggleMonitored?.(event);
          }}
          title={event.monitored ? "Monitored" : "Not monitored"}
        >
          {event.monitored ? "●" : "○"}
        </button>
      </div>

      <div className="p-3 flex-1 flex flex-col">
        <h3 className="text-sm font-semibold text-text-bright line-clamp-2 leading-snug">
          {event.title}
        </h3>

        {event.main_event && (
          <p className="text-xs text-text-muted mt-1 line-clamp-1">
            {event.main_event}
          </p>
        )}

        <div className="mt-auto pt-3 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-text-dim">
            <CalendarIcon size={11} />
            <span>{format(date, "EEE, MMM d")}</span>
          </div>
          {event.location && (
            <div className="flex items-center gap-1.5 text-xs text-text-dim">
              <MapPin size={11} />
              <span className="line-clamp-1">{event.location}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
