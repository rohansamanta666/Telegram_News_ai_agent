"""Unit tests for LangGraph 6-node Daily Digest workflow."""

import pytest
from unittest.mock import patch, AsyncMock
from agent.digest_workflow import build_digest_graph


@pytest.mark.asyncio
async def test_digest_graph_pipeline():
    """Verify state transitions across all 6 nodes of the digest workflow."""
    mock_articles = [
        {
            "title": "Quantum AI Breakthrough",
            "source": "The Guardian",
            "url": "https://example.com/qai",
            "published_at": "2026-10-30T10:00:00Z",
            "summary": "Quantum computer trains LLM 10x faster.",
            "author": "Tech Staff"
        },
        {
            "title": "Open Source Weights Released",
            "source": "Hacker News",
            "url": "https://example.com/weights",
            "published_at": "2026-10-30T09:00:00Z",
            "summary": "Community releases open model.",
            "author": "Dev"
        }
    ]

    graph = build_digest_graph()

    with patch("agent.digest_workflow.get_all_news", AsyncMock(return_value=mock_articles)), \
         patch("agent.digest_workflow.save_daily_digest", return_value=1), \
         patch("agent.digest_workflow.Bot") as MockBot:

        mock_bot_instance = AsyncMock()
        MockBot.return_value = mock_bot_instance

        initial_state = {
            "raw_articles": [],
            "filtered_articles": [],
            "summarized_articles": [],
            "top_stories_summary": "",
            "full_newsletter_text": "",
            "newsletter_chunks": [],
            "delivery_status": "",
            "target_chat_id": 12345678,
            "error": None
        }

        final_state = await graph.ainvoke(initial_state)

        assert len(final_state["raw_articles"]) == 2
        assert len(final_state["filtered_articles"]) == 2
        assert len(final_state["newsletter_chunks"]) >= 1
        assert "DAILY AI NEWS DIGEST" in final_state["full_newsletter_text"]
        assert "Quantum AI Breakthrough" in final_state["full_newsletter_text"]
        assert final_state["delivery_status"] == "success"

