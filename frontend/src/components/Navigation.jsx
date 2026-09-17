import React from "react";
import {
  LayoutDashboard,
  Tv,
  Trophy,
  Scale,
  Video,
  RefreshCw,
  Activity,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

export default function Navigation({
  currentView,
  setCurrentView,
  channelsCount = 0,
  videosCount = 0,
  systemHealth,
  onSyncAll,
  isSyncingAll,
}) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "channels", label: "Channels", icon: Tv, count: channelsCount },
    { id: "leaderboard", label: "Leaderboard", icon: Trophy },
    { id: "compare", label: "Compare Studio", icon: Scale },
    { id: "videos", label: "Video Explorer", icon: Video, count: videosCount },
  ];

  const isHealthy = systemHealth?.status === "healthy";
  const schedulerRunning = systemHealth?.scheduler?.is_running;

  return (
    <aside className="app-sidebar">
      {/* Brand Header */}
      <div className="brand-header">
        <div className="brand-icon">
          <Activity size={22} />
        </div>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span className="brand-title">Sociator</span>
            <span className="brand-badge">Pro</span>
          </div>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="nav-menu">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              className={`nav-link ${isActive ? "active" : ""}`}
              onClick={() => setCurrentView(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.count !== undefined && item.count > 0 && (
                <span className="nav-count">{item.count}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Global Sync All Button */}
      <div style={{ padding: "0 16px 16px" }}>
        <button
          className="btn btn-primary"
          style={{ width: "100%" }}
          onClick={onSyncAll}
          disabled={isSyncingAll}
        >
          <RefreshCw size={16} className={isSyncingAll ? "spin" : ""} />
          <span>{isSyncingAll ? "Syncing Network..." : "Sync All Creators"}</span>
        </button>
      </div>

      {/* Sidebar Footer / System Status */}
      <div className="sidebar-footer">
        <div className="system-status-card">
          <div className="status-pill-group">
            <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>System Status</span>
            <div className="status-indicator">
              <span className={`pulse-dot ${isHealthy ? "" : "warning"}`} />
              <span>{isHealthy ? "Online" : "Degraded"}</span>
            </div>
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
            <span>Auto-Sync:</span>
            <span style={{ color: schedulerRunning ? "var(--success)" : "var(--text-secondary)" }}>
              {schedulerRunning ? "Active (Every 6h)" : "Scheduled"}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
