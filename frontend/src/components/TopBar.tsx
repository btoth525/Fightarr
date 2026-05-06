import { useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { api } from "../api/client";

export default function TopBar() {
  const queryClient = useQueryClient();

  const refresh = useMutation({
    mutationFn: () => api.post("/command/refresh-schedule"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["calendar"] });
    },
  });

  return (
    <header className="h-12 shrink-0 border-b border-border bg-bg-panel flex items-center px-4 gap-2">
      <div className="flex-1" />
      <button
        className="btn"
        onClick={() => refresh.mutate()}
        disabled={refresh.isPending}
        title="Refresh schedule from Wikipedia"
      >
        <RefreshCw
          size={14}
          className={refresh.isPending ? "animate-spin" : ""}
        />
        <span>Refresh</span>
      </button>
    </header>
  );
}
