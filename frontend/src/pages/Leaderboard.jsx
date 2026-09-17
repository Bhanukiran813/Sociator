import React, { useState, useEffect } from "react";
import { Trophy, Users, Eye, Video as VideoIcon, TrendingUp, Loader2 } from "lucide-react";
import { api } from "../services/api";
import { formatCompactNumber, formatFullNumber } from "../utils/format";

export default function Leaderboard({ onSelectChannel }) {
  const [sortBy, setSortBy] = useState("subscribers");
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadLeaderboard(sortBy);
  }, [sortBy]);

  const loadLeaderboard = async (metric) => {
    setIsLoading(true);
    try {
      const data = await api.getLeaderboard(metric, 50);
      setLeaderboardData(data || []);
    } catch (e) {
      console.error("Leaderboard load failed:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const sortTabs = [
    { id: "subscribers", label: "Subscribers", icon: Users },
    { id: "views", label: "Total Views", icon: Eye },
    { id: "videos", label: "Video Volume", icon: VideoIcon },
    { id: "avg_views", label: "Avg Views/Video", icon: TrendingUp },
  ];

  const getRankBadgeClass = (rank) => {
    if (rank === 1) return "rank-badge rank-gold";
    if (rank === 2) return "rank-badge rank-silver";
    if (rank === 3) return "rank-badge rank-bronze";
    return "rank-badge rank-other";
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "28px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <Trophy size={28} color="#ffd700" />
            <h1 style={{ fontSize: "2rem" }}>Creator Leaderboard</h1>
          </div>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
            Real-time rankings across all tracked YouTube channels benchmarked by key performance metrics.
          </p>
        </div>
      </div>

      {/* Sorting Tabs Toolbar */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "24px", flexWrap: "wrap" }}>
        {sortTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = sortBy === tab.id;

          return (
            <button
              key={tab.id}
              className={`btn ${isActive ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setSortBy(tab.id)}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Leaderboard Table Container */}
      <div className="table-container">
        {isLoading ? (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
            <Loader2 size={32} className="spin" style={{ margin: "0 auto 12px" }} />
            <p>Calculating leaderboard rankings...</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: "70px", textAlign: "center" }}>Rank</th>
                <th>Creator</th>
                <th style={{ textAlign: "right" }}>Subscribers</th>
                <th style={{ textAlign: "right" }}>Total Views</th>
                <th style={{ textAlign: "right" }}>Videos</th>
                <th style={{ textAlign: "right" }}>Avg Views / Video</th>
                <th style={{ width: "100px", textAlign: "center" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {leaderboardData.map((item) => (
                <tr key={item.id} style={{ cursor: "pointer" }} onClick={() => onSelectChannel(item)}>
                  <td style={{ textAlign: "center" }}>
                    <span className={getRankBadgeClass(item.rank)}>{item.rank}</span>
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <img
                        src={item.thumbnail_url || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=80"}
                        alt={item.title}
                        style={{ width: "40px", height: "40px", borderRadius: "50%", objectFit: "cover" }}
                      />
                      <div>
                        <div style={{ fontWeight: 700, fontSize: "0.95rem" }}>{item.title}</div>
                        <span style={{ fontSize: "0.8rem", color: "var(--accent-secondary)" }}>
                          {item.custom_url || item.channel_id}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td style={{ textAlign: "right", fontWeight: 700, fontSize: "0.95rem" }}>
                    {formatCompactNumber(item.subscriber_count)}
                  </td>
                  <td style={{ textAlign: "right", fontWeight: 700, fontSize: "0.95rem" }}>
                    {formatCompactNumber(item.view_count)}
                  </td>
                  <td style={{ textAlign: "right", fontWeight: 600 }}>
                    {formatFullNumber(item.video_count)}
                  </td>
                  <td style={{ textAlign: "right", fontWeight: 700, color: "var(--accent-secondary)" }}>
                    {formatCompactNumber(item.avg_views_per_video)}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => onSelectChannel(item)}>
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}

              {leaderboardData.length === 0 && (
                <tr>
                  <td colSpan="7" style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                    No creators found in the database. Track channels to populate the leaderboard.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
