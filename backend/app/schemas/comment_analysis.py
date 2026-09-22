from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Standard sentiment categories
SentimentType = Literal["positive", "neutral", "negative"]

# Standard creator comment intents
VALID_INTENTS = {
    "praise",
    "criticism",
    "question",
    "content_request",
    "suggestion",
    "feedback",
    "information_request",
    "spam",
    "promotion",
    "personal_experience",
    "other",
}


class CommentAnalysisResult(BaseModel):
    """
    Structured AI output schema for YouTube comment intelligence.
    Enforces strict validation before database persistence.
    """
    sentiment: SentimentType = Field(
        ...,
        description="Sentiment classification: positive, neutral, or negative",
    )
    sentiment_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized sentiment intensity score between 0.0 (minimal/weak) and 1.0 (strong/intense)",
    )
    intent: str = Field(
        ...,
        max_length=100,
        description="Primary intent: praise, criticism, question, content_request, suggestion, feedback, information_request, spam, promotion, personal_experience, other",
    )
    topic: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Concise primary topic of the comment (e.g., Python, Video Quality, Tutorial, Audio)",
    )
    is_question: bool = Field(
        ...,
        description="True if the comment poses a question or inquiry",
    )
    is_actionable: bool = Field(
        ...,
        description="True if the creator can reasonably take concrete action based on this comment",
    )

    @field_validator("sentiment", mode="before")
    @classmethod
    def normalize_sentiment(cls, v: str) -> str:
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ("positive", "neutral", "negative"):
                return v_lower
        return v

    @field_validator("intent", mode="before")
    @classmethod
    def normalize_intent(cls, v: str) -> str:
        if isinstance(v, str):
            v_norm = v.strip().lower().replace(" ", "_")
            if v_norm in VALID_INTENTS:
                return v_norm
            return "other"
        return "other"

    @field_validator("topic", mode="before")
    @classmethod
    def clean_topic(cls, v: str) -> str:
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean:
                return v_clean[:100]
        return "General"


class CommentAnalysisResponse(BaseModel):
    """
    API response schema representing a stored CommentAnalysis database record.
    """
    id: int
    comment_id: int
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    intent: Optional[str] = None
    topic: Optional[str] = None
    is_question: bool = False
    is_actionable: bool = False
    model: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchAnalysisResult(BaseModel):
    """
    Aggregated outcome metrics returned after analyzing a batch of comments.
    """
    total_comments: int
    already_analyzed: int
    analyzed: int
    failed: int
    error_message: Optional[str] = None


class TopicBreakdown(BaseModel):
    topic: str
    count: int
    percentage: float


class IntentBreakdown(BaseModel):
    intent: str
    count: int
    percentage: float


class SentimentDistribution(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    positive_percentage: float = 0.0
    neutral_percentage: float = 0.0
    negative_percentage: float = 0.0
    average_sentiment_score: float = 0.0
    label: str = "No Data"


class CommentIntelligenceSummaryResponse(BaseModel):
    """
    Comprehensive comment intelligence metrics and aggregation summary for a video.
    """
    video_id: int
    total_comments: int
    analyzed_comments: int
    coverage_percentage: float
    sentiment: SentimentDistribution
    top_topics: list[TopicBreakdown]
    top_intents: list[IntentBreakdown]
    actionable_count: int
    actionable_percentage: float
    question_count: int
    question_percentage: float
