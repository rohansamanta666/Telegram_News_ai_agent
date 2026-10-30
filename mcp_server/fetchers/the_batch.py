"""Fetcher for DeepLearning.AI (The Batch)."""

import re
import logging
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from mcp_server.fetchers.base import BaseFetcher
from mcp_server.models import Article

logger = logging.getLogger(__name__)


class TheBatchFetcher(BaseFetcher):
    """Fetches articles from DeepLearning.AI's weekly newsletter 'The Batch'."""

    BASE_URL = "https://www.deeplearning.ai/the-batch/"

    def __init__(self):
        super().__init__(name="deeplearning_ai_the_batch")

    async def fetch_articles(self, limit: int = 5) -> List[Article]:
        articles: List[Article] = []
        try:
            resp = await self._get_with_retry(self.BASE_URL)
            html = resp.text

            # Extract latest issue number
            issues = re.findall(r"/the-batch/issue-(\d+)", html)
            if not issues:
                logger.warning(f"[{self.name}] No issue numbers found in The Batch index.")
                return []

            latest_num = max(int(x) for x in set(issues))
            latest_issue_url = f"https://www.deeplearning.ai/the-batch/issue-{latest_num}/"
            logger.info(f"[{self.name}] Fetching latest issue: {latest_issue_url}")

            issue_resp = await self._get_with_retry(latest_issue_url)
            soup = BeautifulSoup(issue_resp.text, "html.parser")

            ignored_keywords = [
                "news", "the batch", "subscribe to the batch",
                "a message from", "learn", "company", "choose your plan",
                "introducing deeplearning.ai", "deeplearning.ai pro", "careers",
                "andrew's letter", "letter from andrew"
            ]

            for heading in soup.find_all(["h1", "h2"]):
                title = heading.get_text(strip=True)
                title_lower = title.lower()
                if not title or len(title) < 5 or any(k in title_lower for k in ignored_keywords):
                    continue

                # Find first non-empty following paragraph
                summary = ""
                curr = heading.find_next_sibling()
                while curr and not summary:
                    if curr.name == "p":
                        text = curr.get_text(strip=True)
                        if len(text) > 25 and "subscribe" not in text.lower():
                            summary = text
                    elif curr.name in ["h1", "h2"]:
                        break
                    curr = curr.find_next_sibling()

                if not summary:
                    # Try find_next
                    p = heading.find_next("p")
                    if p:
                        summary = p.get_text(strip=True)

                if summary and len(summary) > 25:
                    article = Article(
                        title=title,
                        source="DeepLearning.AI (The Batch)",
                        url=latest_issue_url,
                        published_at=datetime.utcnow().isoformat() + "Z",
                        summary=summary[:400],
                        author="Andrew Ng & The Batch Editorial"
                    )
                    articles.append(article)

                if len(articles) >= limit:
                    break

        except Exception as exc:
            logger.error(f"[{self.name}] Error fetching articles: {exc}", exc_info=True)

        return articles[:limit]
