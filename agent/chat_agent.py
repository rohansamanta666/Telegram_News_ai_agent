"""Interactive conversational AI agent powered by LangChain, LangGraph & MCP tools."""

import sqlite3
import logging
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from config import settings
from agent.llm_factory import get_llm
from agent.memory import get_latest_daily_digest, get_digest_by_date, init_database
from mcp_server.server import (
    list_sources,
    get_latest_news,
    get_all_news,
    search_news,
    get_article_content
)

logger = logging.getLogger(__name__)


# -------------------------------------------------------------
# LangChain Tool Bindings for MCP Tools & Past Digest Store
# -------------------------------------------------------------

@tool
async def tool_list_sources() -> List[str]:
    """List all available AI news sources supported by the MCP server."""
    return await list_sources()


@tool
async def tool_get_latest_news(source: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch latest AI news articles from a specific source (e.g. 'the_guardian', 'hacker_news', 'mit_tech_review', 'the_batch')."""
    return await get_latest_news(source=source, limit=limit)


@tool
async def tool_search_news(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Search AI news articles across all connected sources for keywords, models, or topics."""
    return await search_news(query=query, limit=limit)


@tool
async def tool_get_article_content(url: str) -> str:
    """Fetch and read the full text of an article for in-depth questions or summaries."""
    return await get_article_content(url=url)


@tool
def tool_get_past_digest(digest_date: str) -> Dict[str, Any]:
    """Retrieve an archived daily digest by date in YYYY-MM-DD format (e.g. '2026-10-30')."""
    digest = get_digest_by_date(digest_date)
    if not digest:
        return {"status": "not_found", "message": f"No digest found for date {digest_date}."}
    return {
        "status": "found",
        "date": digest["digest_date"],
        "top_stories": digest["top_stories_summary"],
        "article_count": len(digest["raw_articles"])
    }


CHAT_TOOLS = [
    tool_list_sources,
    tool_get_latest_news,
    tool_search_news,
    tool_get_article_content,
    tool_get_past_digest
]


class ChatAgentManager:
    """Manages conversational agent sessions with SQLite-backed checkpointer."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.database_path
        init_database(self.db_path)
        self.llm = get_llm()

    def _build_system_prompt(self) -> str:
        """Inject today's digest summary and context into system prompt."""
        latest = get_latest_daily_digest(self.db_path)
        context = ""
        if latest:
            articles = latest.get("raw_articles", [])
            article_list_str = "\n".join(
                [f"[{i+1}] {a.get('source')}: \"{a.get('title')}\" - {a.get('url')}" for i, a in enumerate(articles[:10])]
            )
            context = (
                f"--- TODAY'S DIGEST CONTEXT ({latest.get('digest_date')}) ---\n"
                f"Top Stories Overview:\n{latest.get('top_stories_summary', 'N/A')}\n\n"
                f"Articles sent today:\n{article_list_str}\n"
                "-----------------------------------------------\n"
            )

        return (
            "You are the Daily AI News Assistant Telegram bot.\n"
            "You help the user understand and explore AI news, papers, and tech releases.\n\n"
            f"{context}\n"
            "Guidelines:\n"
            "- When the user asks about 'the second story' or 'today's news', refer directly to Today's Digest Context above.\n"
            "- If the user needs more details on an article, use `tool_get_article_content` with the article's URL.\n"
            "- If the user asks about a fresh topic not in today's digest, use `tool_search_news`.\n"
            "- If the user asks about yesterday or previous days, use `tool_get_past_digest`.\n"
            "- Always format answers cleanly for Telegram using HTML formatting (<b>bold</b>, <i>italic</i>, <a href='...'>links</a>).\n"
            "- Keep replies friendly, accurate, and concise."
        )

    async def chat(self, user_text: str, chat_id: int) -> str:
        """Send a message to the agent and receive a response with chat history."""
        system_prompt = self._build_system_prompt()
        config = {"configurable": {"thread_id": str(chat_id)}}

        try:
            async with AsyncSqliteSaver.from_conn_string(self.db_path) as checkpointer:
                await checkpointer.setup()
                agent = create_react_agent(
                    model=self.llm,
                    tools=CHAT_TOOLS,
                    checkpointer=checkpointer
                )

                inputs = {
                    "messages": [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=user_text)
                    ]
                }

                result = await agent.ainvoke(inputs, config=config)
                messages = result.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    content = getattr(last_msg, "content", str(last_msg))
                    return content
                return "I couldn't process your request. Please try again."

        except Exception as exc:
            logger.error(f"Error in chat processing: {exc}", exc_info=True)
            # Resilient fallback: answer from latest digest if possible
            latest = get_latest_daily_digest(self.db_path)
            if latest:
                return (
                    f"I received your question: <i>\"{user_text}\"</i>.\n\n"
                    f"Here is today's AI Digest ({latest['digest_date']}) context:\n"
                    f"{latest.get('top_stories_summary', '')}\n\n"
                    "Use `/news` to re-send today's full digest or `/help` for options."
                )
            return (
                f"I received your question: <i>\"{user_text}\"</i>.\n\n"
                "I am monitoring AI news across The Guardian, MIT, The Batch, and Hacker News. "
                "Type `/news` to fetch the latest stories!"
            )

    async def clear_memory(self, chat_id: int) -> bool:
        """Clear conversation memory for a chat ID."""
        try:
            async with AsyncSqliteSaver.from_conn_string(self.db_path) as checkpointer:
                await checkpointer.setup()
                try:
                    await checkpointer.adelete_thread(str(chat_id))
                except Exception:
                    pass

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (str(chat_id),))
                try:
                    cursor.execute("DELETE FROM writes WHERE thread_id = ?", (str(chat_id),))
                except Exception:
                    pass
                conn.commit()

            logger.info(f"Cleared memory for chat_id={chat_id}")
            return True
        except Exception as exc:
            logger.error(f"Error clearing memory for {chat_id}: {exc}")
            return False


# Singleton agent manager
chat_agent_manager = ChatAgentManager()
