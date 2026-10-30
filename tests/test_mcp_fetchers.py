"""Unit tests for MCP server tools with mocked HTTP responses."""

import pytest
from unittest.mock import patch, MagicMock
from mcp_server.models import Article
from mcp_server.fetchers.guardian import GuardianFetcher
from mcp_server.fetchers.hacker_news import HackerNewsFetcher
from mcp_server.server import list_sources, search_news, get_latest_news


@pytest.mark.asyncio
async def test_list_sources():
    """Verify all 7 news sources are listed."""
    sources = await list_sources()
    assert "the_guardian" in sources
    assert "the_batch" in sources
    assert "mit_tech_review" in sources
    assert "mit_news" in sources
    assert "hacker_news" in sources
    assert "techcrunch" in sources
    assert "ars_technica" in sources


@pytest.mark.asyncio
async def test_guardian_fetcher_mocked():
    """Test Guardian fetcher parsing with mocked API response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {
            "results": [
                {
                    "webTitle": "Mocked AI Breakthrough",
                    "webUrl": "https://theguardian.com/tech/mock-ai",
                    "webPublicationDate": "2026-10-30T10:00:00Z",
                    "fields": {
                        "trailText": "A major discovery in artificial intelligence.",
                        "byline": "Jane Doe"
                    }
                }
            ]
        }
    }
    mock_response.status_code = 200

    fetcher = GuardianFetcher(api_key="mock_key")
    with patch.object(fetcher, "_get_with_retry", return_value=mock_response):
        articles = await fetcher.fetch_articles(limit=1)
        assert len(articles) == 1
        assert articles[0].title == "Mocked AI Breakthrough"
        assert articles[0].source == "The Guardian"
        assert articles[0].author == "Jane Doe"


@pytest.mark.asyncio
async def test_hacker_news_fetcher_mocked():
    """Test Hacker News fetcher parsing with mocked Algolia response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "hits": [
            {
                "title": "Show HN: Open Source Neural Agent",
                "url": "https://example.com/agent",
                "created_at": "2026-10-30T09:00:00Z",
                "points": 150,
                "num_comments": 42,
                "author": "hn_user",
                "objectID": "12345"
            }
        ]
    }
    mock_response.status_code = 200

    fetcher = HackerNewsFetcher()
    with patch.object(fetcher, "_get_with_retry", return_value=mock_response):
        articles = await fetcher.fetch_articles(limit=1)
        assert len(articles) == 1
        assert articles[0].title == "Show HN: Open Source Neural Agent"
        assert "150 points" in articles[0].summary
        assert articles[0].author == "hn_user"


@pytest.mark.asyncio
async def test_search_news_mocked():
    """Test search filtering across articles."""
    dummy_articles = [
        {
            "title": "Quantum Computing Meets AI",
            "source": "MIT Tech Review",
            "url": "https://example.com/1",
            "published_at": "2026-10-30T00:00:00Z",
            "summary": "Quantum algorithms speed up neural networks.",
            "author": "Alice"
        },
        {
            "title": "Standard Silicon Advancements",
            "source": "TechCrunch",
            "url": "https://example.com/2",
            "published_at": "2026-10-30T00:00:00Z",
            "summary": "New chip architecture released.",
            "author": "Bob"
        }
    ]

    with patch("mcp_server.server.get_all_news", return_value=dummy_articles):
        results = await search_news("quantum", limit=5)
        assert len(results) == 1
        assert "Quantum" in results[0]["title"]

