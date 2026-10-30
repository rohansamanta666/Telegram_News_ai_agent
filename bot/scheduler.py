"""JobQueue scheduler for daily automated AI news dispatch."""

import datetime
import logging
import pytz
from telegram.ext import Application, ContextTypes

from config import settings
from agent.digest_workflow import digest_graph

logger = logging.getLogger(__name__)


async def scheduled_digest_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback triggered every day at the scheduled time (e.g., 9:10 AM IST)."""
    logger.info("Executing scheduled daily AI news digest job...")
    try:
        initial_state = {
            "raw_articles": [],
            "filtered_articles": [],
            "summarized_articles": [],
            "top_stories_summary": "",
            "full_newsletter_text": "",
            "newsletter_chunks": [],
            "delivery_status": "",
            "target_chat_id": None,  # Will broadcast to all allowed_chat_ids
            "error": None
        }
        final_state = await digest_graph.ainvoke(initial_state)
        logger.info(f"Daily digest job completed with status: {final_state.get('delivery_status')}")
    except Exception as exc:
        logger.error(f"Error during scheduled daily digest job: {exc}", exc_info=True)


def setup_scheduler(app: Application) -> None:
    """Register daily scheduled job with python-telegram-bot's JobQueue."""
    if not app.job_queue:
        logger.warning("JobQueue is not enabled in Application. Scheduled dispatches will be inactive.")
        return

    tz_str = settings.timezone or "Asia/Kolkata"
    tz = pytz.timezone(tz_str)

    # Parse delivery time HH:MM
    raw_time = settings.delivery_time or "09:10"
    try:
        parts = raw_time.strip().replace(".", ":").split(":")
        hour = int(parts[0])
        minute = int(parts[1])
    except Exception:
        hour, minute = 9, 10
        logger.warning(f"Failed to parse DELIVERY_TIME '{raw_time}', defaulting to 09:10")

    target_time = datetime.time(hour=hour, minute=minute, second=0, tzinfo=tz)

    app.job_queue.run_daily(
        callback=scheduled_digest_job,
        time=target_time,
        name="daily_ai_news_digest"
    )
    logger.info(f"Scheduler armed: Daily digest will be sent every day at {hour:02d}:{minute:02d} ({tz_str})")

