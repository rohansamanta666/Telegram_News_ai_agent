"""Entrypoint for the Daily AI News Telegram Bot and AI Engine."""

import os
import sys
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

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


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler to satisfy cloud hosting health checks (Render, Koyeb, etc.)."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Daily AI News Telegram Bot is running OK!\n")

    def log_message(self, format, *args):
        # Suppress routine health check log noise
        pass


def maybe_start_health_server():
    """Start HTTP server if PORT environment variable is set by the cloud platform."""
    port_str = os.getenv("PORT")
    if port_str:
        try:
            port = int(port_str)
            server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            logger.info(f"Cloud health-check server bound to http://0.0.0.0:{port}")
        except Exception as exc:
            logger.warning(f"Failed to start cloud health-check server on port {port_str}: {exc}")


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
    """Start database, scheduler, cloud health server, and Telegram bot loop."""
    print_banner()

    # Ensure SQLite directory and tables exist
    init_database()

    # Start cloud health server if PORT is provided (Render / Koyeb / Fly)
    maybe_start_health_server()

    # Build python-telegram-bot application with JobQueue
    logger.info("Initializing Telegram bot and armed scheduler...")
    app = build_application()

    logger.info("Starting bot long-polling... Press Ctrl+C to terminate.")
    # Run polling (blocking)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
