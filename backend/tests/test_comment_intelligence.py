from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import ValidationError

from app.db.base import Base
from app.models.channel import Channel
from app.models.video import Video
from app.models.comment import Comment
from app.models.comment_analysis import CommentAnalysis
from app.schemas.comment_analysis import CommentAnalysisResult
from app.services.comment_intelligence import (
    CommentIntelligenceService,
    CommentIntelligenceConfigError,
)


@pytest.fixture
def db_session():
    """
    Creates an isolated in-memory SQLite database session for tests.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        # Seed dummy channel and video
        channel = Channel(
            channel_id="UC_TEST_123",
            title="Tech Channel",
            custom_url="@techchannel",
        )
        session.add(channel)
        session.commit()
        session.refresh(channel)

        video = Video(
            channel_id=channel.id,
            video_id="VID_TEST_123",
            title="FastAPI Tutorial",
        )
        session.add(video)
        session.commit()
        session.refresh(video)

        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def create_mock_completion(parsed_result: CommentAnalysisResult):
    """
    Builds a mock OpenAI chat completion object with parsed structured output.
    """
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
# TEST 1: Valid AI Response
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_valid_ai_response():
    """
    Verifies that a valid LLM response is properly parsed into CommentAnalysisResult.
    """
    expected_result = CommentAnalysisResult(
        sentiment="positive",
        sentiment_score=0.95,
        intent="content_request",
        topic="FastAPI",
        is_question=True,
        is_actionable=True,
    )

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=create_mock_completion(expected_result)
    )

    service = CommentIntelligenceService(api_key="sk-test-fake-key", client=mock_client)
    result = await service.analyze_comment_text("Can you please make a video about FastAPI?")

    assert result.sentiment == "positive"
    assert result.sentiment_score == 0.95
    assert result.intent == "content_request"
    assert result.topic == "FastAPI"
    assert result.is_question is True
    assert result.is_actionable is True


# ---------------------------------------------------------------------------
# TEST 2: Invalid AI Response
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_invalid_ai_response():
    """
    Verifies that malformed AI responses fail Pydantic validation and are not accepted.
    """
    # Test sentiment_score out of range (> 1.0)
    with pytest.raises(ValidationError):
        CommentAnalysisResult(
            sentiment="positive",
            sentiment_score=1.5,  # Invalid: must be <= 1.0
            intent="praise",
            topic="Python",
            is_question=False,
            is_actionable=False,
        )

    # Test invalid sentiment category
    with pytest.raises(ValidationError):
        CommentAnalysisResult(
            sentiment="ecstatic",  # Invalid: must be positive/neutral/negative
            sentiment_score=0.9,
            intent="praise",
            topic="Python",
            is_question=False,
            is_actionable=False,
        )


# ---------------------------------------------------------------------------
# TEST 3: Empty Comment
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_empty_comment():
    """
    Verifies that empty or whitespace-only comment text raises a ValueError without calling the LLM.
    """
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock()

    service = CommentIntelligenceService(api_key="sk-test-fake-key", client=mock_client)

    with pytest.raises(ValueError, match="cannot be empty"):
        await service.analyze_comment_text("")

    with pytest.raises(ValueError, match="cannot be empty"):
        await service.analyze_comment_text("   \n\t  ")

    mock_client.beta.chat.completions.parse.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 4: Missing API Key
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_missing_api_key():
    """
    Verifies that missing API keys raise CommentIntelligenceConfigError.
    """
    with patch("app.core.config.settings.OPENAI_API_KEY", ""), \
         patch("app.core.config.settings.GROQ_API_KEY", ""), \
         patch.dict("os.environ", {"OPENAI_API_KEY": "", "GROQ_API_KEY": ""}):
        service = CommentIntelligenceService(api_key="", client=None)
        with pytest.raises(CommentIntelligenceConfigError, match="OPENAI_API_KEY is not configured"):
            service.get_client()


# ---------------------------------------------------------------------------
# TEST 5: Existing Analysis is Skipped
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_skip_already_analyzed(db_session):
    """
    Verifies that comments with an existing analysis are skipped when force_reanalyze=False.
    """
    comment = Comment(
        video_id=1,
        youtube_comment_id="yt_c_001",
        text="Great tutorial!",
        like_count=5,
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    # Add existing analysis
    existing_analysis = CommentAnalysis(
        comment_id=comment.id,
        sentiment="positive",
        sentiment_score=0.88,
        intent="praise",
        topic="Tutorial",
        is_question=False,
        is_actionable=False,
        model="gpt-4o-mini",
        analyzed_at=datetime.now(timezone.utc),
    )
    db_session.add(existing_analysis)
    db_session.commit()

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock()

    service = CommentIntelligenceService(api_key="sk-test-fake-key", client=mock_client)

    result = await service.analyze_comment(
        db=db_session,
        comment=comment,
        force_reanalyze=False,
    )

    assert result.id == existing_analysis.id
    assert result.sentiment == "positive"
    # LLM must not be called
    mock_client.beta.chat.completions.parse.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 6: force_reanalyze=True Updates Existing Analysis
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_force_reanalyze_updates_record(db_session):
    """
    Verifies that force_reanalyze=True re-calls the LLM and updates the existing record.
    """
    comment = Comment(
        video_id=1,
        youtube_comment_id="yt_c_002",
        text="Actually the audio is completely broken at 3:15",
        like_count=12,
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    # Existing outdated analysis
    existing_analysis = CommentAnalysis(
        comment_id=comment.id,
        sentiment="neutral",
        sentiment_score=0.5,
        intent="feedback",
        topic="General",
        is_question=False,
        is_actionable=False,
        model="gpt-3.5-turbo",
        analyzed_at=datetime.now(timezone.utc),
    )
    db_session.add(existing_analysis)
    db_session.commit()

    # New updated analysis result
    updated_result = CommentAnalysisResult(
        sentiment="negative",
        sentiment_score=0.92,
        intent="criticism",
        topic="Audio Quality",
        is_question=False,
        is_actionable=True,
    )

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=create_mock_completion(updated_result)
    )

    service = CommentIntelligenceService(
        api_key="sk-test-fake-key",
        model="gpt-4o-mini",
        client=mock_client,
    )

    analysis = await service.analyze_comment(
        db=db_session,
        comment=comment,
        force_reanalyze=True,
    )

    assert analysis.id == existing_analysis.id  # Same database record
    assert analysis.sentiment == "negative"
    assert analysis.sentiment_score == 0.92
    assert analysis.intent == "criticism"
    assert analysis.topic == "Audio Quality"
    assert analysis.is_actionable is True
    assert analysis.model == "gpt-4o-mini"
    mock_client.beta.chat.completions.parse.assert_called_once()


# ---------------------------------------------------------------------------
# TEST 7: Database Record is Created Correctly
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_database_record_created_correctly(db_session):
    """
    Verifies that a new CommentAnalysis row is saved to the database with all fields populated.
    """
    comment = Comment(
        video_id=1,
        youtube_comment_id="yt_c_003",
        text="Could you share the GitHub repo link for this project?",
        like_count=3,
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    ai_result = CommentAnalysisResult(
        sentiment="neutral",
        sentiment_score=0.75,
        intent="information_request",
        topic="GitHub Repo",
        is_question=True,
        is_actionable=True,
    )

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=create_mock_completion(ai_result)
    )

    service = CommentIntelligenceService(
        api_key="sk-test-fake-key",
        model="gpt-4o-mini",
        client=mock_client,
    )

    saved_analysis = await service.analyze_comment(
        db=db_session,
        comment=comment,
        force_reanalyze=False,
    )

    assert saved_analysis.id is not None
    assert saved_analysis.comment_id == comment.id
    assert saved_analysis.sentiment == "neutral"
    assert saved_analysis.sentiment_score == 0.75
    assert saved_analysis.intent == "information_request"
    assert saved_analysis.topic == "GitHub Repo"
    assert saved_analysis.is_question is True
    assert saved_analysis.is_actionable is True
    assert saved_analysis.model == "gpt-4o-mini"
    assert saved_analysis.analyzed_at is not None


# ---------------------------------------------------------------------------
# TEST 8: Batch Analysis Returns Correct Counts
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_batch_analysis_counts(db_session):
    """
    Verifies that batch analysis accurately counts total, already_analyzed, analyzed, and failed.
    """
    # Comment 1: Already analyzed
    c1 = Comment(video_id=1, youtube_comment_id="yt_b_1", text="Already done")
    # Comment 2: Valid, to be analyzed
    c2 = Comment(video_id=1, youtube_comment_id="yt_b_2", text="Love this content!")
    # Comment 3: Valid, to be analyzed
    c3 = Comment(video_id=1, youtube_comment_id="yt_b_3", text="Where can I find docs?")
    # Comment 4: Empty text -> will fail
    c4 = Comment(video_id=1, youtube_comment_id="yt_b_4", text="   ")

    db_session.add_all([c1, c2, c3, c4])
    db_session.commit()
    for c in [c1, c2, c3, c4]:
        db_session.refresh(c)

    # Mark c1 as already analyzed
    a1 = CommentAnalysis(
        comment_id=c1.id,
        sentiment="neutral",
        sentiment_score=0.5,
        intent="other",
        topic="General",
        is_question=False,
        is_actionable=False,
    )
    db_session.add(a1)
    db_session.commit()

    # Mock response for c2 and c3
    mock_ai_result = CommentAnalysisResult(
        sentiment="positive",
        sentiment_score=0.9,
        intent="praise",
        topic="Content",
        is_question=False,
        is_actionable=False,
    )
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=create_mock_completion(mock_ai_result)
    )

    service = CommentIntelligenceService(
        api_key="sk-test-fake-key",
        client=mock_client,
    )

    result = await service.analyze_comments(
        db=db_session,
        comments=[c1, c2, c3, c4],
        force_reanalyze=False,
        batch_size=2,
    )

    assert result.total_comments == 4
    assert result.already_analyzed == 1
    assert result.analyzed == 2
    assert result.failed == 1


# ---------------------------------------------------------------------------
# TEST 9: Groq Client Initialization & Provider Resolution
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_groq_client_initialization():
    """
    Verifies that setting GROQ_API_KEY configures client with Groq base_url and model.
    """
    with patch("app.core.config.settings.GROQ_API_KEY", "gsk_test_groq_key_123"), \
         patch("app.core.config.settings.OPENAI_API_KEY", ""), \
         patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test_groq_key_123", "OPENAI_API_KEY": ""}):
        service = CommentIntelligenceService(client=None)
        client = service.get_client()
        assert str(client.base_url).rstrip("/") == "https://api.groq.com/openai/v1"
        assert service.model == "openai/gpt-oss-120b"


# ---------------------------------------------------------------------------
# TEST 10: Fallback to JSON Object Chat Completion
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_fallback_to_json_object():
    """
    Verifies that if beta.chat.completions.parse fails, fallback to chat.completions.create succeeds.
    """
    mock_client = MagicMock()
    # Beta parse raises error (e.g. model does not support beta parse)
    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=Exception("json_schema not supported for this model")
    )
    # chat.completions.create succeeds with raw JSON string (potentially inside markdown fences)
    mock_create_msg = MagicMock()
    mock_create_msg.content = '```json\n{"sentiment": "positive", "sentiment_score": 0.95, "intent": "praise", "topic": "AI", "is_question": false, "is_actionable": false}\n```'
    mock_create_choice = MagicMock()
    mock_create_choice.message = mock_create_msg
    mock_create_completion = MagicMock()
    mock_create_completion.choices = [mock_create_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_create_completion)

    service = CommentIntelligenceService(
        api_key="gsk_test_key",
        client=mock_client,
    )

    result = await service.analyze_comment_text("Incredible video!")
    assert result.sentiment == "positive"
    assert result.intent == "praise"
    assert result.sentiment_score == 0.95
    assert result.topic == "AI"
    mock_client.chat.completions.create.assert_called_once()

