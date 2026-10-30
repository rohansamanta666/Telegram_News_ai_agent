"""Fetcher for Ars Technica."""

import logging
from typing import List
import feedparser
from bs4 import BeautifulSoup
from mcp_server.fetchers.base import BaseFetcher
from mcp_server.models import Article

logger = logging.getLogger(__name__)


class ArsTechnicaFetcher(BaseFetcher):
    """Fetches stories from Ars Technica Technology Lab RSS feed."""

    RSS_URL = "https://feeds.arstechnica.com/arstechnica/technology-lab"

    def __init__(self):
        super().__init__(name="ars_technica")

    async def fetch_articles(self, limit: int = 5) -> List[Article]:
        try:
            resp = await self._get_with_retry(self.RSS_URL)
            feed = feedparser.parse(resp.text)
            articles: List[Article] = []

            for entry in feed.entries[:limit]:
                raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text(strip=True)

                article = Article(
                    title=getattr(entry, "title", "Ars Technica Story"),
                    source="Ars Technica",
                    url=getattr(entry, "link", ""),
                    published_at=getattr(entry, "published", ""),
                    summary=clean_summary[:400] or "Ars Technica Technology coverage",
                    author=getattr(entry, "author", "Ars Technica Staff")
                )
                articles.append(article)
            return articles
        except Exception as exc:
            logger.error(f"[{self.name}] Error fetching Ars Technica: {exc}")
            return []

