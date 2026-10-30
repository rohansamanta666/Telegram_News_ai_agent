"""Security and authorization decorator for Telegram bot handlers."""

import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import settings

logger = logging.getLogger(__name__)


def restricted(func):
    """Decorator ensuring only authorized Telegram chat IDs can invoke the bot."""
    @functools.wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        chat_id = update.effective_chat.id if update.effective_chat else None
        allowed_ids = settings.allowed_chat_ids_list

        # If no allowed IDs configured in .env, allow for initial onboarding
        if not allowed_ids:
            return await func(update, context, *args, **kwargs)

        if chat_id not in allowed_ids and user_id not in allowed_ids:
            logger.warning(
                f"Unauthorized access attempt from user_id={user_id}, chat_id={chat_id}. "
                f"Allowed IDs: {allowed_ids}"
            )
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⛔ <b>Access Denied</b>\n"
                    "This is a private AI News Bot restricted to its owner.\n"
                    f"Your Chat ID is: <code>{chat_id}</code>\n"
                    "Please add this ID to <code>TELEGRAM_ALLOWED_CHAT_IDS</code> in <code>.env</code>.",
                    parse_mode="HTML"
                )
            return

        return await func(update, context, *args, **kwargs)

    return wrapped

