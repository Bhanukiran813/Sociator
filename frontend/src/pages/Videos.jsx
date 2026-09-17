import React, { useState } from "react";
import {
  Video as VideoIcon,
  Search,
  Eye,
  ThumbsUp,
  MessageSquare,
  Calendar,
  ExternalLink,
  Filter,
} from "lucide-react";
import { formatCompactNumber, formatDate, formatTimeAgo, parseISO8601Duration } from "../utils/format";

export default function Videos({
  videos = [],
  channels = [],
  selectedChannelFilter,
  setSelectedChannelFilter,
  sortBy,
  setSortBy,
  onSelectVideo,
}) {
  const [filterQuery, setFilterQuery] = useState("");

  const filteredVideos = videos.filter((v) => {
    const matchesChannel =
      !selectedChannelFilter ||
      v.channel_id === Number(selectedChannelFilter) ||
      (v.channel && v.channel.channel_id === selectedChannelFilter);
    const matchesSearch = v.title.toLowerCase().includes(filterQuery.toLowerCase());
    return matchesChannel && matchesSearch;
  });

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "28px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <VideoIcon size={28} color="var(--accent-primary)" />
            <h1 style={{ fontSize: "2rem" }}>Video Performance Explorer</h1>
          </div>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
            Analyze indexed video performance metrics, views, likes, and viewer comment threads.
          </p>
        </div>
      </div>

      {/* Filter & Sort Bar */}
      <div
        className="glass-card"
        style={{
          display: "flex",
          gap: "16px",
          alignItems: "center",
          flexWrap: "wrap",
          padding: "16px 20px",
          marginBottom: "28px",
        }}
      >
        <div className="search-input-wrapper" style={{ flex: 1, minWidth: "240px" }}>
          <Search className="search-input-icon" size={18} />
          <input
            type="text"
            className="form-input"
            placeholder="Filter videos by title..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
          />
        </div>

        {/* Channel Filter Select */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Filter size={16} color="var(--text-muted)" />
          <select
            className="form-input"
            style={{ padding: "10px 14px", width: "auto" }}
            value={selectedChannelFilter || ""}
            onChange={(e) => setSelectedChannelFilter(e.target.value || null)}
          >
            <option value="">All Channels ({channels.length})</option>
            {channels.map((ch) => (
              <option key={ch.id} value={ch.id}>
                {ch.title}
              </option>
            ))}
          </select>
        </div>

        {/* Sort Select */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Sort by:</span>
          <select
            className="form-input"
            style={{ padding: "10px 14px", width: "auto" }}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="published_at">Latest Published</option>
            <option value="views">Most Views</option>
            <option value="likes">Most Likes</option>
            <option value="comments">Most Comments</option>
          </select>
        </div>
      </div>

      {/* Videos Grid */}
      <div className="videos-grid">
        {filteredVideos.map((video) => {
          const ytUrl = `https://www.youtube.com/watch?v=${video.video_id}`;

          return (
            <div key={video.id} className="video-card">
              <div className="video-thumbnail-wrapper">
                <img
                  src={video.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400"}
                  alt={video.title}
                  className="video-thumbnail"
                />
                {video.duration && (
                  <span className="video-duration-badge">{parseISO8601Duration(video.duration)}</span>
                )}
              </div>

              <div className="video-body">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                  <h4 className="video-title" title={video.title}>
                    {video.title}
                  </h4>
                  <a
                    href={ytUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "var(--text-muted)", flexShrink: 0, marginTop: "2px" }}
                    title="Watch on YouTube"
                  >
                    <ExternalLink size={16} />
                  </a>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.78rem", color: "var(--text-muted)" }}>
                  <Calendar size={13} />
                  <span>{formatDate(video.published_at)} ({formatTimeAgo(video.published_at)})</span>
                </div>

                {/* Metrics Bar */}
                <div className="video-metrics-bar">
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }} title="Views">
                    <Eye size={14} color="var(--accent-primary)" />
                    <strong>{formatCompactNumber(video.view_count)}</strong>
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }} title="Likes">
                    <ThumbsUp size={14} color="var(--success)" />
                    <span>{formatCompactNumber(video.like_count)}</span>
                  </span>
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ padding: "4px 8px", fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "4px" }}
                    onClick={() => onSelectVideo(video)}
                    title="Inspect Comments"
                  >
                    <MessageSquare size={13} color="var(--accent-secondary)" />
                    <span>{formatCompactNumber(video.comment_count)}</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {filteredVideos.length === 0 && (
          <div
            style={{
              gridColumn: "1 / -1",
              textAlign: "center",
              padding: "60px 20px",
              background: "var(--bg-card)",
              borderRadius: "var(--border-radius-lg)",
              border: "1px solid var(--bg-card-border)",
            }}
          >
            <VideoIcon size={36} style={{ opacity: 0.3, marginBottom: "8px" }} />
            <p style={{ fontSize: "1rem", color: "var(--text-secondary)" }}>
              No videos matching the selected criteria.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
