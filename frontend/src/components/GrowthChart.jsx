import React, { useState } from "react";
import { formatCompactNumber, formatDate } from "../utils/format";

export default function GrowthChart({ snapshots = [], metric = "views", title = "Growth Trajectory" }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="chart-card" style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
        <p>No historical snapshot data recorded yet.</p>
        <span style={{ fontSize: "0.8rem", marginTop: "4px", display: "inline-block" }}>
          Trigger sync to capture point-in-time metrics.
        </span>
      </div>
    );
  }

  // Sort chronological
  const sorted = [...snapshots].sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at));

  // If only 1 snapshot, duplicate for visual line
  const data = sorted.length === 1 ? [sorted[0], sorted[0]] : sorted;

  const values = data.map((d) => (metric === "subscribers" ? d.subscribers || 0 : d.views || 0));
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  // Chart coordinate space
  const width = 500;
  const height = 160;
  const paddingX = 40;
  const paddingY = 20;

  const points = data.map((d, index) => {
    const x = paddingX + (index / (data.length - 1)) * (width - 2 * paddingX);
    const val = metric === "subscribers" ? d.subscribers || 0 : d.views || 0;
    const y = height - paddingY - ((val - minVal) / range) * (height - 2 * paddingY);
    return { x, y, val, date: d.recorded_at };
  });

  const pathD = points.reduce((acc, pt, i) => {
    return i === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
  }, "");

  const areaD = `${pathD} L ${points[points.length - 1].x} ${height - paddingY} L ${points[0].x} ${height - paddingY} Z`;

  const isSubs = metric === "subscribers";
  const strokeColor = isSubs ? "#06b6d4" : "#6366f1";
  const fillGradientId = isSubs ? "cyanGradient" : "indigoGradient";

  return (
    <div className="chart-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h4 style={{ fontSize: "0.95rem", color: "var(--text-secondary)" }}>{title}</h4>
        <span style={{ fontSize: "0.8rem", color: strokeColor, fontWeight: 700 }}>
          Latest: {formatCompactNumber(values[values.length - 1])} {isSubs ? "Subscribers" : "Views"}
        </span>
      </div>

      <div style={{ position: "relative" }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="chart-svg"
          style={{ width: "100%", height: "180px", overflow: "visible" }}
        >
          <defs>
            <linearGradient id="indigoGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="cyanGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Background grid lines */}
          <line x1={paddingX} y1={paddingY} x2={width - paddingX} y2={paddingY} stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
          <line x1={paddingX} y1={height / 2} x2={width - paddingX} y2={height / 2} stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
          <line x1={paddingX} y1={height - paddingY} x2={width - paddingX} y2={height - paddingY} stroke="rgba(255,255,255,0.08)" />

          {/* Area Fill */}
          <path d={areaD} fill={`url(#${fillGradientId})`} />

          {/* Line Path */}
          <path d={pathD} fill="none" stroke={strokeColor} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

          {/* Data Points */}
          {points.map((pt, idx) => (
            <circle
              key={idx}
              cx={pt.x}
              cy={pt.y}
              r={hoveredPoint === idx ? 6 : 4}
              fill="#ffffff"
              stroke={strokeColor}
              strokeWidth="2.5"
              style={{ cursor: "pointer", transition: "all 0.15s ease" }}
              onMouseEnter={() => setHoveredPoint(idx)}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          ))}
        </svg>

        {/* Hover Tooltip */}
        {hoveredPoint !== null && points[hoveredPoint] && (
          <div
            style={{
              position: "absolute",
              left: `${(points[hoveredPoint].x / width) * 100}%`,
              top: `${(points[hoveredPoint].y / height) * 100 - 35}%`,
              transform: "translateX(-50%)",
              background: "#1e293b",
              border: "1px solid rgba(255,255,255,0.15)",
              borderRadius: "6px",
              padding: "4px 8px",
              fontSize: "0.75rem",
              color: "#ffffff",
              whiteSpace: "nowrap",
              pointerEvents: "none",
              boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
              zIndex: 10,
            }}
          >
            <strong>{formatCompactNumber(points[hoveredPoint].val)}</strong> ({formatDate(points[hoveredPoint].date)})
          </div>
        )}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "0.72rem", color: "var(--text-muted)" }}>
        <span>Start: {formatDate(data[0]?.recorded_at)}</span>
        <span>Latest: {formatDate(data[data.length - 1]?.recorded_at)}</span>
      </div>
    </div>
  );
}
