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
import logoUrl from "/logo.svg";

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
        <div className="flex items-center gap-2.5">
          <img src={logoUrl} alt="Fightarr" className="w-8 h-8 rounded-lg" />
          <div className="font-semibold text-text-bright tracking-tight text-base">
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
