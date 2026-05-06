import { useState } from "react";
import { format, parseISO } from "date-fns";
import { MapPin, Calendar as CalendarIcon, RefreshCw } from "lucide-react";
import clsx from "clsx";

import type { Event } from "../api/types";
import { api } from "../api/client";
import StatusBadge from "./StatusBadge";

interface Props {
  event: Event;
  onToggleMonitored?: (event: Event) => void;
  onMetadataRefresh?: (event: Event) => void;
}

export default function EventCard({ event, onToggleMonitored, onMetadataRefresh }: Props) {
  const date = parseISO(event.event_date);
  const [imgError, setImgError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const showPoster = event.poster_url && !imgError;

  async function handleRefreshMetadata(e: React.MouseEvent) {
    e.stopPropagation();
    setRefreshing(true);
    try {
      const updated = await api.post<Event>(`/event/${event.id}/refresh-metadata`);
      onMetadataRefresh?.(updated);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="card p-0 overflow-hidden flex flex-col hover:border-border-strong transition-colors group">
      {/* Poster area */}
      <div className="relative aspect-[2/3] bg-gradient-to-br from-bg-elevated via-bg-panel to-bg-input flex items-center justify-center overflow-hidden">
        {showPoster ? (
          <img
            src={event.poster_url!}
            alt={event.title}
            className="absolute inset-0 w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
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
        )}

        {/* Gradient overlay on poster so badges are readable */}
        {showPoster && (
          <div className="absolute inset-0 bg-gradient-to-t from-bg-base/80 via-transparent to-bg-base/20" />
        )}

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

        {/* Refresh metadata button — shown on hover */}
        <button
          className={clsx(
            "absolute bottom-2 right-2 w-6 h-6 rounded border border-border/60 bg-bg-panel/80",
            "flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity",
            refreshing && "opacity-100",
          )}
          onClick={handleRefreshMetadata}
          title="Refresh TMDB metadata"
        >
          <RefreshCw size={11} className={clsx("text-text-dim", refreshing && "animate-spin")} />
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
