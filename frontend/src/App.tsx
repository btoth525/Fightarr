import { Routes, Route, Navigate } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import EventsPage from "./pages/EventsPage";
import EventDetailPage from "./pages/EventDetailPage";
import CalendarPage from "./pages/CalendarPage";
import ActivityPage from "./pages/ActivityPage";
import WantedPage from "./pages/WantedPage";
import SettingsPage from "./pages/SettingsPage";
import SystemPage from "./pages/SystemPage";

export default function App() {
  return (
    <div className="flex h-full bg-bg text-text">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
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
        </main>
      </div>
    </div>
  );
}
