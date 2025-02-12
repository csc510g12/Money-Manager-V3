"""Main module for the Telegram bot."""

import logging
import os
import sys

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
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


def main() -> None:
    """Initialize and start the bot."""
    token = config.TELEGRAM_BOT_TOKEN
    application = Application.builder().token(token).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))

    # Add auth handlers
    for handler in auth_handlers:
        application.add_handler(handler)

    # Add expenses handlers
    for handler in expenses_handlers:
        application.add_handler(handler)

    # Add categories handlers
    for handler in categories_handlers:
        application.add_handler(handler)
    # Add categories handlers
    for handler in accounts_handlers:
        application.add_handler(handler)
    for handler in analytics_handlers:
        application.add_handler(handler)

    application.add_handler(CommandHandler("unknown", unknown))

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
