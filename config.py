"""Application configuration loaded from environment variables."""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_chat_ids: str = Field("", alias="TELEGRAM_ALLOWED_CHAT_IDS")

    # LLM (Google Gemini)
    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")
    google_api_key: str = Field("", alias="GOOGLE_API_KEY")
    gemini_model: str = Field("gemini-3.8-flash", alias="GEMINI_MODEL")

    # News APIs
    guardian_api_key: str = Field("", alias="GUARDIAN_API_KEY")

    # Scheduler
    delivery_time: str = Field("09:10", alias="DELIVERY_TIME")
    timezone: str = Field("Asia/Kolkata", alias="TIMEZONE")

    # Storage
    database_path: str = Field("data/bot_memory.db", alias="DATABASE_PATH")
    cache_ttl_seconds: int = Field(900, alias="CACHE_TTL_SECONDS")  # 15 minutes

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @property
    def allowed_chat_ids_list(self) -> List[int]:
        """Parse comma-separated chat IDs into a list of integers."""
        if not self.telegram_allowed_chat_ids:
            return []
        ids = []
        for raw_id in self.telegram_allowed_chat_ids.split(","):
            cleaned = raw_id.strip()
            if cleaned:
                try:
                    ids.append(int(cleaned))
                except ValueError:
                    continue
        return ids

    @property
    def effective_gemini_api_key(self) -> str:
        """Return whichever key is set."""
        return self.gemini_api_key or self.google_api_key or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")


# Singleton instance
settings = Settings()
