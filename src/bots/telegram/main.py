"""Main module for the Telegram bot."""

import logging
import os
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bots.telegram.accounts import accounts_handlers
from bots.telegram.analytics import analytics_handlers
from bots.telegram.auth import auth_handlers, get_user  # Update import
from bots.telegram.categories import categories_handlers
from bots.telegram.expenses import expenses_handlers
from bots.telegram.receipts import receipts_handlers  # New import
from bots.telegram.utils import get_menu_commands, unknown
from config import config

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user = await get_user(update=update)
    if user:
        username = user.get("username")
        await update.message.reply_text(
            f"Welcome back, {username}!\n\n{get_menu_commands()}"
        )
    else:
        await update.message.reply_text(
            "Welcome to Money Manager Telegram Bot!\nPlease /login or /signup to continue."
        )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /menu command."""
    await update.message.reply_text(get_menu_commands())


async def group_chat_handler(update: Update, context: CallbackContext):
    """Handles group chat messages where the bot is mentioned"""
    chat = update.message.chat
    user = update.message.from_user
    text = update.message.text

    if f"@{config.TELEGRAM_BOT_NAME}" in text:
        await update.message.reply_text(
            f"Hello {user.first_name}, you mentioned me in {chat.title}!"
        )


async def unknown(update: Update, context: CallbackContext):
    """Handles unknown commands"""
    await update.message.reply_text("I don't understand that command.")


def main() -> None:
    """Initialize and start the bot."""
    token = config.TELEGRAM_BOT_TOKEN
    application = Application.builder().token(token).build()

    # Register private chat handlers
    private_filter = filters.ChatType.PRIVATE
    application.add_handler(CommandHandler("start", start, private_filter))
    application.add_handler(CommandHandler("menu", menu, private_filter))

    # Add all your existing private chat handlers
    for handler in auth_handlers:
        application.add_handler(handler)
    for handler in expenses_handlers:
        application.add_handler(handler)
    for handler in categories_handlers:
        application.add_handler(handler)
    for handler in accounts_handlers:
        application.add_handler(handler)
    for handler in analytics_handlers:
        application.add_handler(handler)

    # Register group chat handler (bot mention only)
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & filters.Regex(f"@{config.TELEGRAM_BOT_NAME}"),
            group_chat_handler,
        )
    )

    # Catch unknown commands (only for private chat)
    application.add_handler(CommandHandler("unknown", unknown, private_filter))

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
