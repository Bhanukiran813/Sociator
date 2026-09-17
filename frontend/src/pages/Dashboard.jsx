import React, { useState } from "react";
import {
  Users,
  Eye,
  Video as VideoIcon,
  Tv,
  Plus,
  Search,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Loader2,
  RefreshCw,
} from "lucide-react";
import StatCard from "../components/StatCard";
import { formatCompactNumber, formatFullNumber, formatTimeAgo, parseISO8601Duration } from "../utils/format";

export default function Dashboard({
  channels = [],
  videos = [],
  onTrackChannel,
  isTracking,
  onOpenSearchModal,
  onSelectChannel,
  onSelectVideo,
  onViewAllChannels,
  onViewAllVideos,
  onSyncChannel,
}) {
  const [quickInput, setQuickInput] = useState("");

  const handleQuickTrack = (e) => {
    e.preventDefault();
    if (!quickInput.trim()) return;
    onTrackChannel(quickInput.trim());
    setQuickInput("");
  };

  // Aggregate stats
  const totalSubscribers = channels.reduce((sum, ch) => sum + (ch.subscriber_count || 0), 0);
  const totalViews = channels.reduce((sum, ch) => sum + (ch.view_count || 0), 0);
  const totalVideos = channels.reduce((sum, ch) => sum + (ch.video_count || 0), 0);

  // Top 4 channels by subscriber count
  const topChannels = [...channels].sort((a, b) => b.subscriber_count - a.subscriber_count).slice(0, 4);

  // Top 6 recent videos
  const recentVideos = [...videos].slice(0, 6);

  return (
    <div>
      {/* Page Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "2rem", marginBottom: "6px" }}>Creator Intelligence Dashboard</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
            Real-time tracking, metrics snapshots, and growth intelligence across YouTube channels.
          </p>
        </div>
        <button className="btn btn-primary" onClick={onOpenSearchModal}>
          <Search size={16} />
          <span>Discover Creators</span>
        </button>
      </div>

      {/* KPI Stats Grid */}
      <div className="stats-grid">
        <StatCard
          label="Tracked Channels"
          value={channels.length}
          icon={Tv}
          color="indigo"
          subtext="Active creator streams"
        />
        <StatCard
          label="Combined Audience"
          value={formatCompactNumber(totalSubscribers)}
          icon={Users}
          color="cyan"
          subtext={`${formatFullNumber(totalSubscribers)} total subscribers`}
        />
        <StatCard
          label="Network Views"
          value={formatCompactNumber(totalViews)}
          icon={Eye}
          color="green"
          subtext={`${formatFullNumber(totalViews)} video views`}
        />
        <StatCard
          label="Indexed Content"
          value={formatCompactNumber(totalVideos)}
          icon={VideoIcon}
          color="amber"
          subtext={`${videos.length} cached locally`}
        />
      </div>

      {/* Quick Track Input Bar */}
      <div className="quick-track-container">
        <div className="quick-track-header">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Sparkles size={18} color="var(--accent-primary)" />
            <h3 style={{ fontSize: "1.1rem" }}>Instant Channel Tracker</h3>
          </div>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Accepts handles (@MrBeast), channel IDs (UC...), or YouTube URLs
          </span>
        </div>
        <form onSubmit={handleQuickTrack} className="quick-track-form">
          <div className="search-input-wrapper quick-track-input">
            <Plus className="search-input-icon" size={18} />
            <input
              type="text"
              className="form-input"
              placeholder="Enter YouTube handle (e.g. @veritasium) or channel URL..."
              value={quickInput}
              onChange={(e) => setQuickInput(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={isTracking || !quickInput.trim()}>
            {isTracking ? (
              <>
                <Loader2 size={16} className="spin" />
                <span>Tracking...</span>
              </>
            ) : (
              <>
                <Plus size={16} />
                <span>Track Channel</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Two Column Layout: Top Creators & Recent Videos */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "28px" }}>
        {/* Top Tracked Channels */}
        <div className="glass-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <TrendingUp size={18} color="var(--accent-secondary)" />
              <h3 style={{ fontSize: "1.15rem" }}>Top Tracked Creators</h3>
            </div>
            {channels.length > 4 && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={onViewAllChannels}
                style={{ display: "flex", alignItems: "center", gap: "4px" }}
              >
                <span>View All ({channels.length})</span>
                <ArrowRight size={14} />
              </button>
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {topChannels.map((ch) => (
              <div
                key={ch.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 14px",
                  background: "rgba(255,255,255,0.025)",
                  border: "1px solid var(--bg-card-border)",
                  borderRadius: "var(--border-radius-md)",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
                onClick={() => onSelectChannel(ch)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <img
                    src={ch.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=80"}
                    alt={ch.title}
                    style={{ width: "42px", height: "42px", borderRadius: "50%", objectFit: "cover" }}
                  />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "0.95rem" }}>{ch.title}</div>
                    <span style={{ fontSize: "0.8rem", color: "var(--accent-secondary)" }}>
                      {ch.custom_url || ch.channel_id}
                    </span>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontWeight: 800, fontSize: "1rem" }}>
                    {formatCompactNumber(ch.subscriber_count)}
                  </div>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {formatCompactNumber(ch.view_count)} views
                  </span>
                </div>
              </div>
            ))}

            {channels.length === 0 && (
              <div style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                <Tv size={32} style={{ opacity: 0.3, marginBottom: "8px" }} />
                <p>No creators tracked yet. Track your first creator above!</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Videos Grid */}
        <div className="glass-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <VideoIcon size={18} color="var(--accent-primary)" />
              <h3 style={{ fontSize: "1.15rem" }}>Latest Published Videos</h3>
            </div>
            {videos.length > 6 && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={onViewAllVideos}
                style={{ display: "flex", alignItems: "center", gap: "4px" }}
              >
                <span>View All ({videos.length})</span>
                <ArrowRight size={14} />
              </button>
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {recentVideos.map((v) => (
              <div
                key={v.video_id}
                style={{
                  display: "flex",
                  gap: "12px",
                  alignItems: "center",
                  padding: "8px 10px",
                  background: "rgba(255,255,255,0.025)",
                  borderRadius: "var(--border-radius-md)",
                  border: "1px solid var(--bg-card-border)",
                  cursor: "pointer",
                }}
                onClick={() => onSelectVideo(v)}
              >
                <div style={{ position: "relative", width: "88px", aspectRatio: "16/9", borderRadius: "6px", overflow: "hidden", flexShrink: 0 }}>
                  <img
                    src={v.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=160"}
                    alt={v.title}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                  {v.duration && (
                    <span className="video-duration-badge" style={{ fontSize: "0.65rem", padding: "1px 4px" }}>
                      {parseISO8601Duration(v.duration)}
                    </span>
                  )}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "0.85rem", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {v.title}
                  </div>
                  <div style={{ display: "flex", gap: "10px", fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "3px" }}>
                    <span>{formatCompactNumber(v.view_count)} views</span>
                    <span>•</span>
                    <span>{formatTimeAgo(v.published_at)}</span>
                  </div>
                </div>
              </div>
            ))}

            {videos.length === 0 && (
              <div style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                <VideoIcon size={32} style={{ opacity: 0.3, marginBottom: "8px" }} />
                <p>No video records indexed yet.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
