import React, { useState, useEffect } from "react";
import {
  X,
  RefreshCw,
  Trash2,
  ExternalLink,
  Users,
  Eye,
  Video as VideoIcon,
  Calendar,
  Globe,
  TrendingUp,
} from "lucide-react";
import { api } from "../services/api";
import { formatCompactNumber, formatFullNumber, formatDate, formatTimeAgo, parseISO8601Duration } from "../utils/format";
import GrowthChart from "./GrowthChart";

export default function ChannelDrawer({ channel, isOpen, onClose, onChannelUpdated, onChannelDeleted }) {
  const [snapshots, setSnapshots] = useState([]);
  const [recentVideos, setRecentVideos] = useState([]);
  const [activeChartMetric, setActiveChartMetric] = useState("views");
  const [isSyncing, setIsSyncing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  useEffect(() => {
    if (channel && isOpen) {
      loadDetails(channel.channel_id);
    }
  }, [channel, isOpen]);

  const loadDetails = async (identifier) => {
    setIsLoadingDetails(true);
    try {
      const [snapData, vidData] = await Promise.all([
        api.getChannelSnapshots(identifier, 30).catch(() => []),
        api.getVideos({ channel: identifier, limit: 8 }).catch(() => []),
      ]);
      setSnapshots(snapData || []);
      setRecentVideos(vidData || []);
    } catch (e) {
      console.error("Error loading channel details:", e);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  if (!isOpen || !channel) return null;

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const updated = await api.syncChannel(channel.channel_id);
      onChannelUpdated(updated);
      await loadDetails(channel.channel_id);
    } catch (err) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to stop tracking "${channel.title}"?`)) return;

    setIsDeleting(true);
    try {
      await api.deleteChannel(channel.channel_id);
      onChannelDeleted(channel.channel_id);
      onClose();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const avgViews = channel.video_count > 0 ? Math.floor(channel.view_count / channel.video_count) : 0;
  const ytUrl = channel.custom_url
    ? `https://www.youtube.com/${channel.custom_url}`
    : `https://www.youtube.com/channel/${channel.channel_id}`;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="drawer-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "14px", overflow: "hidden" }}>
            <img
              src={channel.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120"}
              alt={channel.title}
              style={{ width: "52px", height: "52px", borderRadius: "50%", objectFit: "cover" }}
            />
            <div style={{ overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h3 style={{ fontSize: "1.2rem", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {channel.title}
                </h3>
                <a
                  href={ytUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--accent-secondary)", display: "flex", alignItems: "center" }}
                  title="Open in YouTube"
                >
                  <ExternalLink size={16} />
                </a>
              </div>
              <span style={{ fontSize: "0.85rem", color: "var(--accent-secondary)", fontWeight: 500 }}>
                {channel.custom_url || channel.channel_id}
              </span>
            </div>
          </div>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* Drawer Body */}
        <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Core Metrics Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 1fr)",
              gap: "12px",
            }}
          >
            <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "var(--border-radius-md)", border: "1px solid var(--bg-card-border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase" }}>
                <Users size={14} color="var(--accent-secondary)" />
                <span>Subscribers</span>
              </div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, marginTop: "4px" }}>
                {formatCompactNumber(channel.subscriber_count)}
              </div>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {formatFullNumber(channel.subscriber_count)} exact
              </span>
            </div>

            <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "var(--border-radius-md)", border: "1px solid var(--bg-card-border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase" }}>
                <Eye size={14} color="var(--accent-primary)" />
                <span>Total Views</span>
              </div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, marginTop: "4px" }}>
                {formatCompactNumber(channel.view_count)}
              </div>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {formatFullNumber(channel.view_count)} exact
              </span>
            </div>

            <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "var(--border-radius-md)", border: "1px solid var(--bg-card-border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase" }}>
                <VideoIcon size={14} color="var(--warning)" />
                <span>Videos Published</span>
              </div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, marginTop: "4px" }}>
                {formatFullNumber(channel.video_count)}
              </div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "var(--border-radius-md)", border: "1px solid var(--bg-card-border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase" }}>
                <TrendingUp size={14} color="var(--success)" />
                <span>Avg Views / Video</span>
              </div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, marginTop: "4px" }}>
                {formatCompactNumber(avgViews)}
              </div>
            </div>
          </div>

          {/* Growth Chart Section */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <h4 style={{ fontSize: "0.95rem" }}>Historical Performance</h4>
              <div style={{ display: "flex", gap: "6px" }}>
                <button
                  className={`btn btn-sm ${activeChartMetric === "views" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setActiveChartMetric("views")}
                >
                  Views
                </button>
                <button
                  className={`btn btn-sm ${activeChartMetric === "subscribers" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setActiveChartMetric("subscribers")}
                >
                  Subscribers
                </button>
              </div>
            </div>
            <GrowthChart
              snapshots={snapshots}
              metric={activeChartMetric}
              title={`${channel.title} - ${activeChartMetric === "views" ? "View Velocity" : "Subscriber Trajectory"}`}
            />
          </div>

          {/* Channel Info Pills */}
          <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            {channel.country && (
              <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                <Globe size={14} /> Region: {channel.country}
              </span>
            )}
            {channel.published_at && (
              <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                <Calendar size={14} /> Joined {formatDate(channel.published_at)}
              </span>
            )}
          </div>

          {/* Recent Videos Section */}
          <div>
            <h4 style={{ fontSize: "0.95rem", marginBottom: "12px" }}>Recent Videos</h4>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {recentVideos.map((video) => (
                <div
                  key={video.video_id}
                  style={{
                    display: "flex",
                    gap: "12px",
                    padding: "10px",
                    background: "rgba(255,255,255,0.02)",
                    borderRadius: "var(--border-radius-md)",
                    border: "1px solid var(--bg-card-border)",
                    alignItems: "center",
                  }}
                >
                  <div style={{ position: "relative", width: "90px", aspectRatio: "16/9", flexShrink: 0, borderRadius: "6px", overflow: "hidden" }}>
                    <img
                      src={video.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=160"}
                      alt={video.title}
                      style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    />
                    {video.duration && (
                      <span className="video-duration-badge" style={{ fontSize: "0.65rem", padding: "1px 4px" }}>
                        {parseISO8601Duration(video.duration)}
                      </span>
                    )}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "0.85rem", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {video.title}
                    </div>
                    <div style={{ display: "flex", gap: "10px", fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "3px" }}>
                      <span>{formatCompactNumber(video.view_count)} views</span>
                      <span>•</span>
                      <span>{formatTimeAgo(video.published_at)}</span>
                    </div>
                  </div>
                </div>
              ))}

              {recentVideos.length === 0 && !isLoadingDetails && (
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>No indexed videos found.</span>
              )}
            </div>
          </div>
        </div>

        {/* Drawer Actions Footer */}
        <div style={{ padding: "16px 24px", borderTop: "1px solid var(--bg-card-border)", display: "flex", justifyContent: "space-between" }}>
          <button className="btn btn-danger-outline btn-sm" onClick={handleDelete} disabled={isDeleting}>
            <Trash2 size={16} />
            <span>Untrack Creator</span>
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleSync} disabled={isSyncing}>
            <RefreshCw size={16} className={isSyncing ? "spin" : ""} />
            <span>{isSyncing ? "Syncing..." : "Sync Fresh Data"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
