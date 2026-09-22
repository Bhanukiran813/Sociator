# 🚀 Sociator

> YouTube Creator Intelligence & Analytics Platform

Sociator is an AI-powered platform for analyzing YouTube channels, videos, and audience feedback.

It helps creators, marketers, talent agencies, and brands understand channel performance, audience sentiment, engagement, and content opportunities from a single dashboard.

---

## ✨ Features

### 📊 YouTube Channel Analytics
- Track YouTube channels using channel ID or supported identifiers
- View subscribers, views, video count and channel information
- Track channel growth through analytics snapshots
- Automatically synchronize channel data

### 🎥 Video Analytics
- View recent videos
- Analyze video-level performance
- Track views, likes, comments and engagement
- Sort and paginate video data

### 💬 Comment Intelligence
- Fetch and store YouTube comments
- Analyze comments using an LLM
- Sentiment classification:
  - Positive
  - Neutral
  - Negative
- Detect comment intent
- Identify topics
- Detect questions
- Identify actionable feedback
- Generate aggregated audience insights

### 📈 Growth Tracking
- Store historical analytics snapshots
- Compare channel metrics over time
- Visualize growth trends

### 🤖 AI-Powered Insights
Sociator uses LLM-based analysis to transform raw audience comments into structured insights.

---

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │      YouTube API    │
                    └──────────┬──────────┘
                               │
                               ▼
┌──────────────┐       ┌──────────────────┐
│    React     │ ◄──── │     FastAPI      │
│   Frontend   │       │      Backend     │
└──────────────┘       └────────┬─────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
             ┌──────────────┐       ┌──────────────┐
             │ PostgreSQL   │       │ LLM Provider │
             │   Database   │       │    (Groq)    │
             └──────────────┘       └──────────────┘
