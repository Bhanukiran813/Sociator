import React from "react";

export default function StatCard({ label, value, icon: Icon, color = "indigo", subtext }) {
  return (
    <div className="stat-card">
      <div className="stat-content">
        <span className="stat-label">{label}</span>
        <span className="stat-value">{value}</span>
        {subtext && (
          <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            {subtext}
          </span>
        )}
      </div>
      <div className={`stat-icon-wrapper ${color}`}>
        {Icon && <Icon size={24} />}
      </div>
    </div>
  );
}
