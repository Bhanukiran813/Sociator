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
    compute_sentiment_label,
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


# ===========================================================================
# DEDICATED EDGE CASE SUITE (10 REQUIREMENTS)
# ===========================================================================

# ---------------------------------------------------------------------------
# EDGE CASE 1: 100% Positive Comments
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_edge_case_100_percent_positive(db_session):
    """
    Verifies that when all comments are positive, the label is 'Mostly Positive'
    and positive percentage is 100.0%.
    """
    video = Video(channel_id=1, video_id="VID_100_POS", title="Positive Video")
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    for i in range(4):
        c = Comment(video_id=video.id, youtube_comment_id=f"pos_{i}", text=f"Awesome video {i}!")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        a = CommentAnalysis(
            comment_id=c.id,
            sentiment="positive",
            sentiment_score=0.9,
            intent="praise",
            topic="Tutorial",
            is_question=False,
            is_actionable=False,
        )
        db_session.add(a)
    db_session.commit()

    service = CommentIntelligenceService(api_key="sk-test-fake")
    summary = service.get_video_comment_intelligence(db_session, video.id)

    assert summary.analyzed_comments == 4
    assert summary.sentiment.positive == 4
    assert summary.sentiment.neutral == 0
    assert summary.sentiment.negative == 0
    assert summary.sentiment.positive_percentage == 100.0
    assert summary.sentiment.neutral_percentage == 0.0
    assert summary.sentiment.negative_percentage == 0.0
    assert summary.sentiment.label == "Mostly Positive"


# ---------------------------------------------------------------------------
# EDGE CASE 2: 100% Neutral Comments
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_edge_case_100_percent_neutral(db_session):
    """
    Verifies that when all comments are neutral, the label is 'Mostly Neutral'
    and neutral percentage is 100.0%.
    """
    video = Video(channel_id=1, video_id="VID_100_NEU", title="Neutral Video")
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    for i in range(3):
        c = Comment(video_id=video.id, youtube_comment_id=f"neu_{i}", text=f"Timestamp at 0{i}:00")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        a = CommentAnalysis(
            comment_id=c.id,
            sentiment="neutral",
            sentiment_score=0.5,
            intent="other",
            topic="Timestamps",
            is_question=False,
            is_actionable=False,
        )
        db_session.add(a)
    db_session.commit()

    service = CommentIntelligenceService(api_key="sk-test-fake")
    summary = service.get_video_comment_intelligence(db_session, video.id)

    assert summary.analyzed_comments == 3
    assert summary.sentiment.positive == 0
    assert summary.sentiment.neutral == 3
    assert summary.sentiment.negative == 0
    assert summary.sentiment.positive_percentage == 0.0
    assert summary.sentiment.neutral_percentage == 100.0
    assert summary.sentiment.negative_percentage == 0.0
    assert summary.sentiment.label == "Mostly Neutral"


# ---------------------------------------------------------------------------
# EDGE CASE 3: 100% Negative Comments
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_edge_case_100_percent_negative(db_session):
    """
    Verifies that when all comments are negative, the label is 'Mostly Negative'
    and negative percentage is 100.0%.
    """
    video = Video(channel_id=1, video_id="VID_100_NEG", title="Negative Video")
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    for i in range(3):
        c = Comment(video_id=video.id, youtube_comment_id=f"neg_{i}", text=f"Broken audio {i}")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        a = CommentAnalysis(
            comment_id=c.id,
            sentiment="negative",
            sentiment_score=0.85,
            intent="criticism",
            topic="Audio Quality",
            is_question=False,
            is_actionable=True,
        )
        db_session.add(a)
    db_session.commit()

    service = CommentIntelligenceService(api_key="sk-test-fake")
    summary = service.get_video_comment_intelligence(db_session, video.id)

    assert summary.analyzed_comments == 3
    assert summary.sentiment.positive == 0
    assert summary.sentiment.neutral == 0
    assert summary.sentiment.negative == 3
    assert summary.sentiment.negative_percentage == 100.0
    assert summary.sentiment.label == "Mostly Negative"


# ---------------------------------------------------------------------------
# EDGE CASE 4: Mixed Positive / Neutral Comments
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_edge_case_mixed_positive_neutral(db_session):
    """
    Tests both evenly split positive/neutral ('Mixed') and positive-dominant positive/neutral ('Mostly Positive').
    """
    # Case 4A: 50% Positive, 50% Neutral -> neither satisfies >= 60% positive nor pure neutral -> "Mixed"
    label_even = compute_sentiment_label(50.0, 50.0, 0.0, analyzed_comments=10)
    assert label_even == "Mixed"

    # Case 4B: 70% Positive, 30% Neutral -> >= 60% positive, < 20% negative -> "Mostly Positive"
    label_pos_dom = compute_sentiment_label(70.0, 30.0, 0.0, analyzed_comments=10)
    assert label_pos_dom == "Mostly Positive"


# ---------------------------------------------------------------------------
# EDGE CASE 5: Mixed Positive / Negative Comments
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_edge_case_mixed_positive_negative(db_session):
    """
    Tests mixed distributions involving both positive and negative comments.
    """
    # 50% positive, 30% negative, 20% neutral -> negative < 40 and not > positive; positive < 60 -> "Mixed"
    label_mixed = compute_sentiment_label(50.0, 20.0, 30.0, analyzed_comments=10)
    assert label_mixed == "Mixed"

    # 45% negative, 45% positive, 10% neutral -> negative >= 40% -> "Mostly Negative"
    label_high_neg = compute_sentiment_label(45.0, 10.0, 45.0, analyzed_comments=10)
    assert label_high_neg == "Mostly Negative"


# ---------------------------------------------------------------------------
# EDGE CASE 6: Zero Analyzed Comments
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_edge_case_zero_analyzed_comments(db_session):
    """
    Verifies that a video with zero analyzed comments returns safe zero metrics and 'No Data' label.
    """
    video = Video(channel_id=1, video_id="VID_ZERO", title="Unanalyzed Video")
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    service = CommentIntelligenceService(api_key="sk-test-fake")
    summary = service.get_video_comment_intelligence(db_session, video.id)

    assert summary.video_id == video.id
    assert summary.total_comments == 0
    assert summary.analyzed_comments == 0
    assert summary.coverage_percentage == 0.0
    assert summary.sentiment.label == "No Data"
    assert summary.sentiment.positive == 0
    assert summary.sentiment.neutral == 0
    assert summary.sentiment.negative == 0
    assert summary.sentiment.average_sentiment_score == 0.0
    assert summary.top_topics == []
    assert summary.top_intents == []
    assert summary.actionable_count == 0
    assert summary.question_count == 0


# ---------------------------------------------------------------------------
# EDGE CASE 7: Partially Analyzed Comments
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_edge_case_partially_analyzed_comments(db_session):
    """
    Verifies that coverage is calculated accurately when only some comments have been analyzed.
    Total = 10, Analyzed = 4 -> coverage = 40.0%.
    """
    video = Video(channel_id=1, video_id="VID_PARTIAL", title="Partial Video")
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    # 10 comments in total
    comments = []
    for i in range(10):
        c = Comment(video_id=video.id, youtube_comment_id=f"part_{i}", text=f"Comment {i}")
        comments.append(c)
    db_session.add_all(comments)
    db_session.commit()
    for c in comments:
        db_session.refresh(c)

    # Analyze only the first 4 (3 positive, 1 neutral)
    for i in range(4):
        a = CommentAnalysis(
            comment_id=comments[i].id,
            sentiment="positive" if i < 3 else "neutral",
            sentiment_score=0.8,
            intent="praise" if i < 3 else "other",
            topic="Coding",
            is_question=False,
            is_actionable=False,
        )
        db_session.add(a)
    db_session.commit()

    service = CommentIntelligenceService(api_key="sk-test-fake")
    summary = service.get_video_comment_intelligence(db_session, video.id)

    assert summary.total_comments == 10
    assert summary.analyzed_comments == 4
    assert summary.coverage_percentage == 40.0
    # Positive percentage among analyzed: 3/4 = 75.0%
    assert summary.sentiment.positive == 3
    assert summary.sentiment.positive_percentage == 75.0
    assert summary.sentiment.neutral == 1
    assert summary.sentiment.neutral_percentage == 25.0
    assert summary.sentiment.negative == 0
    assert summary.sentiment.negative_percentage == 0.0
    assert summary.sentiment.label == "Mostly Positive"


# ---------------------------------------------------------------------------
# EDGE CASE 8: Sentiment Score Boundaries (0.0 and 1.0)
# ---------------------------------------------------------------------------
def test_edge_case_sentiment_score_boundaries():
    """
    Verifies that boundary values 0.0 and 1.0 are valid, while values < 0.0 or > 1.0 are rejected.
    """
    # 0.0 is valid
    res_min = CommentAnalysisResult(
        sentiment="neutral",
        sentiment_score=0.0,
        intent="other",
        topic="General",
        is_question=False,
        is_actionable=False,
    )
    assert res_min.sentiment_score == 0.0

    # 1.0 is valid
    res_max = CommentAnalysisResult(
        sentiment="positive",
        sentiment_score=1.0,
        intent="praise",
        topic="General",
        is_question=False,
        is_actionable=False,
    )
    assert res_max.sentiment_score == 1.0

    # Below 0.0 is invalid
    with pytest.raises(ValidationError):
        CommentAnalysisResult(
            sentiment="negative",
            sentiment_score=-0.01,
            intent="criticism",
            topic="General",
            is_question=False,
            is_actionable=False,
        )

    # Above 1.0 is invalid
    with pytest.raises(ValidationError):
        CommentAnalysisResult(
            sentiment="positive",
            sentiment_score=1.01,
            intent="praise",
            topic="General",
            is_question=False,
            is_actionable=False,
        )


# ---------------------------------------------------------------------------
# EDGE CASE 9: Invalid & Normalized Sentiment Values
# ---------------------------------------------------------------------------
def test_edge_case_invalid_sentiment_values():
    """
    Verifies normalization of valid sentiment variants and rejection of invalid values.
    """
    # Case-insensitive whitespace normalization
    res_upper = CommentAnalysisResult(
        sentiment="  POSITIVE \n",
        sentiment_score=0.9,
        intent="praise",
        topic="General",
        is_question=False,
        is_actionable=False,
    )
    assert res_upper.sentiment == "positive"

    res_neu = CommentAnalysisResult(
        sentiment="Neutral",
        sentiment_score=0.5,
        intent="other",
        topic="General",
        is_question=False,
        is_actionable=False,
    )
    assert res_neu.sentiment == "neutral"

    # Completely invalid sentiment strings
    invalid_sentiments = ["excited", "angry", "terrible", "good", "", "123"]
    for inv in invalid_sentiments:
        with pytest.raises(ValidationError):
            CommentAnalysisResult(
                sentiment=inv,
                sentiment_score=0.5,
                intent="other",
                topic="General",
                is_question=False,
                is_actionable=False,
            )


# ---------------------------------------------------------------------------
# EDGE CASE 10: Re-analysis Flow
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_edge_case_reanalysis_flow(db_session):
    """
    Verifies that re-analysis with force_reanalyze=True updates the existing record
    without creating duplicate records.
    """
    comment = Comment(
        video_id=1,
        youtube_comment_id="yt_reanalyze_test",
        text="Initially neutral comment",
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    # Initial analysis
    initial_analysis = CommentAnalysis(
        comment_id=comment.id,
        sentiment="neutral",
        sentiment_score=0.5,
        intent="other",
        topic="General",
        is_question=False,
        is_actionable=False,
        model="groq-test",
    )
    db_session.add(initial_analysis)
    db_session.commit()
    db_session.refresh(initial_analysis)

    initial_id = initial_analysis.id

    # Mock new analysis for re-run
    new_result = CommentAnalysisResult(
        sentiment="positive",
        sentiment_score=0.95,
        intent="praise",
        topic="Architecture",
        is_question=False,
        is_actionable=False,
    )
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=create_mock_completion(new_result)
    )

    service = CommentIntelligenceService(api_key="sk-test-fake", client=mock_client)

    # Re-analyze with force_reanalyze=True
    updated = await service.analyze_comment(
        db=db_session,
        comment=comment,
        force_reanalyze=True,
    )

    assert updated.id == initial_id  # Same primary key
    assert updated.sentiment == "positive"
    assert updated.sentiment_score == 0.95
    assert updated.intent == "praise"
    assert updated.topic == "Architecture"

    # Confirm only 1 CommentAnalysis record exists in the table for this comment
    all_analyses = db_session.query(CommentAnalysis).filter_by(comment_id=comment.id).all()
    assert len(all_analyses) == 1
    mock_client.beta.chat.completions.parse.assert_called_once()


