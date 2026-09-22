import React, { useState, useEffect, useCallback } from "react";
import {
  X,
  MessageSquare,
  ThumbsUp,
  Loader2,
  RefreshCw,
  Database,
  CheckCircle2,
  Sparkles,
  HelpCircle,
  Zap,
  TrendingUp,
  Tag,
  AlertTriangle,
  RotateCw,
} from "lucide-react";
import { api } from "../services/api";
import { formatCompactNumber, formatTimeAgo } from "../utils/format";

export function computeSentimentLabel(pos = 0, neu = 0, neg = 0, count = 1) {
  if (count === 0) return "No Data";
  if (pos >= 60.0 && neg < 20.0) return "Mostly Positive";
  if (neg >= 40.0 || (neg >= 30.0 && neg > pos)) return "Mostly Negative";
  if (neu >= 50.0 && pos < 40.0 && neg < 20.0) return "Mostly Neutral";
  return "Mixed";
}

function getSentimentBadgeStyle(label) {
  switch (label) {
    case "Mostly Positive":
      return {
        bg: "rgba(16, 185, 129, 0.12)",
        border: "1px solid rgba(16, 185, 129, 0.3)",
        color: "#34d399",
      };
    case "Mostly Negative":
      return {
        bg: "rgba(239, 68, 68, 0.12)",
        border: "1px solid rgba(239, 68, 68, 0.3)",
        color: "#f87171",
      };
    case "Mostly Neutral":
      return {
        bg: "rgba(100, 116, 139, 0.12)",
        border: "1px solid rgba(100, 116, 139, 0.3)",
        color: "#94a3b8",
      };
    case "Mixed":
    default:
      return {
        bg: "rgba(99, 102, 241, 0.12)",
        border: "1px solid rgba(99, 102, 241, 0.3)",
        color: "#a5b4fc",
      };
  }
}

export default function CommentDrawer({ video, isOpen, onClose }) {
  const [comments, setComments] = useState([]);
  const [total, setTotal] = useState(0);
  const [intelligence, setIntelligence] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingIntel, setIsLoadingIntel] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzingCommentId, setAnalyzingCommentId] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const [error, setError] = useState(null);

  // Filter state
  const [sentimentFilter, setSentimentFilter] = useState(null);
  const [typeFilter, setTypeFilter] = useState(null); // 'actionable' | 'question'
  const [topicFilter, setTopicFilter] = useState(null);

  const videoIdentifier = video ? video.id || video.video_id : null;

  const loadIntelligence = useCallback(async (id) => {
    if (!id) return;
    setIsLoadingIntel(true);
    try {
      const data = await api.getVideoCommentIntelligence(id);
      setIntelligence(data);
    } catch {
      // Non-blocking: intelligence endpoint might have 0 analyzed comments
      setIntelligence(null);
    } finally {
      setIsLoadingIntel(false);
    }
  }, []);

  const loadComments = useCallback(
    async (id, sFilter, tFilter, topFilter) => {
      if (!id) return;
      setIsLoading(true);
      setError(null);
      try {
        const queryFilters = {};
        if (sFilter) queryFilters.sentiment = sFilter;
        if (tFilter === "actionable") queryFilters.is_actionable = true;
        if (tFilter === "question") queryFilters.is_question = true;

        const data = await api.getVideoComments(id, 100, 0, queryFilters);
        if (data && Array.isArray(data.items)) {
          let items = data.items;
          if (topFilter) {
            items = items.filter(
              (c) => c.analysis && c.analysis.topic && c.analysis.topic.toLowerCase() === topFilter.toLowerCase()
            );
          }
          setComments(items);
          setTotal(topFilter ? items.length : data.total);
        } else {
          setComments([]);
          setTotal(0);
        }
      } catch (err) {
        setError(err.message || "Could not load comments.");
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (videoIdentifier && isOpen) {
      setSyncStatus(null);
      setAnalysisStatus(null);
      setError(null);
      setSentimentFilter(null);
      setTypeFilter(null);
      setTopicFilter(null);
      loadComments(videoIdentifier, null, null, null);
      loadIntelligence(videoIdentifier);
    }
  }, [videoIdentifier, isOpen, loadComments, loadIntelligence]);

  // Re-fetch when filters change
  const handleFilterChange = (newSentiment, newType, newTopic) => {
    setSentimentFilter(newSentiment);
    setTypeFilter(newType);
    setTopicFilter(newTopic);
    loadComments(videoIdentifier, newSentiment, newType, newTopic);
  };

  const handleSyncComments = async () => {
    if (!videoIdentifier || isSyncing) return;
    setIsSyncing(true);
    setError(null);
    setSyncStatus(null);
    try {
      const res = await api.syncVideoComments(videoIdentifier, 100);
      setSyncStatus(
        `Synced ${res.comments_fetched} comments from YouTube (${res.comments_created} new, ${res.comments_updated} updated)`
      );
      await loadComments(videoIdentifier, sentimentFilter, typeFilter, topicFilter);
      await loadIntelligence(videoIdentifier);
    } catch (err) {
      setError(err.message || "Failed to synchronize comments from YouTube.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleBatchAnalyze = async (forceReanalyze = false) => {
    if (!videoIdentifier || isAnalyzing) return;
    setIsAnalyzing(true);
    setError(null);
    setAnalysisStatus(null);
    try {
      const res = await api.analyzeVideoComments(videoIdentifier, forceReanalyze);
      if (res.total_comments === 0) {
        setError("No comments found in database. Click 'Sync YouTube' first to fetch comments from YouTube.");
      } else if (res.error_message) {
        if (
          res.error_message.includes("insufficient_quota") ||
          res.error_message.includes("credit_balance_exhausted")
        ) {
          setError(
            "API Quota Exhausted: You have no credits remaining. Switch to Groq (free at console.groq.com) or add credits to continue."
          );
        } else if (res.error_message.includes("invalid_api_key")) {
          setError("Invalid API Key: Please verify GROQ_API_KEY or OPENAI_API_KEY in your backend/.env file.");
        } else {
          setError(`AI Error: ${res.error_message}`);
        }
      } else if (res.analyzed === 0 && res.already_analyzed > 0 && !forceReanalyze) {
        setAnalysisStatus(
          `All ${res.already_analyzed} comments are already analyzed! Click 'Re-analyze All' in the overview card to re-run analysis.`
        );
      } else {
        setAnalysisStatus(
          `AI Analysis complete: ${res.analyzed} comments analyzed (${res.already_analyzed} already cached, ${res.failed} failed).`
        );
      }
      await loadComments(videoIdentifier, sentimentFilter, typeFilter, topicFilter);
      await loadIntelligence(videoIdentifier);
    } catch (err) {
      setError(err.message || "AI comment analysis failed.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSingleAnalyze = async (commentId, forceReanalyze = false) => {
    if (!videoIdentifier || analyzingCommentId) return;
    setAnalyzingCommentId(commentId);
    setError(null);
    try {
      const updatedAnalysis = await api.analyzeSingleComment(videoIdentifier, commentId, forceReanalyze);
      setComments((prev) =>
        prev.map((c) => (c.id === commentId ? { ...c, analysis: updatedAnalysis } : c))
      );
      await loadIntelligence(videoIdentifier);
    } catch (err) {
      setError(err.message || "Failed to analyze comment.");
    } finally {
      setAnalyzingCommentId(null);
    }
  };

  if (!isOpen || !video) return null;

  const hasIntelligence = intelligence && intelligence.analyzed_comments > 0;
  const isApiKeyError =
    error &&
    (error.includes("OPENAI_API_KEY") ||
      error.includes("GROQ_API_KEY") ||
      error.includes("API key is not configured"));

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="drawer-dialog"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: "680px", width: "100%" }}
      >
        {/* Drawer Header */}
        <div
          className="modal-header"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "16px 20px",
            borderBottom: "1px solid var(--bg-card-border)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
            <div
              className="brand-icon"
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                background: "var(--accent-gradient)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Sparkles size={18} color="#fff" />
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
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
                {hasIntelligence && (
                  <span
                    style={{
                      fontSize: "0.72rem",
                      padding: "2px 8px",
                      borderRadius: "12px",
                      background: "rgba(16, 185, 129, 0.15)",
                      color: "var(--success, #10b981)",
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <Sparkles size={11} />
                    {intelligence.coverage_percentage}% analyzed
                  </span>
                )}
              </div>
              <p
                style={{
                  fontSize: "0.78rem",
                  color: "var(--text-muted)",
                  margin: "2px 0 0 0",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {video.title}
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
            {/* Sync Button */}
            <button
              className="btn btn-secondary btn-sm"
              style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.78rem", padding: "6px 10px" }}
              onClick={handleSyncComments}
              disabled={isSyncing || isLoading || isAnalyzing}
              title="Synchronize fresh comments from YouTube"
            >
              <RefreshCw size={13} className={isSyncing ? "spin" : ""} />
              <span>{isSyncing ? "Syncing..." : "Sync YouTube"}</span>
            </button>

            {/* AI Analyze Button */}
            <button
              className="btn btn-primary btn-sm"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "0.78rem",
                padding: "6px 12px",
                background: "var(--accent-gradient)",
              }}
              onClick={() => handleBatchAnalyze(false)}
              disabled={isAnalyzing || isSyncing || isLoading}
              title="Run AI classification on unprocessed comments"
            >
              <Sparkles size={13} className={isAnalyzing ? "spin" : ""} />
              <span>{isAnalyzing ? "Analyzing..." : "AI Analyze"}</span>
            </button>

            <button className="btn-icon" onClick={onClose} title="Close">
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Drawer Body */}
        <div
          className="modal-body"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "16px",
            padding: "20px",
            overflowY: "auto",
            maxHeight: "calc(100vh - 120px)",
          }}
        >
          {/* Status Banners */}
          {syncStatus && (
            <div
              style={{
                background: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "#6ee7b7",
                padding: "10px 14px",
                borderRadius: "var(--border-radius-md)",
                fontSize: "0.82rem",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <CheckCircle2 size={16} color="var(--success)" />
              <span>{syncStatus}</span>
            </div>
          )}

          {analysisStatus && (
            <div
              style={{
                background: "rgba(99, 102, 241, 0.1)",
                border: "1px solid rgba(99, 102, 241, 0.3)",
                color: "#a5b4fc",
                padding: "10px 14px",
                borderRadius: "var(--border-radius-md)",
                fontSize: "0.82rem",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <Sparkles size={16} color="var(--accent-primary)" />
              <span>{analysisStatus}</span>
            </div>
          )}

          {/* Missing AI API Key Banner */}
          {isApiKeyError && (
            <div
              style={{
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.3)",
                color: "#fbbf24",
                padding: "14px",
                borderRadius: "var(--border-radius-md)",
                fontSize: "0.84rem",
                display: "flex",
                gap: "10px",
                alignItems: "flex-start",
              }}
            >
              <AlertTriangle size={20} color="#f59e0b" style={{ flexShrink: 0, marginTop: "2px" }} />
              <div>
                <strong style={{ display: "block", marginBottom: "4px" }}>AI API Key Required</strong>
                <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "0.8rem", lineHeight: 1.4 }}>
                  Use <strong>Groq API</strong> (free tier at{" "}
                  <a
                    href="https://console.groq.com"
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "#38bdf8", textDecoration: "underline" }}
                  >
                    console.groq.com
                  </a>
                  ) or OpenAI. Add your key to <code>backend/.env</code>:
                  <br />
                  <code style={{ background: "rgba(0,0,0,0.3)", padding: "2px 6px", borderRadius: "4px", color: "#f8fafc", display: "inline-block", marginTop: "4px" }}>
                    GROQ_API_KEY=gsk_...
                  </code>
                </p>
              </div>
            </div>
          )}

          {/* Generic Error Banner */}
          {error && !isApiKeyError && (
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

          {/* Executive AI Analysis Report at the Top */}
          {hasIntelligence ? (
            <div className="intelligence-card" style={{ flexShrink: 0 }}>
              {/* Report Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px", marginBottom: "14px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div
                      style={{
                        background: "rgba(99, 102, 241, 0.25)",
                        padding: "6px",
                        borderRadius: "8px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Sparkles size={18} color="#818cf8" />
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: "1rem", fontWeight: 800, color: "#fff", letterSpacing: "0.01em" }}>
                        AI Comment Intelligence Report
                      </h4>
                      <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>
                        Analyzed using Groq AI ({intelligence.analyzed_comments} of {intelligence.total_comments} comments &bull; {intelligence.coverage_percentage}%)
                      </span>
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {intelligence.analyzed_comments < intelligence.total_comments && (
                    <button
                      className="btn btn-primary btn-sm"
                      style={{ padding: "4px 10px", fontSize: "0.75rem", background: "var(--accent-gradient)" }}
                      onClick={() => handleBatchAnalyze(false)}
                      disabled={isAnalyzing}
                      title="Analyze the remaining unclassified comments"
                    >
                      <Sparkles size={12} className={isAnalyzing ? "spin" : ""} />
                      <span>{isAnalyzing ? "Analyzing..." : "Analyze Remaining"}</span>
                    </button>
                  )}
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                    onClick={() => handleBatchAnalyze(true)}
                    disabled={isAnalyzing}
                    title="Re-run analysis on all comments"
                  >
                    <RotateCw size={12} className={isAnalyzing ? "spin" : ""} />
                    <span>{isAnalyzing ? "Running..." : "Re-analyze All"}</span>
                  </button>
                </div>
              </div>

              {/* Executive Audience Verdict Badge */}
              {(() => {
                const sentimentLabel =
                  intelligence.sentiment.label ||
                  computeSentimentLabel(
                    intelligence.sentiment.positive_percentage,
                    intelligence.sentiment.neutral_percentage,
                    intelligence.sentiment.negative_percentage,
                    intelligence.analyzed_comments
                  );
                const badgeStyle = getSentimentBadgeStyle(sentimentLabel);
                return (
                  <div
                    style={{
                      background: badgeStyle.bg,
                      border: badgeStyle.border,
                      borderRadius: "8px",
                      padding: "8px 12px",
                      marginBottom: "14px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      fontSize: "0.82rem",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <TrendingUp size={16} color={badgeStyle.color} />
                      <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                        Audience Sentiment:{" "}
                        <strong style={{ color: badgeStyle.color }}>
                          {sentimentLabel}
                        </strong>
                      </span>
                    </div>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      Avg Sentiment Score: {Math.round(intelligence.sentiment.average_sentiment_score * 100)}%
                    </span>
                  </div>
                );
              })()}

              {/* Visual Sentiment Distribution Bar */}
              <div style={{ marginBottom: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.74rem", color: "var(--text-muted)", marginBottom: "4px" }}>
                  <span>Sentiment Distribution</span>
                  <span>{intelligence.analyzed_comments} analyzed</span>
                </div>
                <div className="sentiment-bar-track">
                  <div
                    className="sentiment-bar-pos"
                    style={{ width: `${intelligence.sentiment.positive_percentage}%` }}
                    title={`Positive: ${intelligence.sentiment.positive_percentage}% (${intelligence.sentiment.positive})`}
                  />
                  <div
                    className="sentiment-bar-neu"
                    style={{ width: `${intelligence.sentiment.neutral_percentage}%` }}
                    title={`Neutral: ${intelligence.sentiment.neutral_percentage}% (${intelligence.sentiment.neutral})`}
                  />
                  <div
                    className="sentiment-bar-neg"
                    style={{ width: `${intelligence.sentiment.negative_percentage}%` }}
                    title={`Negative: ${intelligence.sentiment.negative_percentage}% (${intelligence.sentiment.negative})`}
                  />
                </div>
              </div>

              {/* 4 Stat Breakdown Metric Boxes */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4, 1fr)",
                  gap: "10px",
                  marginBottom: "14px",
                }}
              >
                <div
                  className="intel-stat-box"
                  style={{
                    borderTop: "2px solid #10b981",
                    cursor: "pointer",
                    background: sentimentFilter === "positive" ? "rgba(16, 185, 129, 0.15)" : undefined,
                  }}
                  onClick={() => handleFilterChange(sentimentFilter === "positive" ? null : "positive", typeFilter, topicFilter)}
                  title="Filter positive comments"
                >
                  <div style={{ fontSize: "0.72rem", color: "#34d399", fontWeight: 700, textTransform: "uppercase" }}>
                    Positive
                  </div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#fff", margin: "2px 0" }}>
                    {intelligence.sentiment.positive_percentage}%
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    {intelligence.sentiment.positive} comments
                  </div>
                </div>

                <div
                  className="intel-stat-box"
                  style={{
                    borderTop: "2px solid #64748b",
                    cursor: "pointer",
                    background: sentimentFilter === "neutral" ? "rgba(100, 116, 139, 0.15)" : undefined,
                  }}
                  onClick={() => handleFilterChange(sentimentFilter === "neutral" ? null : "neutral", typeFilter, topicFilter)}
                  title="Filter neutral comments"
                >
                  <div style={{ fontSize: "0.72rem", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>
                    Neutral
                  </div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#fff", margin: "2px 0" }}>
                    {intelligence.sentiment.neutral_percentage}%
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    {intelligence.sentiment.neutral} comments
                  </div>
                </div>

                <div
                  className="intel-stat-box"
                  style={{
                    borderTop: "2px solid #ef4444",
                    cursor: "pointer",
                    background: sentimentFilter === "negative" ? "rgba(239, 68, 68, 0.15)" : undefined,
                  }}
                  onClick={() => handleFilterChange(sentimentFilter === "negative" ? null : "negative", typeFilter, topicFilter)}
                  title="Filter negative comments"
                >
                  <div style={{ fontSize: "0.72rem", color: "#f87171", fontWeight: 700, textTransform: "uppercase" }}>
                    Negative
                  </div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#fff", margin: "2px 0" }}>
                    {intelligence.sentiment.negative_percentage}%
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    {intelligence.sentiment.negative} comments
                  </div>
                </div>

                <div className="intel-stat-box" style={{ borderTop: "2px solid #818cf8" }}>
                  <div style={{ fontSize: "0.72rem", color: "#818cf8", fontWeight: 700, textTransform: "uppercase" }}>
                    Avg Score
                  </div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#fff", margin: "2px 0" }}>
                    {Math.round(intelligence.sentiment.average_sentiment_score * 100)}%
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    Avg Sentiment Score
                  </div>
                </div>
              </div>

              {/* Actionable & Question Filter Signals */}
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "12px" }}>
                <div
                  className={`filter-pill ${typeFilter === "actionable" ? "active" : ""}`}
                  onClick={() =>
                    handleFilterChange(
                      sentimentFilter,
                      typeFilter === "actionable" ? null : "actionable",
                      topicFilter
                    )
                  }
                  style={{
                    cursor: "pointer",
                    padding: "7px 14px",
                    background: typeFilter === "actionable" ? "rgba(245, 158, 11, 0.25)" : "rgba(245, 158, 11, 0.08)",
                    border: "1px solid rgba(245, 158, 11, 0.35)",
                    color: "#fcd34d",
                  }}
                >
                  <Zap size={14} color="#f59e0b" />
                  <span>
                    <strong>{intelligence.actionable_count}</strong> Actionable Feedback ({intelligence.actionable_percentage}%)
                  </span>
                </div>

                <div
                  className={`filter-pill ${typeFilter === "question" ? "active" : ""}`}
                  onClick={() =>
                    handleFilterChange(
                      sentimentFilter,
                      typeFilter === "question" ? null : "question",
                      topicFilter
                    )
                  }
                  style={{
                    cursor: "pointer",
                    padding: "7px 14px",
                    background: typeFilter === "question" ? "rgba(6, 182, 212, 0.25)" : "rgba(6, 182, 212, 0.08)",
                    border: "1px solid rgba(6, 182, 212, 0.35)",
                    color: "#67e8f9",
                  }}
                >
                  <HelpCircle size={14} color="#38bdf8" />
                  <span>
                    <strong>{intelligence.question_count}</strong> Questions Asked ({intelligence.question_percentage}%)
                  </span>
                </div>
              </div>

              {/* Top Topics Cloud */}
              {intelligence.top_topics && intelligence.top_topics.length > 0 && (
                <div style={{ paddingTop: "8px", borderTop: "1px solid rgba(255, 255, 255, 0.06)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                    <Tag size={13} color="var(--text-muted)" />
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.03em" }}>
                      Key Discussion Topics:
                    </span>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {intelligence.top_topics.map((t) => {
                      const isActive = topicFilter === t.topic;
                      return (
                        <span
                          key={t.topic}
                          className="topic-tag"
                          style={{
                            background: isActive ? "rgba(99, 102, 241, 0.4)" : undefined,
                            borderColor: isActive ? "var(--accent-primary)" : undefined,
                            fontWeight: isActive ? 700 : 600,
                            boxShadow: isActive ? "0 0 10px rgba(99, 102, 241, 0.4)" : undefined,
                          }}
                          onClick={() =>
                            handleFilterChange(
                              sentimentFilter,
                              typeFilter,
                              isActive ? null : t.topic
                            )
                          }
                        >
                          #{t.topic} <span style={{ opacity: 0.75 }}>({t.count})</span>
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Call-to-Action Card when 0 comments are analyzed */
            <div
              className="intelligence-card"
              style={{
                textAlign: "center",
                padding: "24px 20px",
                borderStyle: "dashed",
                borderColor: "rgba(99, 102, 241, 0.4)",
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "12px",
                  background: "var(--accent-gradient)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 12px",
                }}
              >
                <Sparkles size={24} color="#fff" />
              </div>
              <h4 style={{ margin: "0 0 6px", fontSize: "1.05rem", fontWeight: 700, color: "#fff" }}>
                AI Comment Intelligence Report
              </h4>
              <p style={{ fontSize: "0.84rem", color: "var(--text-secondary)", maxWidth: "420px", margin: "0 auto 16px", lineHeight: 1.5 }}>
                Generate an AI-powered sentiment overview, question detection, creator action items, and topic extraction using your free Groq API.
              </p>
              <button
                className="btn btn-primary"
                onClick={() => handleBatchAnalyze(false)}
                disabled={isAnalyzing || isSyncing}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 20px",
                  fontSize: "0.85rem",
                  background: "var(--accent-gradient)",
                  boxShadow: "0 4px 20px rgba(99, 102, 241, 0.35)",
                }}
              >
                <Sparkles size={16} className={isAnalyzing ? "spin" : ""} />
                <span>{isAnalyzing ? "Analyzing Comments with Groq..." : "Generate AI Analysis Report"}</span>
              </button>
            </div>
          )}

          {/* Quick Filter Bar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "8px",
              padding: "4px 0",
              flexShrink: 0,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
              <button
                className={`filter-pill ${!sentimentFilter && !typeFilter && !topicFilter ? "active" : ""}`}
                onClick={() => handleFilterChange(null, null, null)}
              >
                All ({total})
              </button>
              <button
                className={`filter-pill ${sentimentFilter === "positive" ? "active" : ""}`}
                onClick={() =>
                  handleFilterChange(
                    sentimentFilter === "positive" ? null : "positive",
                    typeFilter,
                    topicFilter
                  )
                }
              >
                😊 Positive
              </button>
              <button
                className={`filter-pill ${sentimentFilter === "neutral" ? "active" : ""}`}
                onClick={() =>
                  handleFilterChange(
                    sentimentFilter === "neutral" ? null : "neutral",
                    typeFilter,
                    topicFilter
                  )
                }
              >
                😐 Neutral
              </button>
              <button
                className={`filter-pill ${sentimentFilter === "negative" ? "active" : ""}`}
                onClick={() =>
                  handleFilterChange(
                    sentimentFilter === "negative" ? null : "negative",
                    typeFilter,
                    topicFilter
                  )
                }
              >
                🙁 Negative
              </button>
            </div>

            {topicFilter && (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "rgba(99, 102, 241, 0.15)",
                  color: "var(--accent-primary)",
                  padding: "4px 10px",
                  borderRadius: "var(--border-radius-pill)",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                }}
              >
                <span>Filtered by: #{topicFilter}</span>
                <button
                  onClick={() => handleFilterChange(sentimentFilter, typeFilter, null)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "inherit",
                    cursor: "pointer",
                    padding: 0,
                    display: "flex",
                  }}
                >
                  <X size={12} />
                </button>
              </div>
            )}
          </div>

          {/* Loading Indicator */}
          {isLoading && (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
              <Loader2 size={32} className="spin" style={{ margin: "0 auto 12px" }} />
              <p>Loading comments...</p>
            </div>
          )}

          {/* Empty State: No comments */}
          {!isLoading && !error && comments.length === 0 && (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
              <Database size={36} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
              <p style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
                {sentimentFilter || typeFilter || topicFilter
                  ? "No comments match the active filters"
                  : "No comments stored yet"}
              </p>
              <p style={{ fontSize: "0.85rem", maxWidth: "320px", margin: "0 auto 16px" }}>
                {sentimentFilter || typeFilter || topicFilter
                  ? "Try resetting filters or analyzing more comments."
                  : "Synchronize comments from YouTube, then trigger AI analysis to see sentiment and intent insights."}
              </p>
              {sentimentFilter || typeFilter || topicFilter ? (
                <button className="btn btn-secondary btn-sm" onClick={() => handleFilterChange(null, null, null)}>
                  Reset Filters
                </button>
              ) : (
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleSyncComments}
                  disabled={isSyncing}
                  style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                >
                  <RefreshCw size={13} className={isSyncing ? "spin" : ""} />
                  <span>{isSyncing ? "Syncing..." : "Sync Comments Now"}</span>
                </button>
              )}
            </div>
          )}

          {/* Comment Cards */}
          {!isLoading &&
            comments.map((c) => {
              const analysis = c.analysis;
              const isActionable = analysis && analysis.is_actionable;
              const isQuestion = analysis && analysis.is_question;
              const isAnalyzingThis = analyzingCommentId === c.id;

              return (
                <div
                  key={c.id || c.youtube_comment_id}
                  className={
                    isActionable
                      ? "comment-card-actionable"
                      : analysis && analysis.sentiment === "positive"
                      ? "comment-card-positive"
                      : analysis && analysis.sentiment === "negative"
                      ? "comment-card-negative"
                      : analysis && analysis.sentiment === "neutral"
                      ? "comment-card-neutral"
                      : ""
                  }
                  style={{
                    display: "flex",
                    gap: "14px",
                    padding: "14px",
                    background: "rgba(255,255,255,0.02)",
                    borderRadius: "var(--border-radius-md)",
                    border: "1px solid var(--bg-card-border)",
                    transition: "all var(--transition-fast)",
                  }}
                >
                  <img
                    src={c.author_profile_image || "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=60"}
                    alt={c.author_name || "Viewer"}
                    style={{ width: "38px", height: "38px", borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
                  />

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "6px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>
                          {c.author_name || "YouTube Viewer"}
                        </span>
                        <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                          {formatTimeAgo(c.published_at)}
                        </span>
                      </div>

                      {/* AI Badges on top right */}
                      {analysis && (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          {analysis.sentiment && (
                            <span className={`sentiment-badge sentiment-badge-${analysis.sentiment}`}>
                              {analysis.sentiment === "positive" && "😊"}
                              {analysis.sentiment === "neutral" && "😐"}
                              {analysis.sentiment === "negative" && "🙁"}
                              {analysis.sentiment} {analysis.sentiment_score ? `(${Math.round(analysis.sentiment_score * 100)}%)` : ""}
                            </span>
                          )}
                          {isActionable && (
                            <span className="actionable-badge" title="Creator can act upon this">
                              <Zap size={11} /> Actionable
                            </span>
                          )}
                          {isQuestion && (
                            <span className="question-badge" title="Viewer inquiry">
                              <HelpCircle size={11} /> Question
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    <p
                      style={{
                        fontSize: "0.85rem",
                        color: "var(--text-secondary)",
                        lineHeight: 1.45,
                        wordBreak: "break-word",
                        margin: 0,
                      }}
                    >
                      {c.text}
                    </p>

                    {/* Metadata & Tag Footer */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginTop: "10px",
                        paddingTop: "6px",
                        borderTop: "1px solid rgba(255,255,255,0.03)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                            fontSize: "0.75rem",
                            color: "var(--text-muted)",
                          }}
                        >
                          <ThumbsUp size={12} />
                          <span>{formatCompactNumber(c.like_count)}</span>
                        </div>

                        {analysis && analysis.topic && (
                          <span
                            className="topic-tag"
                            onClick={() => handleFilterChange(sentimentFilter, typeFilter, analysis.topic)}
                            title={`Filter by #${analysis.topic}`}
                          >
                            #{analysis.topic}
                          </span>
                        )}

                        {analysis && analysis.intent && (
                          <span
                            style={{
                              fontSize: "0.7rem",
                              color: "var(--text-muted)",
                              textTransform: "capitalize",
                              background: "rgba(255,255,255,0.04)",
                              padding: "2px 6px",
                              borderRadius: "4px",
                            }}
                          >
                            {analysis.intent.replace("_", " ")}
                          </span>
                        )}
                      </div>

                      {/* Single comment analysis trigger */}
                      <div>
                        {analysis ? (
                          <button
                            onClick={() => handleSingleAnalyze(c.id, true)}
                            disabled={isAnalyzingThis}
                            style={{
                              background: "none",
                              border: "none",
                              color: "var(--text-muted)",
                              cursor: "pointer",
                              fontSize: "0.72rem",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              padding: "2px 6px",
                              borderRadius: "4px",
                            }}
                            title="Re-analyze comment with AI"
                          >
                            <RotateCw size={11} className={isAnalyzingThis ? "spin" : ""} />
                            <span>{isAnalyzingThis ? "Analyzing..." : "Re-analyze"}</span>
                          </button>
                        ) : (
                          <button
                            onClick={() => handleSingleAnalyze(c.id, false)}
                            disabled={isAnalyzingThis}
                            className="btn btn-secondary btn-sm"
                            style={{ padding: "2px 8px", fontSize: "0.72rem", height: "auto" }}
                            title="Analyze this comment with AI"
                          >
                            <Sparkles size={11} className={isAnalyzingThis ? "spin" : ""} color="var(--accent-primary)" />
                            <span>{isAnalyzingThis ? "Analyzing..." : "Analyze"}</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
}
