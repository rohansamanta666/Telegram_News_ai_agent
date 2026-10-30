"""Fetcher for The Guardian with API and RSS fallback."""

import logging
from typing import List, Optional
import feedparser
from bs4 import BeautifulSoup

from config import settings
from mcp_server.fetchers.base import BaseFetcher
from mcp_server.models import Article

logger = logging.getLogger(__name__)


class GuardianFetcher(BaseFetcher):
    """Fetches AI news from The Guardian using Open Platform API with RSS fallback."""

    API_URL = "https://content.guardianapis.com/search"
    RSS_URL = "https://www.theguardian.com/technology/artificialintelligenceai/rss"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="the_guardian")
        self.api_key = api_key or settings.guardian_api_key

    async def fetch_articles(self, limit: int = 5) -> List[Article]:
        # 1. Try Open Platform API if key is available
        if self.api_key and self.api_key.strip():
            try:
                articles = await self._fetch_via_api(limit)
                if articles:
                    return articles
            except Exception as exc:
                logger.warning(f"[{self.name}] API failed, falling back to RSS: {exc}")

        # 2. Fallback to RSS feed
        return await self._fetch_via_rss(limit)

    async def _fetch_via_api(self, limit: int) -> List[Article]:
        params = {
            "q": "artificial intelligence OR AI OR machine learning",
            "section": "technology",
            "api-key": self.api_key,
            "show-fields": "headline,byline,trailText,publication",
            "page-size": str(min(limit, 20)),
            "order-by": "newest",
        }
        resp = await self._get_with_retry(self.API_URL, params=params)
        data = resp.json()
        results = data.get("response", {}).get("results", [])

        articles: List[Article] = []
        for item in results:
            fields = item.get("fields", {})
            raw_trail = fields.get("trailText") or item.get("webTitle", "")
            # Clean HTML from trailText
            clean_summary = BeautifulSoup(raw_trail, "html.parser").get_text(strip=True)

            article = Article(
                title=item.get("webTitle", "No Title"),
                source="The Guardian",
                url=item.get("webUrl", ""),
                published_at=item.get("webPublicationDate", ""),
                summary=clean_summary[:400],
                author=fields.get("byline")
            )
            articles.append(article)
        return articles[:limit]

    async def _fetch_via_rss(self, limit: int) -> List[Article]:
        resp = await self._get_with_retry(self.RSS_URL)
        feed = feedparser.parse(resp.text)
        articles: List[Article] = []

        for entry in feed.entries[:limit]:
            clean_summary = BeautifulSoup(getattr(entry, "summary", ""), "html.parser").get_text(strip=True)
            article = Article(
                title=getattr(entry, "title", "No Title"),
                source="The Guardian",
                url=getattr(entry, "link", ""),
                published_at=getattr(entry, "published", ""),
                summary=clean_summary[:400] or "Guardian technology coverage",
                author=getattr(entry, "author", None)
            )
            articles.append(article)
        return articles[:limit]

