import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, Download, AlertTriangle, CheckCircle2 } from "lucide-react";

import { api } from "../api/client";
import type { ScheduledTask } from "../api/types";

interface SystemStatus {
  appName: string;
  version: string;
  branch: string;
}

interface HealthFailure {
  kind: "indexer" | "download_client";
  name: string;
  message: string;
}

interface SystemHealth {
  checked_at: string | null;
  indexers_checked: number;
  clients_checked: number;
  failures: HealthFailure[];
}

const CURRENT_YEAR = new Date().getFullYear();

const PRESETS = [
  { label: "This Year", from: CURRENT_YEAR, to: CURRENT_YEAR },
  { label: "Last 2 Years", from: CURRENT_YEAR - 1, to: CURRENT_YEAR },
  { label: "Last 5 Years", from: CURRENT_YEAR - 4, to: CURRENT_YEAR },
  { label: "All Time", from: 2001, to: CURRENT_YEAR + 1 },
];

export default function SystemPage() {
  const queryClient = useQueryClient();

  const [fromYear, setFromYear] = useState(CURRENT_YEAR);
  const [toYear, setToYear] = useState(CURRENT_YEAR + 1);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["system-status"],
    queryFn: () => api.get<SystemStatus>("/system/status"),
  });

  const { data: tasks = [], isLoading: tasksLoading } = useQuery({
    queryKey: ["system-tasks"],
    queryFn: () => api.get<ScheduledTask[]>("/system/tasks"),
    refetchInterval: 15_000,
  });

  const { data: health } = useQuery({
    queryKey: ["system-health"],
    queryFn: () => api.get<SystemHealth>("/system/health"),
    refetchInterval: 30_000,
  });

  const runNow = useMutation({
    mutationFn: (jobId: string) =>
      api.post(`/system/tasks/${jobId}/run-now`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["system-tasks"] }),
  });

  const syncYears = useMutation({
    mutationFn: (vars: { from_year: number; to_year: number }) =>
      api.post<{ events_synced: number; years: number[] }>("/command/sync-years", vars),
    onSuccess: (data) => {
      setSyncResult(
        `Synced ${data.events_synced} events across ${data.years.length} year(s).`
      );
      queryClient.invalidateQueries({ queryKey: ["events"] });
    },
    onError: () => setSyncResult("Sync failed — check logs."),
  });

  const unmonitorAll = useMutation({
    mutationFn: () => api.post("/command/unmonitor-all"),
    onSuccess: () => {
      setSyncResult("All events set to unmonitored.");
      queryClient.invalidateQueries({ queryKey: ["events"] });
    },
  });

  function applyPreset(from: number, to: number) {
    setFromYear(from);
    setToYear(to);
    setSyncResult(null);
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-semibold text-text-bright">System</h1>
        <p className="text-sm text-text-muted">Application status and scheduled tasks</p>
      </div>

      {/* Status */}
      <section>
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-2">
          Status
        </h2>
        {statusLoading ? (
          <p className="text-text-muted text-sm">Loading…</p>
        ) : status ? (
          <div className="card p-4 space-y-2">
            <Row label="Application" value={status.appName} />
            <Row label="Version" value={status.version} />
            <Row label="Branch" value={status.branch} />
          </div>
        ) : null}
      </section>

      {/* Historical / Future Sync */}
      <section>
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-2">
          Load Events by Year
        </h2>
        <div className="card p-4 space-y-4">
          <p className="text-xs text-text-muted">
            Scrape Wikipedia for UFC events in a custom year range. New events are added
            as <span className="text-text-bright">unmonitored</span> so nothing is grabbed
            automatically until you decide to monitor it.
          </p>

          {/* Presets */}
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                className="btn-secondary text-xs px-3 py-1"
                onClick={() => applyPreset(p.from, p.to)}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Year inputs */}
          <div className="flex items-center gap-3">
            <label className="text-sm text-text-muted shrink-0">From</label>
            <input
              type="number"
              className="input w-24"
              min={2001}
              max={CURRENT_YEAR + 2}
              value={fromYear}
              onChange={(e) => {
                const v = Number(e.target.value);
                setFromYear(v);
                if (v > toYear) setToYear(v);
                setSyncResult(null);
              }}
            />
            <label className="text-sm text-text-muted shrink-0">To</label>
            <input
              type="number"
              className="input w-24"
              min={fromYear}
              max={CURRENT_YEAR + 2}
              value={toYear}
              onChange={(e) => {
                setToYear(Number(e.target.value));
                setSyncResult(null);
              }}
            />
            <button
              className="btn-primary flex items-center gap-1.5 text-sm"
              disabled={syncYears.isPending}
              onClick={() =>
                syncYears.mutate({ from_year: fromYear, to_year: toYear })
              }
            >
              <Download size={14} />
              {syncYears.isPending ? "Syncing…" : "Sync"}
            </button>
          </div>

          {syncResult && (
            <p className="text-sm text-accent">{syncResult}</p>
          )}

          <hr className="border-border" />

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-bright">Unmonitor All Events</p>
              <p className="text-xs text-text-muted mt-0.5">
                Reset every event to unmonitored — useful after a bulk sync.
              </p>
            </div>
            <button
              className="btn-secondary text-sm shrink-0"
              disabled={unmonitorAll.isPending}
              onClick={() => {
                setSyncResult(null);
                unmonitorAll.mutate();
              }}
            >
              {unmonitorAll.isPending ? "Working…" : "Unmonitor All"}
            </button>
          </div>
        </div>
      </section>

      {/* Health */}
      <section>
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-2">
          Health
        </h2>
        {!health || health.checked_at === null ? (
          <p className="text-text-muted text-sm">
            Awaiting first health check (runs every 15 minutes — or click Run Now on
            the <span className="text-text-bright">health_check</span> task below).
          </p>
        ) : health.failures.length === 0 ? (
          <div className="card p-4 flex items-center gap-2">
            <CheckCircle2 size={16} className="text-status-downloaded shrink-0" />
            <div className="text-sm">
              <p className="text-text-bright">All systems operational</p>
              <p className="text-xs text-text-muted">
                {health.indexers_checked} indexer(s) and {health.clients_checked} download client(s)
                reachable. Last check: {new Date(health.checked_at).toLocaleString()}
              </p>
            </div>
          </div>
        ) : (
          <div className="card divide-y divide-border">
            {health.failures.map((f, i) => (
              <div key={i} className="px-4 py-3 flex items-start gap-2">
                <AlertTriangle size={14} className="text-status-missing shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-text-bright">
                    {f.kind === "indexer" ? "Indexer" : "Download client"}{" "}
                    <span className="text-accent">{f.name}</span> unreachable
                  </p>
                  <p className="text-xs text-text-muted font-mono mt-0.5 break-all">{f.message}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Scheduled Tasks */}
      <section>
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-2">
          Scheduled Tasks
        </h2>
        {tasksLoading ? (
          <p className="text-text-muted text-sm">Loading…</p>
        ) : tasks.length === 0 ? (
          <p className="text-text-muted text-sm">No scheduled tasks found.</p>
        ) : (
          <div className="card divide-y divide-border">
            {tasks.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                onRunNow={() => runNow.mutate(task.id)}
                isRunning={runNow.isPending && runNow.variables === task.id}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-text-muted">{label}</span>
      <span className="text-text-bright font-mono">{value}</span>
    </div>
  );
}

function TaskRow({
  task,
  onRunNow,
  isRunning,
}: {
  task: ScheduledTask;
  onRunNow: () => void;
  isRunning: boolean;
}) {
  const nextRun = task.next_run_time
    ? new Date(task.next_run_time).toLocaleString()
    : "—";

  return (
    <div className="flex items-center justify-between px-4 py-3 gap-4">
      <div className="min-w-0">
        <p className="text-sm text-text-bright truncate">{task.name}</p>
        <p className="text-xs text-text-muted mt-0.5">Next run: {nextRun}</p>
      </div>
      <button
        className="btn-secondary flex items-center gap-1.5 text-sm shrink-0"
        onClick={onRunNow}
        disabled={isRunning}
        title="Run now"
      >
        <Play size={12} />
        {isRunning ? "Running…" : "Run Now"}
      </button>
    </div>
  );
}
