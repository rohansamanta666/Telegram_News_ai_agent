"""Fetcher for TechCrunch AI."""

import logging
from typing import List
import feedparser
from bs4 import BeautifulSoup
from mcp_server.fetchers.base import BaseFetcher
from mcp_server.models import Article

logger = logging.getLogger(__name__)


class TechCrunchFetcher(BaseFetcher):
    """Fetches stories from TechCrunch AI category RSS feed."""

    RSS_URL = "https://techcrunch.com/category/artificial-intelligence/feed/"

    def __init__(self):
        super().__init__(name="techcrunch_ai")

    async def fetch_articles(self, limit: int = 5) -> List[Article]:
        try:
            resp = await self._get_with_retry(self.RSS_URL)
            feed = feedparser.parse(resp.text)
            articles: List[Article] = []

            for entry in feed.entries[:limit]:
                raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text(strip=True)

                article = Article(
                    title=getattr(entry, "title", "TechCrunch AI Story"),
                    source="TechCrunch AI",
                    url=getattr(entry, "link", ""),
                    published_at=getattr(entry, "published", ""),
                    summary=clean_summary[:400] or "TechCrunch AI coverage",
                    author=getattr(entry, "author", "TechCrunch Staff")
                )
                articles.append(article)
            return articles
        except Exception as exc:
            logger.error(f"[{self.name}] Error fetching TechCrunch: {exc}")
            return []

