/**
 * Sociator API Client
 * Connects frontend to the FastAPI backend at http://localhost:8000/api/v1
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const config = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        // Fallback to text
        const errorText = await response.text();
        if (errorText) errorDetail = errorText;
      }
      throw new Error(errorDetail);
    }
    if (response.status === 204) {
      return null;
    }
    return await response.json();
  } catch (error) {
    console.error(`API Error on [${options.method || "GET"} ${endpoint}]:`, error);
    throw error;
  }
}

export const api = {
  // System Health & Scheduler
  getHealth: () => request("/health"),

  // Channels
  getChannels: (search = "", limit = 50) => {
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (limit) params.append("limit", limit);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request(`/channels${qs}`);
  },

  searchYouTubeChannels: (q, limit = 10) => {
    return request(`/channels/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  },

  trackChannel: (identifier) => {
    return request("/channels/track", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    });
  },

  getChannel: (identifier) => request(`/channels/${encodeURIComponent(identifier)}`),

  syncChannel: (identifier) => {
    return request(`/channels/${encodeURIComponent(identifier)}/sync`, {
      method: "POST",
    });
  },

  deleteChannel: (identifier) => {
    return request(`/channels/${encodeURIComponent(identifier)}`, {
      method: "DELETE",
    });
  },

  syncAllChannels: () => {
    return request("/channels/sync-all", {
      method: "POST",
    });
  },

  // Videos
  getVideos: ({ channel = "", sortBy = "published_at", order = "desc", limit = 50 } = {}) => {
    const params = new URLSearchParams();
    if (channel) params.append("channel", channel);
    if (sortBy) params.append("sort_by", sortBy);
    if (order) params.append("order", order);
    if (limit) params.append("limit", limit);
    return request(`/videos?${params.toString()}`);
  },

  trackVideo: (identifier) => {
    return request("/videos/track", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    });
  },

  getVideo: (identifier) => request(`/videos/${encodeURIComponent(identifier)}`),

  syncVideo: (identifier) => {
    return request(`/videos/${encodeURIComponent(identifier)}/sync`, {
      method: "POST",
    });
  },

  getVideoComments: (identifier, limit = 50, skip = 0, filters = {}) => {
    const params = new URLSearchParams({ limit, skip });
    if (filters.sentiment) params.append("sentiment", filters.sentiment);
    if (filters.intent) params.append("intent", filters.intent);
    if (filters.is_question !== undefined && filters.is_question !== null) {
      params.append("is_question", filters.is_question);
    }
    if (filters.is_actionable !== undefined && filters.is_actionable !== null) {
      params.append("is_actionable", filters.is_actionable);
    }
    if (filters.has_analysis !== undefined && filters.has_analysis !== null) {
      params.append("has_analysis", filters.has_analysis);
    }
    return request(`/videos/${encodeURIComponent(identifier)}/comments?${params.toString()}`);
  },

  syncVideoComments: (identifier, maxResults = 100) => {
    return request(`/videos/${encodeURIComponent(identifier)}/comments/sync?max_results=${maxResults}`, {
      method: "POST",
    });
  },

  analyzeVideoComments: (identifier, forceReanalyze = false, limit = null) => {
    const params = new URLSearchParams({ force_reanalyze: forceReanalyze });
    if (limit) params.append("limit", limit);
    return request(`/videos/${encodeURIComponent(identifier)}/comments/analyze?${params.toString()}`, {
      method: "POST",
    });
  },

  analyzeSingleComment: (videoIdentifier, commentId, forceReanalyze = false) => {
    return request(
      `/videos/${encodeURIComponent(videoIdentifier)}/comments/${commentId}/analyze?force_reanalyze=${forceReanalyze}`,
      {
        method: "POST",
      }
    );
  },

  getVideoCommentIntelligence: (identifier) => {
    return request(`/videos/${encodeURIComponent(identifier)}/comments/intelligence`);
  },

  deleteVideo: (identifier) => {
    return request(`/videos/${encodeURIComponent(identifier)}`, {
      method: "DELETE",
    });
  },

  // Analytics & Insights
  getLeaderboard: (sortBy = "subscribers", limit = 50) => {
    return request(`/analytics/leaderboard?sort_by=${sortBy}&limit=${limit}`);
  },

  compareChannels: (identifiers) => {
    const idList = Array.isArray(identifiers) ? identifiers.join(",") : identifiers;
    return request(`/analytics/compare?identifiers=${encodeURIComponent(idList)}`);
  },

  getChannelGrowth: (identifier) => {
    return request(`/analytics/channel/${encodeURIComponent(identifier)}`);
  },

  getChannelSnapshots: (identifier, limit = 50) => {
    return request(`/analytics/channel/${encodeURIComponent(identifier)}/snapshots?limit=${limit}`);
  },
};
