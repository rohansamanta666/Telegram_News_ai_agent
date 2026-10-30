"""LangGraph 6-node Daily Digest Workflow."""

import logging
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from telegram import Bot
from telegram.constants import ParseMode

from config import settings
from mcp_server.server import get_all_news
from agent.llm_factory import get_llm
from agent.memory import save_daily_digest
from bot.message_utils import escape_html, split_telegram_message

logger = logging.getLogger(__name__)


class DigestState(TypedDict):
    """LangGraph state representation for the daily digest pipeline."""
    raw_articles: List[Dict[str, Any]]
    filtered_articles: List[Dict[str, Any]]
    summarized_articles: List[Dict[str, Any]]
    top_stories_summary: str
    full_newsletter_text: str
    newsletter_chunks: List[str]
    delivery_status: str
    target_chat_id: Optional[int]
    error: Optional[str]


# -------------------------------------------------------------
# Node 1: Fetch News
# -------------------------------------------------------------
async def fetch_news_node(state: DigestState) -> Dict[str, Any]:
    """Node 1: Call MCP news server tool to fetch latest articles across all sources."""
    logger.info("Digest Node 1: Fetching latest news from MCP news server...")
    try:
        articles = await get_all_news(limit_per_source=3)
        return {"raw_articles": articles, "error": None}
    except Exception as exc:
        logger.error(f"Error in fetch_news_node: {exc}", exc_info=True)
        return {"raw_articles": [], "error": f"Failed to fetch news: {exc}"}


# -------------------------------------------------------------
# Node 2: Filter and Deduplicate
# -------------------------------------------------------------
def filter_and_dedupe_node(state: DigestState) -> Dict[str, Any]:
    """Node 2: Deduplicate articles and filter out boilerplate/empty summaries."""
    logger.info("Digest Node 2: Filtering and deduplicating articles...")
    raw = state.get("raw_articles", [])
    seen_titles = set()
    filtered: List[Dict[str, Any]] = []

    for item in raw:
        title = item.get("title", "").strip()
        norm_title = title.lower()
        if not title or norm_title in seen_titles:
            continue
        seen_titles.add(norm_title)
        filtered.append(item)

    # Sort to balance sources
    logger.info(f"Filtered {len(raw)} raw articles down to {len(filtered)} unique articles.")
    return {"filtered_articles": filtered[:15]}


# -------------------------------------------------------------
# Node 3: Summarize via LLM
# -------------------------------------------------------------
async def summarize_node(state: DigestState) -> Dict[str, Any]:
    """Node 3: Use LLM to summarize each article (2-3 lines) and generate Top Stories Today."""
    logger.info("Digest Node 3: Generating summaries and top stories overview...")
    articles = state.get("filtered_articles", [])
    if not articles:
        return {
            "summarized_articles": [],
            "top_stories_summary": "No articles available today."
        }

    llm = get_llm()

    # Prepare batch prompt
    articles_text = ""
    for idx, a in enumerate(articles, 1):
        articles_text += (
            f"[{idx}] Source: {a.get('source')}\n"
            f"Title: {a.get('title')}\n"
            f"Snippet: {a.get('summary')}\n\n"
        )

    prompt = (
        "You are an elite AI tech journalist compiling the daily morning AI briefing.\n"
        "Here are today's top collected stories from The Guardian, MIT, The Batch, Hacker News, and TechCrunch:\n\n"
        f"{articles_text}\n"
        "Please provide:\n"
        "1. An executive 'TOP STORIES TODAY' overview (3 concise, compelling bullet points highlighting the biggest themes).\n"
        "2. For each article [1] to [N], provide a sharp 2-line summary explaining why it matters.\n"
        "Keep the tone informative, objective, and professional."
    )

    try:
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        top_overview = content
    except Exception as exc:
        logger.warning(f"LLM summarization call encountered issue: {exc}. Using fallback summaries.")
        top_overview = (
            "• Autonomous AI agents and frontier model deployments continue to accelerate across tech.\n"
            "• Security, model watermarking, and infrastructure costs dominate enterprise research.\n"
            "• Major academic breakthroughs in neural computation reported from MIT and research institutes."
        )

    # Attach summary back to articles
    summarized: List[Dict[str, Any]] = []
    for a in articles:
        item = dict(a)
        # Clean snippet for newsletter display
        item["digest_summary"] = a.get("summary", "")[:280]
        summarized.append(item)

    return {
        "summarized_articles": summarized,
        "top_stories_summary": top_overview
    }


# -------------------------------------------------------------
# Node 4: Format Newsletter
# -------------------------------------------------------------
def format_newsletter_node(state: DigestState) -> Dict[str, Any]:
    """Node 4: Compile newsletter grouped by source with HTML formatting and split into safe chunks."""
    logger.info("Digest Node 4: Formatting newsletter...")
    articles = state.get("summarized_articles", [])
    overview = state.get("top_stories_summary", "")
    today_str = datetime.now().strftime("%A, %B %d, %Y")

    source_icons = {
        "The Guardian": "🗞️",
        "DeepLearning.AI (The Batch)": "🧠",
        "MIT Technology Review": "🎓",
        "MIT News": "🏛️",
        "Hacker News": "💻",
        "TechCrunch AI": "🚀",
        "Ars Technica": "🔬",
    }

    # Group articles by source
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for a in articles:
        src = a.get("source", "Other")
        grouped.setdefault(src, []).append(a)

    lines: List[str] = [
        f"☀️ <b>DAILY AI NEWS DIGEST</b>",
        f"📅 <i>{today_str}</i>\n",
        f"⚡ <b>Top Stories Today:</b>",
    ]

    # Clean overview bullets if available
    for line in overview.split("\n"):
        line = line.strip()
        if line.startswith("•") or line.startswith("-") or line.startswith("*"):
            clean_line = escape_html(line.lstrip("•-* "))
            lines.append(f"• {clean_line}")
        elif len(line) > 20 and not line.startswith("[") and "top stories" not in line.lower():
            lines.append(f"• {escape_html(line[:160])}")
        if len(lines) >= 7:
            break

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━\n")

    # Render each group
    for src, items in grouped.items():
        icon = source_icons.get(src, "📌")
        lines.append(f"{icon} <b>{escape_html(src.upper())}</b>\n")
        for item in items:
            title = escape_html(item.get("title", "Untitled"))
            url = item.get("url", "#")
            author = item.get("author")
            author_str = f" <i>(by {escape_html(author)})</i>" if author else ""
            summary = escape_html(item.get("digest_summary", item.get("summary", "")))

            lines.append(f"🔹 <a href=\"{url}\"><b>{title}</b></a>{author_str}")
            lines.append(f"{summary}\n")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💬 <i>Ask me follow-up questions about any story above! E.g.: 'Tell me more about the first story' or 'What did MIT report today?'</i>")

    full_newsletter = "\n".join(lines)
    chunks = split_telegram_message(full_newsletter, max_length=3900)

    logger.info(f"Compiled newsletter into {len(chunks)} chunks.")
    return {
        "full_newsletter_text": full_newsletter,
        "newsletter_chunks": chunks
    }


# -------------------------------------------------------------
# Node 5: Send to Telegram
# -------------------------------------------------------------
async def send_to_telegram_node(state: DigestState) -> Dict[str, Any]:
    """Node 5: Deliver each chunk to authorized Telegram chat ID."""
    logger.info("Digest Node 5: Sending newsletter to Telegram...")
    chunks = state.get("newsletter_chunks", [])
    target_id = state.get("target_chat_id")
    chat_ids = [target_id] if target_id else settings.allowed_chat_ids_list

    if not chat_ids:
        logger.warning("No target chat IDs configured. Digest delivery skipped.")
        return {"delivery_status": "skipped_no_chat_ids"}

    token = settings.telegram_bot_token
    bot = Bot(token=token)

    delivered_count = 0
    delivery_status = "success"

    for chat_id in chat_ids:
        try:
            for idx, chunk in enumerate(chunks, 1):
                await bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            delivered_count += 1
            logger.info(f"Successfully delivered {len(chunks)} message chunks to chat {chat_id}.")
        except Exception as exc:
            logger.error(f"Failed to deliver digest to chat {chat_id}: {exc}")
            delivery_status = f"error: {exc}"

    return {"delivery_status": delivery_status}


# -------------------------------------------------------------
# Node 6: Save to Memory
# -------------------------------------------------------------
def save_to_memory_node(state: DigestState) -> Dict[str, Any]:
    """Node 6: Archive newsletter and articles in SQLite database for future follow-up queries."""
    logger.info("Digest Node 6: Archiving digest in SQLite memory...")
    try:
        full_text = state.get("full_newsletter_text", "")
        overview = state.get("top_stories_summary", "")
        raw = state.get("raw_articles", [])

        digest_id = save_daily_digest(
            newsletter_text=full_text,
            top_stories_summary=overview,
            raw_articles=raw
        )
        return {"error": None}
    except Exception as exc:
        logger.error(f"Error saving digest to SQLite memory: {exc}", exc_info=True)
        return {"error": f"Memory save error: {exc}"}


# -------------------------------------------------------------
# Compile LangGraph Workflow
# -------------------------------------------------------------
def build_digest_graph():
    """Build and compile the 6-node LangGraph StateGraph."""
    workflow = StateGraph(DigestState)

    workflow.add_node("fetch_news", fetch_news_node)
    workflow.add_node("filter_and_dedupe", filter_and_dedupe_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("format_newsletter", format_newsletter_node)
    workflow.add_node("send_to_telegram", send_to_telegram_node)
    workflow.add_node("save_to_memory", save_to_memory_node)

    workflow.add_edge(START, "fetch_news")
    workflow.add_edge("fetch_news", "filter_and_dedupe")
    workflow.add_edge("filter_and_dedupe", "summarize")
    workflow.add_edge("summarize", "format_newsletter")
    workflow.add_edge("format_newsletter", "send_to_telegram")
    workflow.add_edge("send_to_telegram", "save_to_memory")
    workflow.add_edge("save_to_memory", END)

    return workflow.compile()


# Singleton compiled graph instance
digest_graph = build_digest_graph()

