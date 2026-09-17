import React, { useState, useEffect } from "react";
import { X, MessageSquare, ThumbsUp, Loader2, RefreshCw, Database, CheckCircle2 } from "lucide-react";
import { api } from "../services/api";
import { formatCompactNumber, formatTimeAgo } from "../utils/format";

export default function CommentDrawer({ video, isOpen, onClose }) {
  const [comments, setComments] = useState([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (video && isOpen) {
      setSyncStatus(null);
      loadComments(video.id || video.video_id);
    }
  }, [video, isOpen]);

  const loadComments = async (videoId) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getVideoComments(videoId, 50);
      if (data && Array.isArray(data.items)) {
        setComments(data.items);
        setTotal(data.total);
      } else if (Array.isArray(data)) {
        setComments(data);
        setTotal(data.length);
      } else {
        setComments([]);
        setTotal(0);
      }
    } catch (err) {
      setError(err.message || "Could not load comments.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSyncComments = async () => {
    if (!video || isSyncing) return;
    setIsSyncing(true);
    setError(null);
    setSyncStatus(null);
    try {
      const res = await api.syncVideoComments(video.id || video.video_id, 100);
      setSyncStatus(
        `Synced ${res.comments_fetched} comments (${res.comments_created} new, ${res.comments_updated} updated)`
      );
      await loadComments(video.id || video.video_id);
    } catch (err) {
      setError(err.message || "Failed to synchronize comments from YouTube.");
    } finally {
      setIsSyncing(false);
    }
  };

  if (!isOpen || !video) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="drawer-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", overflow: "hidden" }}>
            <div className="brand-icon" style={{ width: "32px", height: "32px" }}>
              <MessageSquare size={16} />
            </div>
            <div style={{ overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h3 style={{ fontSize: "1.1rem", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  Comment Intelligence
                </h3>
                <span
                  style={{
                    fontSize: "0.72rem",
                    padding: "2px 8px",
                    borderRadius: "12px",
                    background: "rgba(99, 102, 241, 0.15)",
                    color: "var(--accent-primary, #6366f1)",
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <Database size={11} />
                  {total} stored
                </span>
              </div>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {video.title}
              </p>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              className="btn btn-secondary btn-sm"
              style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.78rem", padding: "6px 10px" }}
              onClick={handleSyncComments}
              disabled={isSyncing || isLoading}
              title="Synchronize fresh comments from YouTube Data API into Sociator PostgreSQL"
            >
              <RefreshCw size={13} className={isSyncing ? "spin" : ""} />
              <span>{isSyncing ? "Syncing..." : "Sync YouTube"}</span>
            </button>
            <button className="btn-icon" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {syncStatus && (
            <div
              style={{
                background: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "#6ee7b7",
                padding: "10px 14px",
                borderRadius: "var(--border-radius-md, 8px)",
                fontSize: "0.82rem",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <CheckCircle2 size={16} color="var(--success, #10b981)" />
              <span>{syncStatus}</span>
            </div>
          )}

          {isLoading && (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
              <Loader2 size={32} className="spin" style={{ margin: "0 auto 12px" }} />
              <p>Loading comments from Sociator database...</p>
            </div>
          )}

          {error && (
            <div
              style={{
                background: "rgba(239,68,68,0.1)",
                border: "1px solid var(--danger)",
                color: "#fca5a5",
                padding: "12px",
                borderRadius: "var(--border-radius-md)",
                fontSize: "0.85rem",
              }}
            >
              {error}
            </div>
          )}

          {!isLoading && !error && comments.length === 0 && (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
              <Database size={36} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
              <p style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>No comments stored yet</p>
              <p style={{ fontSize: "0.85rem", maxWidth: "300px", margin: "0 auto 16px" }}>
                Synchronize comments from YouTube to store them in PostgreSQL and prepare for intelligence analysis.
              </p>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSyncComments}
                disabled={isSyncing}
                style={{ margin: "0 auto", display: "inline-flex", alignItems: "center", gap: "6px" }}
              >
                <RefreshCw size={13} className={isSyncing ? "spin" : ""} />
                <span>{isSyncing ? "Syncing..." : "Sync Comments Now"}</span>
              </button>
            </div>
          )}

          {!isLoading &&
            comments.map((c) => (
              <div
                key={c.id || c.youtube_comment_id || c.comment_id}
                style={{
                  display: "flex",
                  gap: "12px",
                  padding: "12px",
                  background: "rgba(255,255,255,0.02)",
                  borderRadius: "var(--border-radius-md)",
                  border: "1px solid var(--bg-card-border)",
                }}
              >
                <img
                  src={c.author_profile_image || "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=60"}
                  alt={c.author_name || "Viewer"}
                  style={{ width: "36px", height: "36px", borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ fontSize: "0.85rem", fontWeight: 700 }}>{c.author_name || "YouTube Viewer"}</span>
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>{formatTimeAgo(c.published_at)}</span>
                  </div>
                  <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.4, wordBreak: "break-word" }}>
                    {c.text}
                  </p>
                  <div style={{ display: "flex", alignItems: "center", gap: "4px", marginTop: "6px", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    <ThumbsUp size={12} />
                    <span>{formatCompactNumber(c.like_count)}</span>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
