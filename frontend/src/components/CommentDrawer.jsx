import React, { useState, useEffect } from "react";
import { X, MessageSquare, ThumbsUp, Loader2 } from "lucide-react";
import { api } from "../services/api";
import { formatCompactNumber, formatTimeAgo } from "../utils/format";

export default function CommentDrawer({ video, isOpen, onClose }) {
  const [comments, setComments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (video && isOpen) {
      loadComments(video.video_id);
    }
  }, [video, isOpen]);

  const loadComments = async (videoId) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getVideoComments(videoId, 25);
      setComments(data || []);
    } catch (err) {
      setError(err.message || "Could not load comments.");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen || !video) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="drawer-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px", overflow: "hidden" }}>
            <div className="brand-icon" style={{ width: "32px", height: "32px" }}>
              <MessageSquare size={16} />
            </div>
            <div style={{ overflow: "hidden" }}>
              <h3 style={{ fontSize: "1.1rem", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                Top Comments
              </h3>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {video.title}
              </p>
            </div>
          </div>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {isLoading && (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
              <Loader2 size={32} className="spin" style={{ margin: "0 auto 12px" }} />
              <p>Fetching top YouTube comments...</p>
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
              <p>No comments found or comments are disabled for this video.</p>
            </div>
          )}

          {!isLoading &&
            comments.map((c) => (
              <div
                key={c.comment_id}
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
                  alt={c.author_name}
                  style={{ width: "36px", height: "36px", borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ fontSize: "0.85rem", fontWeight: 700 }}>{c.author_name}</span>
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
