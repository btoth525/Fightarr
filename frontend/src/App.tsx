import { Component, type ReactNode } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";

import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import EventsPage from "./pages/EventsPage";
import EventDetailPage from "./pages/EventDetailPage";
import CalendarPage from "./pages/CalendarPage";
import ActivityPage from "./pages/ActivityPage";
import WantedPage from "./pages/WantedPage";
import SettingsPage from "./pages/SettingsPage";
import SystemPage from "./pages/SystemPage";

// ─── Error boundary ───────────────────────────────────────────────────────────
// Catches synchronous render errors so a crash in one page doesn't blank the
// entire app. Matches Radarr's graceful degradation behaviour.

interface EBState {
  error: Error | null;
}

class ErrorBoundary extends Component<{ children: ReactNode }, EBState> {
  state: EBState = { error: null };

  static getDerivedStateFromError(error: Error): EBState {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center h-full gap-4 text-text-muted p-8">
          <div className="text-xl text-text-bright font-semibold">Something went wrong</div>
          <pre className="text-xs bg-bg-panel border border-border rounded p-4 max-w-2xl overflow-auto">
            {this.state.error.message}
          </pre>
          <button
            className="px-4 py-2 bg-accent text-white rounded text-sm"
            onClick={() => this.setState({ error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── App shell ────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <div className="flex h-full bg-bg text-text">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Navigate to="/events" replace />} />
              <Route path="/events" element={<EventsPage />} />
              <Route path="/events/:id" element={<EventDetailPage />} />
              <Route path="/calendar" element={<CalendarPage />} />
              <Route path="/activity" element={<ActivityPage />} />
              <Route path="/wanted" element={<WantedPage />} />
              <Route path="/settings/*" element={<SettingsPage />} />
              <Route path="/system" element={<SystemPage />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
      <Toaster
        position="bottom-right"
        theme="dark"
        toastOptions={{
          style: {
            background: "#1a1d24",
            border: "1px solid #2a2f3a",
            color: "#e8e8ea",
          },
        }}
      />
    </div>
  );
}
