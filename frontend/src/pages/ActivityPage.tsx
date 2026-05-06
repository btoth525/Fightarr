import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { QueueItem } from "../api/types";

export default function ActivityPage() {
  const { data: queue = [], isLoading } = useQuery({
    queryKey: ["queue"],
    queryFn: () => api.get<QueueItem[]>("/queue"),
    refetchInterval: 5_000,
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-bright">Activity</h1>
        <p className="text-sm text-text-muted">
          Active downloads from SABnzbd
        </p>
      </div>

      {isLoading && <p className="text-text-muted">Loading…</p>}

      {!isLoading && queue.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-text-muted">Queue is empty.</p>
        </div>
      )}

      <div className="card divide-y divide-border">
        {queue.map((q) => (
          <div key={q.id} className="px-4 py-3">
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="text-sm text-text-bright truncate">
                  {q.release_title}
                </div>
                <div className="text-xs text-text-muted mt-0.5">
                  {q.status}
                </div>
              </div>
              <div className="text-sm text-text-muted shrink-0">
                {q.progress_percent.toFixed(0)}%
              </div>
            </div>
            <div className="mt-2 h-1 bg-bg-input rounded overflow-hidden">
              <div
                className="h-full bg-accent transition-all"
                style={{ width: `${q.progress_percent}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
