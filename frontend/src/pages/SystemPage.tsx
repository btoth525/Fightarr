import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

interface SystemStatus {
  appName: string;
  version: string;
  branch: string;
}

export default function SystemPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["system-status"],
    queryFn: () => api.get<SystemStatus>("/system/status"),
  });

  return (
    <div className="space-y-4 max-w-2xl">
      <div>
        <h1 className="text-xl font-semibold text-text-bright">System</h1>
        <p className="text-sm text-text-muted">Application status</p>
      </div>

      {isLoading && <p className="text-text-muted">Loading…</p>}

      {data && (
        <div className="card p-4 space-y-2">
          <Row label="Application" value={data.appName} />
          <Row label="Version" value={data.version} />
          <Row label="Branch" value={data.branch} />
        </div>
      )}
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
