import React, { useState, useEffect } from "react";
import {
  Activity,
  Search,
  RefreshCw,
  Plus,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";

import { api } from "./services/api";
import Navigation from "./components/Navigation";
import SearchModal from "./components/SearchModal";
import ChannelDrawer from "./components/ChannelDrawer";
import CommentDrawer from "./components/CommentDrawer";

import Dashboard from "./pages/Dashboard";
import Channels from "./pages/Channels";
import Leaderboard from "./pages/Leaderboard";
import Compare from "./pages/Compare";
import Videos from "./pages/Videos";

export default function App() {
  const [currentView, setCurrentView] = useState("dashboard");
  const [channels, setChannels] = useState([]);
  const [videos, setVideos] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);

  // Loading & Action states
  const [isSyncingAll, setIsSyncingAll] = useState(false);
  const [syncingChannelId, setSyncingChannelId] = useState(null);
  const [isTracking, setIsTracking] = useState(false);

  // Drawers & Modals
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [selectedVideo, setSelectedVideo] = useState(null);

  // Video explorer state
  const [videoSortBy, setVideoSortBy] = useState("published_at");
  const [selectedChannelFilter, setSelectedChannelFilter] = useState(null);

  // Toast Notifications
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = "success") => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Initial load
  useEffect(() => {
    loadAllData();
  }, []);

  // Reload videos when sort or filter changes
  useEffect(() => {
    loadVideos();
  }, [videoSortBy, selectedChannelFilter]);

  const loadAllData = async () => {
    try {
      const [chData, vData, healthData] = await Promise.all([
        api.getChannels().catch(() => []),
        api.getVideos({ sortBy: videoSortBy, limit: 50 }).catch(() => []),
        api.getHealth().catch(() => null),
      ]);
      setChannels(chData || []);
      setVideos(vData || []);
      setSystemHealth(healthData);
    } catch (e) {
      console.error("Failed to load initial data:", e);
    }
  };

  const loadVideos = async () => {
    try {
      const vData = await api.getVideos({
        channel: selectedChannelFilter || "",
        sortBy: videoSortBy,
        limit: 50,
      });
      setVideos(vData || []);
    } catch (e) {
      console.error("Failed to reload videos:", e);
    }
  };

  // Channel Actions
  const handleTrackChannel = async (identifier) => {
    setIsTracking(true);
    try {
      const tracked = await api.trackChannel(identifier);
      addToast(`Successfully tracking "${tracked.title}"!`);
      await loadAllData();
    } catch (err) {
      addToast(err.message || "Failed to track channel.", "error");
    } finally {
      setIsTracking(false);
    }
  };

  const handleSyncChannel = async (channelId) => {
    setSyncingChannelId(channelId);
    try {
      const updated = await api.syncChannel(channelId);
      setChannels((prev) => prev.map((c) => (c.channel_id === updated.channel_id ? updated : c)));
      if (selectedChannel && selectedChannel.channel_id === updated.channel_id) {
        setSelectedChannel(updated);
      }
      addToast(`Synced metrics for "${updated.title}"!`);
      loadVideos();
    } catch (err) {
      addToast(err.message || "Failed to sync channel.", "error");
    } finally {
      setSyncingChannelId(null);
    }
  };

  const handleSyncAll = async () => {
    setIsSyncingAll(true);
    try {
      const res = await api.syncAllChannels();
      addToast(`Sync complete: ${res.synced_count} creators updated.`);
      await loadAllData();
    } catch (err) {
      addToast(err.message || "Sync all failed.", "error");
    } finally {
      setIsSyncingAll(false);
    }
  };

  const handleChannelDeleted = (channelId) => {
    setChannels((prev) => prev.filter((c) => c.channel_id !== channelId));
    addToast("Channel untracked.");
    loadVideos();
  };

  const handleChannelUpdated = (updated) => {
    setChannels((prev) => prev.map((c) => (c.channel_id === updated.channel_id ? updated : c)));
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Navigation
        currentView={currentView}
        setCurrentView={setCurrentView}
        channelsCount={channels.length}
        videosCount={videos.length}
        systemHealth={systemHealth}
        onSyncAll={handleSyncAll}
        isSyncingAll={isSyncingAll}
      />

      {/* Main Content Viewport */}
      <main className="app-main">
        {/* Topbar */}
        <header className="app-topbar">
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 700 }}>
              Sociator
            </span>
            <span style={{ color: "var(--text-muted)" }}>/</span>
            <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)", textTransform: "capitalize" }}>
              {currentView}
            </span>
          </div>

          <div className="topbar-actions">
            <button className="btn btn-secondary btn-sm" onClick={() => setIsSearchModalOpen(true)}>
              <Search size={14} />
              <span>Search YouTube</span>
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleSyncAll}
              disabled={isSyncingAll}
              title="Sync metrics across all tracked channels"
            >
              <RefreshCw size={14} className={isSyncingAll ? "spin" : ""} />
              <span>{isSyncingAll ? "Syncing..." : "Sync All"}</span>
            </button>
          </div>
        </header>

        {/* Dynamic View Content */}
        <div className="content-viewport">
          {currentView === "dashboard" && (
            <Dashboard
              channels={channels}
              videos={videos}
              onTrackChannel={handleTrackChannel}
              isTracking={isTracking}
              onOpenSearchModal={() => setIsSearchModalOpen(true)}
              onSelectChannel={(ch) => setSelectedChannel(ch)}
              onSelectVideo={(v) => setSelectedVideo(v)}
              onViewAllChannels={() => setCurrentView("channels")}
              onViewAllVideos={() => setCurrentView("videos")}
              onSyncChannel={handleSyncChannel}
            />
          )}

          {currentView === "channels" && (
            <Channels
              channels={channels}
              onSelectChannel={(ch) => setSelectedChannel(ch)}
              onOpenSearchModal={() => setIsSearchModalOpen(true)}
              onSyncChannel={handleSyncChannel}
              syncingChannelId={syncingChannelId}
            />
          )}

          {currentView === "leaderboard" && (
            <Leaderboard onSelectChannel={(ch) => setSelectedChannel(ch)} />
          )}

          {currentView === "compare" && <Compare channels={channels} />}

          {currentView === "videos" && (
            <Videos
              videos={videos}
              channels={channels}
              selectedChannelFilter={selectedChannelFilter}
              setSelectedChannelFilter={setSelectedChannelFilter}
              sortBy={videoSortBy}
              setSortBy={setVideoSortBy}
              onSelectVideo={(v) => setSelectedVideo(v)}
            />
          )}
        </div>
      </main>

      {/* Search & Discovery Modal */}
      <SearchModal
        isOpen={isSearchModalOpen}
        onClose={() => setIsSearchModalOpen(false)}
        onChannelTracked={(newChannel) => {
          setChannels((prev) => {
            const exists = prev.some((c) => c.channel_id === newChannel.channel_id);
            return exists ? prev : [newChannel, ...prev];
          });
          addToast(`Tracked "${newChannel.title}"!`);
          setIsSearchModalOpen(false);
          loadVideos();
        }}
        trackedChannelIds={channels.map((c) => c.channel_id)}
      />

      {/* Detailed Channel Drawer */}
      <ChannelDrawer
        channel={selectedChannel}
        isOpen={!!selectedChannel}
        onClose={() => setSelectedChannel(null)}
        onChannelUpdated={handleChannelUpdated}
        onChannelDeleted={handleChannelDeleted}
      />

      {/* Video Comments Drawer */}
      <CommentDrawer
        video={selectedVideo}
        isOpen={!!selectedVideo}
        onClose={() => setSelectedVideo(null)}
      />

      {/* Toast Notification Stack */}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            {t.type === "success" ? (
              <CheckCircle2 size={18} color="var(--success)" />
            ) : (
              <AlertCircle size={18} color="var(--danger)" />
            )}
            <span>{t.message}</span>
            <button
              onClick={() => removeToast(t.id)}
              style={{ color: "var(--text-muted)", marginLeft: "8px", cursor: "pointer" }}
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
