from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.channel import Channel
from app.models.video import Video
from app.models.comment import Comment
from app.models.comment_analysis import CommentAnalysis
from app.schemas.comment_analysis import CommentAnalysisResult
from app.services.comment_intelligence import comment_intelligence_service, CommentIntelligenceConfigError


# In-memory SQLite engine with StaticPool to share connection across threads
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db_session):
    channel = Channel(
        channel_id="UC_API_123",
        title="Coding Tutorials",
        custom_url="@codingtutorials",
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)

    video = Video(
        channel_id=channel.id,
        video_id="VID_API_123",
        title="Python Full Course",
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    c1 = Comment(
        video_id=video.id,
        youtube_comment_id="yt_c_1",
        text="This tutorial was fantastic, thank you so much!",
        like_count=10,
    )
    c2 = Comment(
        video_id=video.id,
        youtube_comment_id="yt_c_2",
        text="Could you please make a video about Docker containers next?",
        like_count=4,
    )
    c3 = Comment(
        video_id=video.id,
        youtube_comment_id="yt_c_3",
        text="The volume in the second half is way too quiet.",
        like_count=8,
    )
    db_session.add_all([c1, c2, c3])
    db_session.commit()
    for c in [c1, c2, c3]:
        db_session.refresh(c)

    return {
        "channel": channel,
        "video": video,
        "comments": [c1, c2, c3],
    }


def create_mock_completion(parsed_result: CommentAnalysisResult):
    mock_message = MagicMock()
    mock_message.parsed = parsed_result
    mock_message.refusal = None
    mock_message.content = parsed_result.model_dump_json()

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    return mock_completion


# ---------------------------------------------------------------------------
# TEST: Batch Comment Analysis API
# ---------------------------------------------------------------------------
def test_api_batch_analyze_comments(client, seed_data):
    video = seed_data["video"]

    ai_result = CommentAnalysisResult(
        sentiment="positive",
        sentiment_score=0.92,
        intent="praise",
        topic="Python",
        is_question=False,
        is_actionable=False,
    )

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=create_mock_completion(ai_result)
    )

    with patch.object(comment_intelligence_service, "get_client", return_value=mock_client):
        response = client.post(f"/api/v1/videos/{video.id}/comments/analyze")
        assert response.status_code == 200
        data = response.json()
        assert data["total_comments"] == 3
        assert data["already_analyzed"] == 0
        assert data["analyzed"] == 3
        assert data["failed"] == 0

        # Running again without force should skip all
        response2 = client.post(f"/api/v1/videos/{video.id}/comments/analyze")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["already_analyzed"] == 3
        assert data2["analyzed"] == 0


# ---------------------------------------------------------------------------
# TEST: Single Comment Analysis API
# ---------------------------------------------------------------------------
def test_api_single_comment_analyze(client, seed_data):
    video = seed_data["video"]
    comment = seed_data["comments"][1]

    ai_result = CommentAnalysisResult(
        sentiment="positive",
        sentiment_score=0.85,
        intent="content_request",
        topic="Docker",
        is_question=True,
        is_actionable=True,
    )

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=create_mock_completion(ai_result)
    )

    with patch.object(comment_intelligence_service, "get_client", return_value=mock_client):
        response = client.post(f"/api/v1/videos/{video.id}/comments/{comment.id}/analyze")
        assert response.status_code == 200
        data = response.json()
        assert data["comment_id"] == comment.id
        assert data["sentiment"] == "positive"
        assert data["intent"] == "content_request"
        assert data["topic"] == "Docker"
        assert data["is_question"] is True
        assert data["is_actionable"] is True


# ---------------------------------------------------------------------------
# TEST: Filtered Comments Listing
# ---------------------------------------------------------------------------
def test_api_get_comments_with_analysis_and_filters(client, seed_data, db_session):
    video = seed_data["video"]
    c1, c2, c3 = seed_data["comments"]

    # Pre-populate analyses
    a1 = CommentAnalysis(
        comment_id=c1.id,
        sentiment="positive",
        sentiment_score=0.9,
        intent="praise",
        topic="Python",
        is_question=False,
        is_actionable=False,
        model="gpt-4o-mini",
        analyzed_at=datetime.now(timezone.utc),
    )
    a2 = CommentAnalysis(
        comment_id=c2.id,
        sentiment="positive",
        sentiment_score=0.8,
        intent="content_request",
        topic="Docker",
        is_question=True,
        is_actionable=True,
        model="gpt-4o-mini",
        analyzed_at=datetime.now(timezone.utc),
    )
    a3 = CommentAnalysis(
        comment_id=c3.id,
        sentiment="negative",
        sentiment_score=0.85,
        intent="criticism",
        topic="Audio Quality",
        is_question=False,
        is_actionable=True,
        model="gpt-4o-mini",
        analyzed_at=datetime.now(timezone.utc),
    )
    db_session.add_all([a1, a2, a3])
    db_session.commit()

    # 1. Fetch all comments - verify analysis is populated
    res_all = client.get(f"/api/v1/videos/{video.id}/comments")
    assert res_all.status_code == 200
    all_data = res_all.json()
    assert all_data["total"] == 3
    assert all_data["items"][0]["analysis"] is not None

    # 2. Filter by sentiment=negative
    res_neg = client.get(f"/api/v1/videos/{video.id}/comments?sentiment=negative")
    assert res_neg.status_code == 200
    neg_data = res_neg.json()
    assert neg_data["total"] == 1
    assert neg_data["items"][0]["text"] == c3.text

    # 3. Filter by is_question=true
    res_q = client.get(f"/api/v1/videos/{video.id}/comments?is_question=true")
    assert res_q.status_code == 200
    q_data = res_q.json()
    assert q_data["total"] == 1
    assert q_data["items"][0]["text"] == c2.text

    # 4. Filter by is_actionable=true
    res_act = client.get(f"/api/v1/videos/{video.id}/comments?is_actionable=true")
    assert res_act.status_code == 200
    act_data = res_act.json()
    assert act_data["total"] == 2


# ---------------------------------------------------------------------------
# TEST: Comment Intelligence Summary & Aggregation API
# ---------------------------------------------------------------------------
def test_api_comment_intelligence_summary(client, seed_data, db_session):
    video = seed_data["video"]
    c1, c2, c3 = seed_data["comments"]

    # Pre-populate analyses
    a1 = CommentAnalysis(
        comment_id=c1.id,
        sentiment="positive",
        sentiment_score=0.95,
        intent="praise",
        topic="Python",
        is_question=False,
        is_actionable=False,
    )
    a2 = CommentAnalysis(
        comment_id=c2.id,
        sentiment="positive",
        sentiment_score=0.85,
        intent="content_request",
        topic="Docker",
        is_question=True,
        is_actionable=True,
    )
    a3 = CommentAnalysis(
        comment_id=c3.id,
        sentiment="negative",
        sentiment_score=0.70,
        intent="criticism",
        topic="Audio Quality",
        is_question=False,
        is_actionable=True,
    )
    db_session.add_all([a1, a2, a3])
    db_session.commit()

    res = client.get(f"/api/v1/videos/{video.id}/comments/intelligence")
    assert res.status_code == 200
    data = res.json()

    assert data["video_id"] == video.id
    assert data["total_comments"] == 3
    assert data["analyzed_comments"] == 3
    assert data["coverage_percentage"] == 100.0

    # Sentiment distribution
    sentiment = data["sentiment"]
    assert sentiment["positive"] == 2
    assert sentiment["negative"] == 1
    assert sentiment["neutral"] == 0
    assert sentiment["positive_percentage"] == 66.67
    assert sentiment["negative_percentage"] == 33.33
    assert sentiment["average_sentiment_score"] > 0.8

    # Top topics
    assert len(data["top_topics"]) == 3
    topics = {t["topic"]: t["count"] for t in data["top_topics"]}
    assert topics["Python"] == 1
    assert topics["Docker"] == 1
    assert topics["Audio Quality"] == 1

    # Actionable & Question metrics
    assert data["actionable_count"] == 2
    assert data["actionable_percentage"] == 66.67
    assert data["question_count"] == 1
    assert data["question_percentage"] == 33.33


# ---------------------------------------------------------------------------
# TEST: Edge cases (Missing API Key 503, 404 Video)
# ---------------------------------------------------------------------------
def test_api_missing_api_key_error(client, seed_data):
    video = seed_data["video"]

    with patch.object(
        comment_intelligence_service,
        "analyze_video_comments",
        side_effect=CommentIntelligenceConfigError("OPENAI_API_KEY is not configured"),
    ):
        res = client.post(f"/api/v1/videos/{video.id}/comments/analyze")
        assert res.status_code == 503
        assert "OPENAI_API_KEY is not configured" in res.json()["detail"]


def test_api_video_not_found(client):
    res = client.get("/api/v1/videos/NON_EXISTENT/comments/intelligence")
    assert res.status_code == 404
