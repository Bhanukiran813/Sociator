import asyncio
from datetime import datetime, timezone
import logging
from typing import List, Optional
from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.comment import Comment
from app.models.comment_analysis import CommentAnalysis
from app.schemas.comment_analysis import (
    BatchAnalysisResult,
    CommentAnalysisResult,
    CommentIntelligenceSummaryResponse,
    IntentBreakdown,
    SentimentDistribution,
    TopicBreakdown,
)


logger = logging.getLogger("sociator.comment_intelligence")


class CommentIntelligenceError(Exception):
    """Base exception for Comment Intelligence service."""
    pass


class CommentIntelligenceConfigError(CommentIntelligenceError):
    """Raised when required configuration (such as GROQ_API_KEY or OPENAI_API_KEY) is missing."""
    pass


def compute_sentiment_label(
    positive_percentage: float,
    neutral_percentage: float,
    negative_percentage: float,
    analyzed_comments: int = 1,
) -> str:
    """
    Computes a transparent, data-driven sentiment label based on the underlying distribution:
    - "No Data": when analyzed_comments == 0
    - "Mostly Positive": positive_percentage >= 60.0 and negative_percentage < 20.0
    - "Mostly Negative": negative_percentage >= 40.0 or (negative_percentage >= 30.0 and negative_percentage > positive_percentage)
    - "Mostly Neutral": neutral_percentage >= 50.0 and positive_percentage < 40.0 and negative_percentage < 20.0
    - "Mixed": Any other distribution where sentiment is contested or no single category dominates
    """
    if analyzed_comments == 0:
        return "No Data"
    if positive_percentage >= 60.0 and negative_percentage < 20.0:
        return "Mostly Positive"
    if negative_percentage >= 40.0 or (negative_percentage >= 30.0 and negative_percentage > positive_percentage):
        return "Mostly Negative"
    if neutral_percentage >= 50.0 and positive_percentage < 40.0 and negative_percentage < 20.0:
        return "Mostly Neutral"
    return "Mixed"


COMMENT_INTELLIGENCE_SYSTEM_PROMPT = """You are an expert AI comment analyst for YouTube content creators.
Your task is to analyze viewer comments with extreme precision and output structured classification data.

Analyze the given comment across these dimensions:
1. Sentiment:
   - "positive": Expresses appreciation, enthusiasm, happiness, or agreement.
   - "neutral": Neutral statements, observations, timestamps, or balanced remarks.
   - "negative": Expresses frustration, dissatisfaction, disagreement, or harsh critique.
   Provide a normalized sentiment_score between 0.0 and 1.0 reflecting sentiment intensity (0.0 = minimal/weak sentiment, 1.0 = strong/intense sentiment).

2. Intent:
   Select exactly one primary intent category:
   - "praise": Compliments, gratitude, expressing admiration for the video or creator.
   - "criticism": Negative feedback, complaints, expressing disappointment.
   - "question": Direct inquiries asking for clarification, help, or information.
   - "content_request": Asking for a specific future video topic, tutorial, or follow-up.
   - "suggestion": Constructive recommendation on video editing, tools, format, or process.
   - "feedback": General feedback or impressions about the content.
   - "information_request": Asking for links, timestamps, resources, or references.
   - "spam": Self-promotion, bot links, irrelevant gibberish, copy-paste ads.
   - "promotion": Promotional content or channel advertising.
   - "personal_experience": Viewer sharing their own story or experience related to the video.
   - "other": Anything not fitting the categories above.

3. Topic:
   A concise, specific topic label (1-3 words, max 100 characters) describing the subject matter of the comment (e.g., "Python", "FastAPI", "Audio Quality", "Pacing", "Thumbnail").

4. is_question:
   true if the comment asks a question; otherwise false.

5. is_actionable:
   true if the creator could reasonably take concrete action based on this comment (e.g., reply to answer a question, fix an issue mentioned in the video, make a requested video, adopt a suggestion); false if it is purely passive commentary (e.g., "nice video!").

Do not include any introductory remarks, explanations, or commentary. Only return the required structured output schema."""


class CommentIntelligenceService:
    """
    Dedicated service responsible for analyzing YouTube comments using AI LLMs (Groq or OpenAI).
    Enforces structured output, Pydantic validation, idempotent upserting,
    re-analysis guard, and fault-tolerant batch processing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[AsyncOpenAI] = None,
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._client = client
        self._provider: Optional[str] = None

    def get_client(self) -> AsyncOpenAI:
        """
        Lazily creates or returns the AsyncOpenAI client configured for Groq or OpenAI.
        Dynamically reads from settings, os.environ, or .env file to support
        runtime key updates without requiring a full server restart.
        Raises CommentIntelligenceConfigError if neither GROQ_API_KEY nor OPENAI_API_KEY is configured.
        """
        if self._client is not None:
            return self._client

        import os
        from pathlib import Path
        from dotenv import load_dotenv

        # 1. If explicit api_key was provided to constructor, respect it
        if self._api_key is not None:
            api_key = self._api_key.strip()
            if not api_key:
                raise CommentIntelligenceConfigError(
                    "GROQ_API_KEY or OPENAI_API_KEY is not configured. Set GROQ_API_KEY in backend/.env."
                )
            base_url = self._base_url
            if not base_url and api_key.startswith("gsk_"):
                base_url = settings.GROQ_BASE_URL
                self._provider = "groq"
            self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)
            return self._client

        # 2. Check provider preference or auto-detect
        provider_pref = (os.getenv("LLM_PROVIDER") or settings.LLM_PROVIDER or "auto").lower()
        groq_key = (os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY or "").strip()
        openai_key = (os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY or "").strip()

        # Reload .env only if both keys are completely missing from environment and settings
        if not groq_key and not openai_key:
            env_file = Path(__file__).resolve().parent.parent.parent / ".env"
            if env_file.exists():
                load_dotenv(dotenv_path=env_file, override=True)
                groq_key = (os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY or "").strip()
                openai_key = (os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY or "").strip()

        chosen_key: Optional[str] = None
        base_url: Optional[str] = None

        if provider_pref == "groq" and groq_key:
            chosen_key = groq_key
            base_url = os.getenv("GROQ_BASE_URL") or settings.GROQ_BASE_URL
            self._provider = "groq"
        elif provider_pref == "openai" and openai_key:
            chosen_key = openai_key
            base_url = os.getenv("OPENAI_BASE_URL") or settings.OPENAI_BASE_URL
            self._provider = "openai"
        elif groq_key:
            # Groq is prioritized as free alternative when present
            chosen_key = groq_key
            base_url = os.getenv("GROQ_BASE_URL") or settings.GROQ_BASE_URL
            self._provider = "groq"
        elif openai_key:
            chosen_key = openai_key
            base_url = os.getenv("OPENAI_BASE_URL") or settings.OPENAI_BASE_URL
            self._provider = "openai"

        if not chosen_key:
            logger.error("Comment analysis failed: Neither Groq nor OpenAI API key is configured.")
            raise CommentIntelligenceConfigError(
                "GROQ_API_KEY or OPENAI_API_KEY is not configured. Set GROQ_API_KEY in backend/.env."
            )

        self._client = AsyncOpenAI(api_key=chosen_key, base_url=base_url, timeout=30.0, max_retries=2)
        return self._client

    @property
    def model(self) -> str:
        if self._model:
            return self._model
        if self._provider == "groq":
            return settings.GROQ_MODEL or "openai/gpt-oss-120b"
        elif self._provider == "openai":
            return settings.OPENAI_MODEL or "gpt-4o-mini"
        # If not resolved yet, check settings
        if settings.GROQ_API_KEY:
            return settings.GROQ_MODEL or "openai/gpt-oss-120b"
        return settings.OPENAI_MODEL or "gpt-4o-mini"

    async def analyze_comment_text(self, text: str) -> CommentAnalysisResult:
        """
        Calls AI API with structured output enforcement and validates the response schema.
        Supports both OpenAI and Groq models with robust JSON fallbacks.
        Raises ValueError if comment text is empty.
        Raises CommentIntelligenceConfigError if API key is missing.
        """
        if not text or not text.strip():
            raise ValueError("Comment text cannot be empty or whitespace")

        client = self.get_client()

        try:
            try:
                # Attempt structured parse endpoint first
                completion = await client.beta.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": COMMENT_INTELLIGENCE_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Comment text:\n{text.strip()}"},
                    ],
                    response_format=CommentAnalysisResult,
                )

                choice = completion.choices[0]
                message = choice.message

                if getattr(message, "refusal", None):
                    raise ValueError(f"Model refused to analyze comment: {message.refusal}")

                if message.parsed is not None:
                    return message.parsed
                elif message.content:
                    return CommentAnalysisResult.model_validate_json(message.content)
                else:
                    raise ValueError("Received empty response from AI model")

            except Exception as parse_err:
                if isinstance(parse_err, (ValueError, CommentIntelligenceConfigError)):
                    raise
                # Fallback to standard chat completion with json_object mode (universal for Groq/OpenAI)
                logger.info("Beta parse fallback triggered: %s. Using json_object mode.", parse_err)
                completion = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                f"{COMMENT_INTELLIGENCE_SYSTEM_PROMPT}\n\n"
                                "You must return a raw JSON object with keys: "
                                '"sentiment", "sentiment_score", "intent", "topic", "is_question", "is_actionable".'
                            ),
                        },
                        {"role": "user", "content": f"Comment text:\n{text.strip()}"},
                    ],
                    response_format={"type": "json_object"},
                )

                choice = completion.choices[0]
                message = choice.message
                raw_content = message.content or ""
                cleaned_content = raw_content.strip()
                if cleaned_content.startswith("```json"):
                    cleaned_content = cleaned_content[7:]
                elif cleaned_content.startswith("```"):
                    cleaned_content = cleaned_content[3:]
                if cleaned_content.endswith("```"):
                    cleaned_content = cleaned_content[:-3]
                cleaned_content = cleaned_content.strip()

                if not cleaned_content:
                    raise ValueError("Received empty response from AI model")

                return CommentAnalysisResult.model_validate_json(cleaned_content)

        except CommentIntelligenceConfigError:
            raise
        except Exception as exc:
            # Log error without leaking sensitive credentials
            logger.error("LLM analysis request failed: %s", str(exc))
            raise

    def save_or_update_analysis(
        self,
        db: Session,
        comment_id: int,
        result: CommentAnalysisResult,
        model_name: Optional[str] = None,
    ) -> CommentAnalysis:
        """
        Upserts a CommentAnalysis database record for the given comment_id.
        Avoids creating duplicate analysis records for the same comment.
        """
        stmt = select(CommentAnalysis).where(CommentAnalysis.comment_id == comment_id)
        analysis = db.scalars(stmt).first()

        now = datetime.now(timezone.utc)
        used_model = model_name or self.model

        if analysis:
            analysis.sentiment = result.sentiment
            analysis.sentiment_score = result.sentiment_score
            analysis.intent = result.intent
            analysis.topic = result.topic
            analysis.is_question = result.is_question
            analysis.is_actionable = result.is_actionable
            analysis.model = used_model
            analysis.analyzed_at = now
        else:
            analysis = CommentAnalysis(
                comment_id=comment_id,
                sentiment=result.sentiment,
                sentiment_score=result.sentiment_score,
                intent=result.intent,
                topic=result.topic,
                is_question=result.is_question,
                is_actionable=result.is_actionable,
                model=used_model,
                analyzed_at=now,
            )
            db.add(analysis)

        db.commit()
        db.refresh(analysis)
        return analysis

    async def analyze_comment(
        self,
        db: Session,
        comment: Comment,
        force_reanalyze: bool = False,
    ) -> Optional[CommentAnalysis]:
        """
        Analyzes a single stored YouTube comment and persists the result.
        If the comment is already analyzed and force_reanalyze is False, skips LLM analysis.
        """
        # Guard: Check existing analysis
        if not force_reanalyze:
            stmt = select(CommentAnalysis).where(CommentAnalysis.comment_id == comment.id)
            existing = db.scalars(stmt).first()
            if existing is not None:
                return existing

        if not comment.text or not comment.text.strip():
            logger.warning("Comment analysis failed comment_id=%s reason=Empty or whitespace text", comment.id)
            raise ValueError(f"Comment {comment.id} text is empty or whitespace")

        try:
            analysis_result = await self.analyze_comment_text(comment.text)
            return self.save_or_update_analysis(
                db=db,
                comment_id=comment.id,
                result=analysis_result,
                model_name=self.model,
            )
        except Exception as exc:
            logger.error("Comment analysis failed comment_id=%s reason=%s", comment.id, str(exc))
            raise

    async def analyze_comments(
        self,
        db: Session,
        comments: List[Comment],
        force_reanalyze: bool = False,
        batch_size: Optional[int] = None,
    ) -> BatchAnalysisResult:
        """
        Batch analyzes a list of stored comments.
        - Identifies comments requiring analysis
        - Skips already analyzed comments unless forced
        - Processes comments safely in batches
        - Isolates individual failures without corrupting the batch
        - Returns summary execution statistics
        """
        total_comments = len(comments)
        if total_comments == 0:
            return BatchAnalysisResult(
                total_comments=0,
                already_analyzed=0,
                analyzed=0,
                failed=0,
            )

        # Check existing analysis records in bulk
        comment_ids = [c.id for c in comments]
        stmt = select(CommentAnalysis.comment_id).where(CommentAnalysis.comment_id.in_(comment_ids))
        existing_analyzed_ids = set(db.scalars(stmt).all())

        comments_to_process: List[Comment] = []
        already_analyzed_count = 0

        for comment in comments:
            if comment.id in existing_analyzed_ids and not force_reanalyze:
                already_analyzed_count += 1
            else:
                comments_to_process.append(comment)

        chunk_size = batch_size or settings.COMMENT_ANALYSIS_BATCH_SIZE or 20
        analyzed_count = 0
        failed_count = 0
        last_error_message = None

        # Process in chunks
        stop_processing = False
        for i in range(0, len(comments_to_process), chunk_size):
            if stop_processing:
                break
            chunk = comments_to_process[i : i + chunk_size]
            for comment in chunk:
                try:
                    if not comment.text or not comment.text.strip():
                        logger.warning(
                            "Comment analysis failed comment_id=%s reason=Empty or whitespace text",
                            comment.id,
                        )
                        failed_count += 1
                        continue

                    analysis_result = await self.analyze_comment_text(comment.text)
                    self.save_or_update_analysis(
                        db=db,
                        comment_id=comment.id,
                        result=analysis_result,
                        model_name=self.model,
                    )
                    analyzed_count += 1
                    await asyncio.sleep(0.15)
                except Exception as exc:
                    db.rollback()
                    err_str = str(exc)
                    logger.error(
                        "Comment analysis failed comment_id=%s reason=%s",
                        comment.id,
                        err_str,
                    )
                    failed_count += 1
                    last_error_message = err_str

                    # Detect account-level errors (quota exhausted, invalid key)
                    lower_err = err_str.lower()
                    if (
                        "insufficient_quota" in lower_err
                        or "credit_balance_exhausted" in lower_err
                        or "invalid_api_key" in lower_err
                        or "authentication" in lower_err
                    ):
                        remaining = len(comments_to_process) - (analyzed_count + failed_count)
                        failed_count += max(0, remaining)
                        stop_processing = True
                        break

        return BatchAnalysisResult(
            total_comments=total_comments,
            already_analyzed=already_analyzed_count,
            analyzed=analyzed_count,
            failed=failed_count,
            error_message=last_error_message,
        )

    async def analyze_video_comments(
        self,
        db: Session,
        video_id: int,
        force_reanalyze: bool = False,
        limit: Optional[int] = None,
    ) -> BatchAnalysisResult:
        """
        Fetches stored comments for a video and batch analyzes them.
        """
        stmt = (
            select(Comment)
            .where(Comment.video_id == video_id)
            .order_by(Comment.published_at.desc().nulls_last(), Comment.id.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        comments = list(db.scalars(stmt).all())
        return await self.analyze_comments(
            db=db,
            comments=comments,
            force_reanalyze=force_reanalyze,
        )

    def get_video_comment_intelligence(
        self,
        db: Session,
        video_id: int,
    ) -> CommentIntelligenceSummaryResponse:
        """
        Computes aggregate metrics, sentiment breakdown, top topics,
        and top intents for all analyzed comments of a video.
        """
        total_comments = db.scalar(
            select(func.count(Comment.id)).where(Comment.video_id == video_id)
        ) or 0

        analyzed_comments = db.scalar(
            select(func.count(CommentAnalysis.id))
            .join(Comment, Comment.id == CommentAnalysis.comment_id)
            .where(Comment.video_id == video_id)
        ) or 0

        coverage_percentage = (
            round((analyzed_comments / total_comments) * 100.0, 2)
            if total_comments > 0
            else 0.0
        )

        if analyzed_comments == 0:
            return CommentIntelligenceSummaryResponse(
                video_id=video_id,
                total_comments=total_comments,
                analyzed_comments=0,
                coverage_percentage=0.0,
                sentiment=SentimentDistribution(label="No Data"),
                top_topics=[],
                top_intents=[],
                actionable_count=0,
                actionable_percentage=0.0,
                question_count=0,
                question_percentage=0.0,
            )

        # 1. Sentiment counts & average score
        sentiment_stmt = (
            select(CommentAnalysis.sentiment, func.count(CommentAnalysis.id))
            .join(Comment, Comment.id == CommentAnalysis.comment_id)
            .where(Comment.video_id == video_id)
            .group_by(CommentAnalysis.sentiment)
        )
        sentiment_counts = {row[0]: row[1] for row in db.execute(sentiment_stmt).all()}

        pos_count = sentiment_counts.get("positive", 0)
        neu_count = sentiment_counts.get("neutral", 0)
        neg_count = sentiment_counts.get("negative", 0)

        pos_pct = round((pos_count / analyzed_comments) * 100.0, 2)
        neu_pct = round((neu_count / analyzed_comments) * 100.0, 2)
        neg_pct = round((neg_count / analyzed_comments) * 100.0, 2)

        avg_score = db.scalar(
            select(func.avg(CommentAnalysis.sentiment_score))
            .join(Comment, Comment.id == CommentAnalysis.comment_id)
            .where(Comment.video_id == video_id)
        ) or 0.0

        label = compute_sentiment_label(pos_pct, neu_pct, neg_pct, analyzed_comments)

        sentiment_dist = SentimentDistribution(
            positive=pos_count,
            neutral=neu_count,
            negative=neg_count,
            positive_percentage=pos_pct,
            neutral_percentage=neu_pct,
            negative_percentage=neg_pct,
            average_sentiment_score=round(float(avg_score), 3),
            label=label,
        )

        # 2. Top topics
        topic_stmt = (
            select(CommentAnalysis.topic, func.count(CommentAnalysis.id))
            .join(Comment, Comment.id == CommentAnalysis.comment_id)
            .where(
                Comment.video_id == video_id,
                CommentAnalysis.topic.is_not(None),
                CommentAnalysis.topic != "",
            )
            .group_by(CommentAnalysis.topic)
            .order_by(func.count(CommentAnalysis.id).desc())
            .limit(10)
        )
        top_topics = [
            TopicBreakdown(
                topic=row[0],
                count=row[1],
                percentage=round((row[1] / analyzed_comments) * 100.0, 2),
            )
            for row in db.execute(topic_stmt).all()
        ]

        # 3. Top intents
        intent_stmt = (
            select(CommentAnalysis.intent, func.count(CommentAnalysis.id))
            .join(Comment, Comment.id == CommentAnalysis.comment_id)
            .where(
                Comment.video_id == video_id,
                CommentAnalysis.intent.is_not(None),
                CommentAnalysis.intent != "",
            )
            .group_by(CommentAnalysis.intent)
            .order_by(func.count(CommentAnalysis.id).desc())
            .limit(10)
        )
        top_intents = [
            IntentBreakdown(
                intent=row[0],
                count=row[1],
                percentage=round((row[1] / analyzed_comments) * 100.0, 2),
            )
            for row in db.execute(intent_stmt).all()
        ]

        # 4. Actionable and Question counts
        actionable_count = db.scalar(
            select(func.count(CommentAnalysis.id))
            .join(Comment, Comment.id == CommentAnalysis.comment_id)
            .where(Comment.video_id == video_id, CommentAnalysis.is_actionable == True)
        ) or 0

        question_count = db.scalar(
            select(func.count(CommentAnalysis.id))
            .join(Comment, Comment.id == CommentAnalysis.comment_id)
            .where(Comment.video_id == video_id, CommentAnalysis.is_question == True)
        ) or 0

        return CommentIntelligenceSummaryResponse(
            video_id=video_id,
            total_comments=total_comments,
            analyzed_comments=analyzed_comments,
            coverage_percentage=coverage_percentage,
            sentiment=sentiment_dist,
            top_topics=top_topics,
            top_intents=top_intents,
            actionable_count=actionable_count,
            actionable_percentage=round((actionable_count / analyzed_comments) * 100.0, 2),
            question_count=question_count,
            question_percentage=round((question_count / analyzed_comments) * 100.0, 2),
        )


comment_intelligence_service = CommentIntelligenceService()
