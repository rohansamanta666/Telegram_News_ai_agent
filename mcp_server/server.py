"""Daily AI News FastMCP Server.

Exposes standard MCP tools over stdio transport to query and aggregate
AI news from multiple verified sources.
"""

import sys
import asyncio
import logging
from typing import List, Dict, Any

from mcp.server.fastmcp import FastMCP
from mcp_server.cache import cache
from mcp_server.models import Article
from mcp_server.fetchers import FETCHERS, get_fetcher
from mcp_server.content_extractor import extract_article_content

# Configure logging to stderr so stdio JSON-RPC transport on stdout is unaffected
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("mcp_news_server")

# Initialize FastMCP Server
mcp = FastMCP(
    name="Daily AI News Server",
    instructions="Provides verified, up-to-the-minute AI news and article extraction."
)


@mcp.tool()
async def list_sources() -> List[str]:
    """List all available AI news sources supported by this server.

    Returns:
        List of source identifier strings.
    """
    return list(FETCHERS.keys())


@mcp.tool()
async def get_latest_news(source: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch the latest AI articles from a specific news source.

    Args:
        source: Name of the news source (e.g. 'the_guardian', 'the_batch',
                'mit_tech_review', 'mit_news', 'hacker_news', 'techcrunch', 'ars_technica')
        limit: Maximum number of articles to return (default: 5)

    Returns:
        List of normalized article objects with title, source, url, published_at, summary, author.
    """
    cache_key = f"latest:{source}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info(f"Returning cached articles for {cache_key}")
        return cached

    try:
        fetcher = get_fetcher(source)
        articles: List[Article] = await fetcher.fetch_articles(limit=limit)
        results = [a.to_dict() for a in articles]
        cache.set(cache_key, results, ttl_seconds=900)  # 15 minutes TTL
        return results
    except Exception as exc:
        logger.error(f"Error fetching from source '{source}': {exc}", exc_info=True)
        return []


@mcp.tool()
async def get_all_news(limit_per_source: int = 3) -> List[Dict[str, Any]]:
    """Fetch a combined, deduplicated collection of latest news from ALL sources.

    Gracefully handles partial failures (if one source fails or times out,
    articles from the remaining sources are still returned).

    Args:
        limit_per_source: Number of top articles to fetch from each source.

    Returns:
        Deduplicated list of normalized article dictionaries sorted by source and freshness.
    """
    cache_key = f"all_news:{limit_per_source}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info(f"Returning cached results for {cache_key}")
        return cached

    tasks = [fetcher.fetch_articles(limit=limit_per_source) for fetcher in FETCHERS.values()]
    # Gather with return_exceptions=True so one failed source doesn't crash the whole batch
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles: List[Article] = []
    seen_urls = set()
    seen_titles = set()

    for idx, resp in enumerate(responses):
        source_name = list(FETCHERS.keys())[idx]
        if isinstance(resp, Exception):
            logger.warning(f"Source '{source_name}' failed during get_all_news: {resp}")
            continue

        for article in resp:
            # Deduplicate by URL or normalized title
            norm_title = article.title.lower().strip()
            if article.url in seen_urls or norm_title in seen_titles:
                continue

            seen_urls.add(article.url)
            seen_titles.add(norm_title)
            all_articles.append(article)

    results = [a.to_dict() for a in all_articles]
    cache.set(cache_key, results, ttl_seconds=900)
    return results


@mcp.tool()
async def search_news(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for news articles matching a specific keyword or phrase across all sources.

    Args:
        query: Keyword or search phrase (e.g. 'DeepSeek', 'OpenAI', 'Gemini', 'robots')
        limit: Maximum number of search results to return (default: 10)

    Returns:
        List of matching article dictionaries.
    """
    clean_query = query.lower().strip()
    # First get latest news from all sources
    all_articles = await get_all_news(limit_per_source=5)

    matched = []
    for item in all_articles:
        title = item.get("title", "").lower()
        summary = item.get("summary", "").lower()
        if clean_query in title or clean_query in summary:
            matched.append(item)
        if len(matched) >= limit:
            break

    return matched


@mcp.tool()
async def get_article_content(url: str) -> str:
    """Fetch and extract the full, readable text of an article for in-depth analysis.

    Strips out ads, navigation menus, and boilerplate markup.

    Args:
        url: Direct web URL of the article.

    Returns:
        Clean plain-text body of the article.
    """
    cache_key = f"content:{url}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    content = await extract_article_content(url)
    cache.set(cache_key, content, ttl_seconds=3600)  # Cache article content for 1 hour
    return content


def run_stdio():
    """Run the FastMCP server over standard I/O."""
    logger.info("Starting Daily AI News FastMCP Server on stdio...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_stdio()

