import clsx from "clsx";
import type { EventStatus } from "../api/types";

const styles: Record<EventStatus, string> = {
  announced: "bg-status-announced/20 text-status-announced",
  upcoming: "bg-status-upcoming/20 text-status-upcoming",
  airing: "bg-accent/20 text-accent",
  released: "bg-status-missing/20 text-status-missing",
  downloaded: "bg-status-downloaded/20 text-status-downloaded",
  missing: "bg-status-missing/20 text-status-missing",
};

const labels: Record<EventStatus, string> = {
  announced: "Announced",
  upcoming: "Upcoming",
  airing: "Airing",
  released: "Released",
  downloaded: "Downloaded",
  missing: "Missing",
};

export default function StatusBadge({ status }: { status: EventStatus }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        styles[status],
      )}
    >
      {labels[status]}
    </span>
  );
}
