import React, { useState } from "react";
import { Search, Plus, RefreshCw, ExternalLink, Users, Eye, Video as VideoIcon } from "lucide-react";
import { formatCompactNumber, formatFullNumber } from "../utils/format";

export default function Channels({
  channels = [],
  onSelectChannel,
  onOpenSearchModal,
  onSyncChannel,
  syncingChannelId,
}) {
  const [filterQuery, setFilterQuery] = useState("");

  const filtered = channels.filter(
    (ch) =>
      ch.title.toLowerCase().includes(filterQuery.toLowerCase()) ||
      (ch.custom_url && ch.custom_url.toLowerCase().includes(filterQuery.toLowerCase()))
  );

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "2rem", marginBottom: "6px" }}>Tracked Channels</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
            Manage and inspect tracked YouTube channels, view growth curves, and trigger sync cycles.
          </p>
        </div>
        <button className="btn btn-primary" onClick={onOpenSearchModal}>
          <Plus size={16} />
          <span>Add Channel</span>
        </button>
      </div>

      {/* Filter & Search Toolbar */}
      <div style={{ marginBottom: "24px" }}>
        <div className="search-input-wrapper">
          <Search className="search-input-icon" size={18} />
          <input
            type="text"
            className="form-input"
            placeholder="Search tracked channels by title or handle..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Channels Grid */}
      <div className="channels-grid">
        {filtered.map((ch) => {
          const isSyncingThis = syncingChannelId === ch.channel_id;

          return (
            <div key={ch.id} className="channel-card" onClick={() => onSelectChannel(ch)}>
              <div className="channel-card-top">
                <img
                  src={ch.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120"}
                  alt={ch.title}
                  className="channel-avatar"
                />
                <div className="channel-info">
                  <div className="channel-title">{ch.title}</div>
                  <span className="channel-handle">{ch.custom_url || ch.channel_id}</span>
                </div>
              </div>

              {/* Metrics Row */}
              <div className="channel-metrics-row">
                <div className="metric-item">
                  <span className="metric-item-label">Subs</span>
                  <span className="metric-item-val">{formatCompactNumber(ch.subscriber_count)}</span>
                </div>
                <div className="metric-item">
                  <span className="metric-item-label">Views</span>
                  <span className="metric-item-val">{formatCompactNumber(ch.view_count)}</span>
                </div>
                <div className="metric-item">
                  <span className="metric-item-label">Videos</span>
                  <span className="metric-item-val">{formatCompactNumber(ch.video_count)}</span>
                </div>
              </div>

              {/* Actions Footer */}
              <div className="channel-card-actions" onClick={(e) => e.stopPropagation()}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  {formatFullNumber(ch.subscriber_count)} total audience
                </span>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    title="Sync channel data now"
                    onClick={() => onSyncChannel(ch.channel_id)}
                    disabled={isSyncingThis}
                  >
                    <RefreshCw size={14} className={isSyncingThis ? "spin" : ""} />
                    <span>{isSyncingThis ? "Syncing..." : "Sync"}</span>
                  </button>
                  <button className="btn btn-primary btn-sm" onClick={() => onSelectChannel(ch)}>
                    Analytics
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
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
            <p style={{ fontSize: "1.1rem", marginBottom: "8px" }}>No matching channels found</p>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "16px" }}>
              {filterQuery ? "Try a different search query" : "Start by adding your first YouTube creator to track."}
            </p>
            <button className="btn btn-primary" onClick={onOpenSearchModal}>
              <Plus size={16} />
              <span>Add First Channel</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
