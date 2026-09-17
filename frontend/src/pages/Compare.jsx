import React, { useState, useEffect } from "react";
import { Scale, Users, Eye, Video as VideoIcon, TrendingUp, Check, Loader2 } from "lucide-react";
import { api } from "../services/api";
import { formatCompactNumber, formatFullNumber } from "../utils/format";

export default function Compare({ channels = [] }) {
  const [selectedChannels, setSelectedChannels] = useState([]);
  const [comparisonResults, setComparisonResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Default select first 2-3 channels
  useEffect(() => {
    if (channels.length >= 2 && selectedChannels.length === 0) {
      setSelectedChannels(channels.slice(0, 3).map((c) => c.channel_id));
    }
  }, [channels]);

  useEffect(() => {
    if (selectedChannels.length > 0) {
      runComparison(selectedChannels);
    } else {
      setComparisonResults([]);
    }
  }, [selectedChannels]);

  const runComparison = async (identifiers) => {
    setIsLoading(true);
    try {
      const data = await api.compareChannels(identifiers);
      setComparisonResults(data || []);
    } catch (e) {
      console.error("Comparison load failed:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleChannel = (channelId) => {
    if (selectedChannels.includes(channelId)) {
      if (selectedChannels.length <= 1) {
        alert("Please keep at least one channel selected for comparison.");
        return;
      }
      setSelectedChannels(selectedChannels.filter((id) => id !== channelId));
    } else {
      if (selectedChannels.length >= 5) {
        alert("You can compare up to 5 channels at once.");
        return;
      }
      setSelectedChannels([...selectedChannels, channelId]);
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "28px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
          <Scale size={28} color="var(--accent-primary)" />
          <h1 style={{ fontSize: "2rem" }}>Creator Comparison Studio</h1>
        </div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
          Benchmark and compare performance, view velocity, and audience retention side-by-side.
        </p>
      </div>

      {/* Channel Picker Chips */}
      <div className="glass-card" style={{ marginBottom: "28px", padding: "18px 24px" }}>
        <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "12px", textTransform: "uppercase" }}>
          Select Channels to Compare ({selectedChannels.length} / 5 selected)
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
          {channels.map((ch) => {
            const isSelected = selectedChannels.includes(ch.channel_id);
            return (
              <button
                key={ch.channel_id}
                onClick={() => toggleChannel(ch.channel_id)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 14px",
                  borderRadius: "var(--border-radius-pill)",
                  background: isSelected ? "rgba(99, 102, 241, 0.2)" : "rgba(255, 255, 255, 0.04)",
                  border: isSelected ? "1px solid var(--accent-primary)" : "1px solid var(--bg-card-border)",
                  color: isSelected ? "#ffffff" : "var(--text-secondary)",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  transition: "all 0.2s ease",
                }}
              >
                <img
                  src={ch.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=40"}
                  alt={ch.title}
                  style={{ width: "20px", height: "20px", borderRadius: "50%", objectFit: "cover" }}
                />
                <span>{ch.title}</span>
                {isSelected && <Check size={14} color="var(--accent-primary)" />}
              </button>
            );
          })}

          {channels.length === 0 && (
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              No tracked channels available. Track channels first to compare them.
            </span>
          )}
        </div>
      </div>

      {/* Comparison Table */}
      {isLoading ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <Loader2 size={32} className="spin" style={{ margin: "0 auto 12px" }} />
          <p>Analyzing comparative metrics...</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ minWidth: "220px" }}>Metric</th>
                {comparisonResults.map((item) => (
                  <th key={item.id} style={{ textAlign: "center", minWidth: "160px" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
                      <img
                        src={item.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=60"}
                        alt={item.title}
                        style={{ width: "48px", height: "48px", borderRadius: "50%", objectFit: "cover" }}
                      />
                      <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>{item.title}</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--accent-secondary)" }}>
                        {item.custom_url || item.channel_id}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Subscribers */}
              <tr>
                <td style={{ fontWeight: 600 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Users size={16} color="var(--accent-secondary)" />
                    <span>Subscribers</span>
                  </div>
                </td>
                {comparisonResults.map((item) => (
                  <td key={item.id} style={{ textAlign: "center", fontWeight: 800, fontSize: "1.1rem" }}>
                    {formatCompactNumber(item.subscriber_count)}
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 400 }}>
                      {formatFullNumber(item.subscriber_count)}
                    </div>
                  </td>
                ))}
              </tr>

              {/* Total Views */}
              <tr>
                <td style={{ fontWeight: 600 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Eye size={16} color="var(--accent-primary)" />
                    <span>Total Channel Views</span>
                  </div>
                </td>
                {comparisonResults.map((item) => (
                  <td key={item.id} style={{ textAlign: "center", fontWeight: 800, fontSize: "1.1rem" }}>
                    {formatCompactNumber(item.view_count)}
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 400 }}>
                      {formatFullNumber(item.view_count)}
                    </div>
                  </td>
                ))}
              </tr>

              {/* Video Count */}
              <tr>
                <td style={{ fontWeight: 600 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <VideoIcon size={16} color="var(--warning)" />
                    <span>Published Videos</span>
                  </div>
                </td>
                {comparisonResults.map((item) => (
                  <td key={item.id} style={{ textAlign: "center", fontWeight: 700 }}>
                    {formatFullNumber(item.video_count)}
                  </td>
                ))}
              </tr>

              {/* Avg Views / Video */}
              <tr>
                <td style={{ fontWeight: 600 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <TrendingUp size={16} color="var(--success)" />
                    <span>Avg Views / Video</span>
                  </div>
                </td>
                {comparisonResults.map((item) => (
                  <td key={item.id} style={{ textAlign: "center", fontWeight: 800, color: "var(--accent-secondary)" }}>
                    {formatCompactNumber(item.avg_views_per_video)}
                  </td>
                ))}
              </tr>

              {/* Views Growth Rate */}
              <tr>
                <td style={{ fontWeight: 600 }}>
                  <span>Views Growth Rate</span>
                </td>
                {comparisonResults.map((item) => {
                  const rate = item.views_growth?.growth_rate_pct || 0;
                  const isPos = rate >= 0;
                  return (
                    <td key={item.id} style={{ textAlign: "center", fontWeight: 700, color: isPos ? "var(--success)" : "var(--danger)" }}>
                      {isPos ? `+${rate}%` : `${rate}%`}
                    </td>
                  );
                })}
              </tr>

              {/* Subs Growth Rate */}
              <tr>
                <td style={{ fontWeight: 600 }}>
                  <span>Subscribers Growth Rate</span>
                </td>
                {comparisonResults.map((item) => {
                  const rate = item.subs_growth?.growth_rate_pct || 0;
                  const isPos = rate >= 0;
                  return (
                    <td key={item.id} style={{ textAlign: "center", fontWeight: 700, color: isPos ? "var(--success)" : "var(--danger)" }}>
                      {isPos ? `+${rate}%` : `${rate}%`}
                    </td>
                  );
                })}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
