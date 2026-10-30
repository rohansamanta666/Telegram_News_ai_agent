"""Fetchers for MIT Technology Review and MIT News."""

import logging
from typing import List
import feedparser
from bs4 import BeautifulSoup

from mcp_server.fetchers.base import BaseFetcher
from mcp_server.models import Article

logger = logging.getLogger(__name__)


class MITTechReviewFetcher(BaseFetcher):
    """Fetches articles from MIT Technology Review RSS feed."""

    RSS_URL = "https://www.technologyreview.com/feed/"

    def __init__(self):
        super().__init__(name="mit_tech_review")

    async def fetch_articles(self, limit: int = 5) -> List[Article]:
        try:
            resp = await self._get_with_retry(self.RSS_URL)
            feed = feedparser.parse(resp.text)
            articles: List[Article] = []

            for entry in feed.entries[:limit]:
                raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text(strip=True)

                article = Article(
                    title=getattr(entry, "title", "MIT Tech Review Story"),
                    source="MIT Technology Review",
                    url=getattr(entry, "link", ""),
                    published_at=getattr(entry, "published", ""),
                    summary=clean_summary[:400] or "MIT Technology Review article",
                    author=getattr(entry, "author", "MIT Technology Review Editorial")
                )
                articles.append(article)
            return articles
        except Exception as exc:
            logger.error(f"[{self.name}] Error fetching feed: {exc}")
            return []


class MITNewsFetcher(BaseFetcher):
    """Fetches research & AI articles from MIT News RSS feed."""

    RSS_URL = "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml"

    def __init__(self):
        super().__init__(name="mit_news")

    async def fetch_articles(self, limit: int = 5) -> List[Article]:
        try:
            resp = await self._get_with_retry(self.RSS_URL)
            feed = feedparser.parse(resp.text)
            articles: List[Article] = []

            for entry in feed.entries[:limit]:
                raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text(strip=True)

                article = Article(
                    title=getattr(entry, "title", "MIT News AI Story"),
                    source="MIT News",
                    url=getattr(entry, "link", ""),
                    published_at=getattr(entry, "published", ""),
                    summary=clean_summary[:400] or "MIT News AI research development",
                    author=getattr(entry, "author", "MIT News Office")
                )
                articles.append(article)
            return articles
        except Exception as exc:
            logger.error(f"[{self.name}] Error fetching feed: {exc}")
            return []

