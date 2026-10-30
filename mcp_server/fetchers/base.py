"""Base abstract class for news fetchers with retry and normalization logic."""

import abc
import logging
from typing import List, Optional
import httpx
from mcp_server.models import Article

logger = logging.getLogger(__name__)


class BaseFetcher(abc.ABC):
    """Abstract base class that all source fetchers implement."""

    def __init__(self, name: str, default_timeout: float = 12.0):
        self.name = name
        self.default_timeout = default_timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (DailyAINewsBot/1.0)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
        }

    async def _get_with_retry(self, url: str, params: Optional[dict] = None, max_retries: int = 2) -> httpx.Response:
        """Fetch URL with retries on network or server errors."""
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.default_timeout, headers=self.headers, follow_redirects=True) as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    return resp
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_exception = exc
                logger.warning(f"[{self.name}] Fetch attempt {attempt + 1}/{max_retries + 1} failed for {url}: {exc}")
        raise last_exception if last_exception else RuntimeError(f"Failed to fetch {url}")

    @abc.abstractmethod
    async def fetch_articles(self, limit: int = 5) -> List[Article]:
        """Fetch the latest articles normalized to the Article schema."""
        pass

