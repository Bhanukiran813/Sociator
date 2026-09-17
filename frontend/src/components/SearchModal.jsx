import React, { useState } from "react";
import { Search, X, Plus, Check, Loader2, Tv } from "lucide-react";
import { api } from "../services/api";

export default function SearchModal({ isOpen, onClose, onChannelTracked, trackedChannelIds = [] }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [trackingId, setTrackingId] = useState(null);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setError(null);
    try {
      const data = await api.searchYouTubeChannels(searchQuery.trim(), 8);
      setResults(data);
    } catch (err) {
      setError(err.message || "Failed to search YouTube. Check if API key is configured.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleTrack = async (channelId) => {
    setTrackingId(channelId);
    setError(null);
    try {
      const tracked = await api.trackChannel(channelId);
      onChannelTracked(tracked);
    } catch (err) {
      setError(err.message || "Failed to track channel.");
    } finally {
      setTrackingId(null);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div className="brand-icon" style={{ width: "32px", height: "32px" }}>
              <Tv size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: "1.15rem" }}>Discover & Track Creators</h3>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                Search YouTube channels by keyword or channel name
              </p>
            </div>
          </div>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          <form onSubmit={handleSearch} style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
            <div className="search-input-wrapper">
              <Search className="search-input-icon" size={18} />
              <input
                type="text"
                className="form-input"
                placeholder="Search by creator name (e.g. MrBeast, Veritasium, MKBHD)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={isSearching || !searchQuery.trim()}>
              {isSearching ? <Loader2 size={16} className="spin" /> : "Search"}
            </button>
          </form>

          {error && (
            <div
              style={{
                background: "rgba(239, 68, 68, 0.12)",
                border: "1px solid var(--danger)",
                color: "#fca5a5",
                padding: "12px 16px",
                borderRadius: "var(--border-radius-md)",
                fontSize: "0.85rem",
                marginBottom: "16px",
              }}
            >
              {error}
            </div>
          )}

          {/* Results List */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxHeight: "420px", overflowY: "auto" }}>
            {results.map((item) => {
              const isAlreadyTracked = trackedChannelIds.includes(item.channel_id);
              const isTrackingThis = trackingId === item.channel_id;

              return (
                <div
                  key={item.channel_id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "14px",
                    padding: "12px 16px",
                    background: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid var(--bg-card-border)",
                    borderRadius: "var(--border-radius-md)",
                    transition: "all 0.2s ease",
                  }}
                >
                  <img
                    src={item.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100"}
                    alt={item.title}
                    style={{ width: "48px", height: "48px", borderRadius: "50%", objectFit: "cover" }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: "0.95rem", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {item.description || "No description provided."}
                    </div>
                  </div>
                  <div>
                    {isAlreadyTracked ? (
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "0.8rem",
                          color: "var(--success)",
                          fontWeight: 600,
                          padding: "6px 10px",
                        }}
                      >
                        <Check size={16} /> Tracked
                      </span>
                    ) : (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleTrack(item.channel_id)}
                        disabled={isTrackingThis}
                      >
                        {isTrackingThis ? (
                          <>
                            <Loader2 size={14} className="spin" />
                            <span>Adding...</span>
                          </>
                        ) : (
                          <>
                            <Plus size={14} />
                            <span>Track</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}

            {results.length === 0 && !isSearching && !error && (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
                <Search size={36} style={{ opacity: 0.3, marginBottom: "8px" }} />
                <p style={{ fontSize: "0.9rem" }}>Search for any creator above to discover and track them</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
