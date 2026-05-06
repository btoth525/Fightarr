import { NavLink } from "react-router-dom";
import {
  Swords,
  Calendar,
  Activity,
  Search,
  Settings,
  Server,
} from "lucide-react";
import clsx from "clsx";

const navItems = [
  { to: "/events", label: "Events", icon: Swords },
  { to: "/calendar", label: "Calendar", icon: Calendar },
  { to: "/activity", label: "Activity", icon: Activity },
  { to: "/wanted", label: "Wanted", icon: Search },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/system", label: "System", icon: Server },
];

export default function Sidebar() {
  return (
    <aside className="w-52 shrink-0 bg-bg-panel border-r border-border flex flex-col">
      <div className="px-4 py-5 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-accent flex items-center justify-center">
            <Swords size={16} className="text-black" strokeWidth={2.5} />
          </div>
          <div className="font-semibold text-text-bright tracking-tight">
            Fightarr
          </div>
        </div>
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {navItems.map(({ to, label, icon: Icon }) => (
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
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-border text-xs text-text-dim">
        v0.0.1 · pre-alpha
      </div>
    </aside>
  );
}
