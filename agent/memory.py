"""Memory and database persistence for conversations and daily digests."""

import os
import json
import sqlite3
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)


def ensure_db_dir(db_path: str) -> None:
    """Ensure parent directory of database path exists."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)


def init_database(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database tables for digest archives."""
    path = db_path or settings.database_path
    ensure_db_dir(path)

    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_digests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                digest_date TEXT NOT NULL,
                top_stories_summary TEXT,
                newsletter_text TEXT NOT NULL,
                raw_articles_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_digest_date ON daily_digests(digest_date);
            """
        )
        conn.commit()
    logger.info(f"Database initialized at {path}")


def save_daily_digest(
    newsletter_text: str,
    top_stories_summary: str,
    raw_articles: List[Dict[str, Any]],
    digest_date: Optional[str] = None,
    db_path: Optional[str] = None
) -> int:
    """Store today's compiled newsletter and articles in SQLite."""
    path = db_path or settings.database_path
    init_database(path)

    date_str = digest_date or datetime.now().strftime("%Y-%m-%d")
    articles_json = json.dumps(raw_articles, ensure_ascii=False)

    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO daily_digests (digest_date, top_stories_summary, newsletter_text, raw_articles_json)
            VALUES (?, ?, ?, ?)
            """,
            (date_str, top_stories_summary, newsletter_text, articles_json)
        )
        conn.commit()
        last_id = cursor.lastrowid
        logger.info(f"Saved daily digest #{last_id} for {date_str}")
        return last_id


def get_latest_daily_digest(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent daily digest."""
    path = db_path or settings.database_path
    init_database(path)

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, digest_date, top_stories_summary, newsletter_text, raw_articles_json, created_at
            FROM daily_digests
            ORDER BY id DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row["id"],
            "digest_date": row["digest_date"],
            "top_stories_summary": row["top_stories_summary"],
            "newsletter_text": row["newsletter_text"],
            "raw_articles": json.loads(row["raw_articles_json"]) if row["raw_articles_json"] else [],
            "created_at": row["created_at"]
        }


def get_digest_by_date(digest_date: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a digest for a specific date (YYYY-MM-DD)."""
    path = db_path or settings.database_path
    init_database(path)

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, digest_date, top_stories_summary, newsletter_text, raw_articles_json, created_at
            FROM daily_digests
            WHERE digest_date = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (digest_date,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row["id"],
            "digest_date": row["digest_date"],
            "top_stories_summary": row["top_stories_summary"],
            "newsletter_text": row["newsletter_text"],
            "raw_articles": json.loads(row["raw_articles_json"]) if row["raw_articles_json"] else [],
            "created_at": row["created_at"]
        }

