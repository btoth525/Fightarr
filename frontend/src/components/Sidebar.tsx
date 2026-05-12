import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Swords,
  Calendar,
  Activity,
  Search,
  Settings,
  Server,
  AlertTriangle,
} from "lucide-react";
import clsx from "clsx";

import { api } from "../api/client";
import type { Event, QueueItem } from "../api/types";

interface SystemHealth {
  failures: { kind: string; name: string; message: string }[];
}

const logoUrl = "/logo.svg";

export default function Sidebar() {
  // Live counts for badges (Radarr-style at-a-glance state)
  const { data: queue = [] } = useQuery({
    queryKey: ["queue"],
    queryFn: () => api.get<QueueItem[]>("/queue"),
    refetchInterval: 10_000,
  });
  const { data: wanted = [] } = useQuery({
    queryKey: ["wanted"],
    queryFn: () => api.get<Event[]>("/wanted/missing"),
    refetchInterval: 30_000,
  });
  const { data: health } = useQuery({
    queryKey: ["system-health"],
    queryFn: () => api.get<SystemHealth>("/system/health"),
    refetchInterval: 60_000,
  });

  const queueCount = queue.length;
  const wantedCount = wanted.length;
  const healthFailures = health?.failures.length ?? 0;

  const navItems = [
    { to: "/events", label: "Events", icon: Swords },
    { to: "/calendar", label: "Calendar", icon: Calendar },
    { to: "/activity", label: "Activity", icon: Activity, count: queueCount },
    { to: "/wanted", label: "Wanted", icon: Search, count: wantedCount },
    { to: "/settings", label: "Settings", icon: Settings },
    { to: "/system", label: "System", icon: Server, alert: healthFailures > 0 },
  ];

  return (
    <aside className="w-52 shrink-0 bg-bg-panel border-r border-border flex flex-col">
      <div className="px-4 py-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <img src={logoUrl} alt="Fightarr" className="w-8 h-8 rounded-lg" />
          <div className="font-semibold text-text-bright tracking-tight text-base">
            Fightarr
          </div>
        </div>
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {navItems.map(({ to, label, icon: Icon, count, alert }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors",
                isActive
                  ? "bg-bg-elevated text-text-bright border-l-2 border-accent -ml-0.5"
                  : "text-text hover:bg-bg-elevated hover:text-text-bright",
              )
            }
          >
            <Icon size={16} />
            <span className="flex-1">{label}</span>
            {count !== undefined && count > 0 && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-accent/20 text-accent min-w-[18px] text-center">
                {count}
              </span>
            )}
            {alert && (
              <AlertTriangle size={13} className="text-status-missing" aria-label="Health issue" />
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-border text-xs text-text-dim">
        v0.2.0 · alpha
      </div>
    </aside>
  );
}
