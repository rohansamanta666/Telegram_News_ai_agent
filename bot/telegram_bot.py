"""Telegram Bot Handlers, Commands, and Dispatcher Setup."""

import logging
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import settings
from bot.auth import restricted
from bot.scheduler import setup_scheduler
from bot.message_utils import split_telegram_message
from agent.digest_workflow import digest_graph
from agent.chat_agent import chat_agent_manager

logger = logging.getLogger(__name__)


# -------------------------------------------------------------
# Command Handlers
# -------------------------------------------------------------

@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    name = user.first_name if user else "Friend"

    welcome_text = (
        f"👋 <b>Welcome, {name}!</b>\n\n"
        f"I am your <b>Daily AI News Assistant</b>.\n\n"
        f"⏰ <b>Schedule:</b> I send a curated AI newsletter every day at <b>{settings.delivery_time} ({settings.timezone})</b>.\n"
        f"🌐 <b>Sources:</b> The Guardian, DeepLearning.AI The Batch, MIT Tech Review, MIT News, Hacker News, TechCrunch & Ars Technica.\n\n"
        f"<b>Available Commands:</b>\n"
        f"• <code>/news</code> - Generate and send today's AI digest immediately\n"
        f"• <code>/clear</code> - Reset conversation history and memory\n"
        f"• <code>/help</code> - How to chat and ask follow-up questions\n\n"
        f"Your Chat ID: <code>{chat_id}</code>"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "💡 <b>How to Use This Bot:</b>\n\n"
        "1. <b>Instant Digest:</b> Type <code>/news</code> anytime to compile and receive the latest AI news digest.\n"
        "2. <b>Ask Follow-up Questions:</b> After receiving the digest, simply ask me follow-up questions in natural language, such as:\n"
        "   • <i>\"Tell me more about the first story\"</i>\n"
        "   • <i>\"What did MIT report about neural networks?\"</i>\n"
        "   • <i>\"Are there any news about OpenAI or DeepSeek?\"</i>\n"
        "   • <i>\"Summarize what Hacker News is discussing today\"</i>\n\n"
        "3. <b>Memory Reset:</b> If you want to start a fresh topic, send <code>/clear</code> to wipe the SQLite checkpointer memory.\n"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


@restricted
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /news command: Trigger the LangGraph daily digest workflow on demand."""
    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_text(
        "🔄 <b>Compiling your AI News Digest...</b>\n"
        "<i>Connecting to MCP news server and fetching stories from 7 sources...</i>",
        parse_mode=ParseMode.HTML
    )

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        initial_state = {
            "raw_articles": [],
            "filtered_articles": [],
            "summarized_articles": [],
            "top_stories_summary": "",
            "full_newsletter_text": "",
            "newsletter_chunks": [],
            "delivery_status": "",
            "target_chat_id": chat_id,
            "error": None
        }

        # Run 6-node LangGraph pipeline
        final_state = await digest_graph.ainvoke(initial_state)

        # Delete status message once digest has been dispatched
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as exc:
        logger.error(f"Error handling /news command: {exc}", exc_info=True)
        await update.message.reply_text(
            f"❌ <b>Error compiling news digest:</b> <code>{exc}</code>",
            parse_mode=ParseMode.HTML
        )


@restricted
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear command: Clear conversational memory checkpointer."""
    chat_id = update.effective_chat.id
    success = await chat_agent_manager.clear_memory(chat_id)
    if success:
        await update.message.reply_text(
            "🧹 <b>Conversation memory has been reset.</b>\n"
            "You can start a fresh conversation with clean context.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "⚠️ Memory could not be fully cleared or was already empty.",
            parse_mode=ParseMode.HTML
        )


@restricted
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle follow-up questions and conversational interaction."""
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if not user_text:
        return

    # Indicate typing state
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # Invoke chat agent with SQLite checkpointer memory
    response_text = await chat_agent_manager.chat(user_text=user_text, chat_id=chat_id)

    # Split message if it exceeds Telegram limits
    chunks = split_telegram_message(response_text)
    for chunk in chunks:
        await update.message.reply_text(
            chunk,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )


# -------------------------------------------------------------
# Application Factory
# -------------------------------------------------------------

def build_application() -> Application:
    """Create and configure the python-telegram-bot Application."""
    token = settings.telegram_bot_token
    if not token or token == "your_telegram_bot_token_here":
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured in .env file.")

    app = ApplicationBuilder().token(token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("clear", clear_command))

    # Register message handler for follow-up conversational questions
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # Setup 9:10 AM IST scheduler
    setup_scheduler(app)

    return app

