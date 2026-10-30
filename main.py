"""Entrypoint for the Daily AI News Telegram Bot and AI Engine."""

import sys
import logging
from config import settings
from agent.memory import init_database
from bot.telegram_bot import build_application

# Setup structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")


def print_banner():
    banner = f"""
========================================================================
             🤖 DAILY AI NEWS TELEGRAM BOT 📰
========================================================================
 • Sources       : The Guardian, DeepLearning.AI The Batch,
                   MIT Tech Review, MIT News, Hacker News,
                   TechCrunch AI, Ars Technica
 • Delivery Time : {settings.delivery_time} ({settings.timezone})
 • Allowed Chats : {settings.allowed_chat_ids_list}
 • Database Path : {settings.database_path}
 • LLM Model     : {settings.gemini_model}
========================================================================
    """
    print(banner)


def main():
    """Start database, scheduler, and Telegram bot event loop."""
    print_banner()

    # Ensure SQLite directory and tables exist
    init_database()

    # Build python-telegram-bot application with JobQueue
    logger.info("Initializing Telegram bot and armed scheduler...")
    app = build_application()

    logger.info("Starting bot long-polling... Press Ctrl+C to terminate.")
    # Run polling (blocking)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

