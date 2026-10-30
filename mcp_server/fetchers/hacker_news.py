"""Fetcher for Hacker News AI stories via Algolia API."""

import logging
from typing import List
from mcp_server.fetchers.base import BaseFetcher
from mcp_server.models import Article

logger = logging.getLogger(__name__)


class HackerNewsFetcher(BaseFetcher):
    """Fetches high-ranking AI stories from Hacker News via official Algolia Search API."""

    API_URL = "https://hn.algolia.com/api/v1/search_by_date"

    def __init__(self):
        super().__init__(name="hacker_news")

    async def fetch_articles(self, limit: int = 5) -> List[Article]:
        try:
            # Look for AI / LLM / Machine Learning stories with points > 5
            params = {
                "tags": "story",
                "query": "AI OR LLM OR OpenAI OR Anthropic",
                "numericFilters": "points>5",
                "hitsPerPage": str(min(limit * 2, 25)),
            }
            resp = await self._get_with_retry(self.API_URL, params=params)
            data = resp.json()
            hits = data.get("hits", [])

            articles: List[Article] = []
            for hit in hits:
                title = hit.get("title")
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                if not title:
                    continue

                points = hit.get("points", 0)
                num_comments = hit.get("num_comments", 0)
                summary = (
                    f"Trending on Hacker News ({points} points, {num_comments} comments). "
                    f"Community discussion: https://news.ycombinator.com/item?id={hit.get('objectID')}"
                )

                article = Article(
                    title=title,
                    source="Hacker News",
                    url=url,
                    published_at=hit.get("created_at", ""),
                    summary=summary,
                    author=hit.get("author")
                )
                articles.append(article)

                if len(articles) >= limit:
                    break

            return articles
        except Exception as exc:
            logger.error(f"[{self.name}] Error fetching Hacker News: {exc}")
            return []

