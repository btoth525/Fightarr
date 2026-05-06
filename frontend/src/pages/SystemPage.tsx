import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";

import { api } from "../api/client";
import type { ScheduledTask } from "../api/types";

interface SystemStatus {
  appName: string;
  version: string;
  branch: string;
}

export default function SystemPage() {
  const queryClient = useQueryClient();

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["system-status"],
    queryFn: () => api.get<SystemStatus>("/system/status"),
  });

  const { data: tasks = [], isLoading: tasksLoading } = useQuery({
    queryKey: ["system-tasks"],
    queryFn: () => api.get<ScheduledTask[]>("/system/tasks"),
    refetchInterval: 15_000,
  });

  const runNow = useMutation({
    mutationFn: (jobId: string) =>
      api.post(`/system/tasks/${jobId}/run-now`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["system-tasks"] }),
  });

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
