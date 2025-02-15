"""Main module for the Telegram bot."""

import logging
import os
import sys

from proto import Message
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

from api import app
from bots.telegram.accounts import accounts_handlers
from bots.telegram.analytics import analytics_handlers
from bots.telegram.auth import auth_handlers, get_user  # Update import
from bots.telegram.categories import categories_handlers
from bots.telegram.expenses import expenses_handlers
from bots.telegram.group_bill_split import bill_split_entry, confirm_bill_split
from bots.telegram.receipts import receipts_handlers  # New import
from bots.telegram.utils import (
    get_group_chat_menu_commands,
    get_private_chat_menu_commands,
    unknown,
)
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
            f"Welcome back, {username}!\n\n{get_private_chat_menu_commands()}"
        )
    else:
        await update.message.reply_text(
            "Welcome to Money Manager Telegram Bot!\nPlease /login or /signup to continue."
        )


async def private_chat_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /menu command."""
    await update.message.reply_text(get_private_chat_menu_commands())


async def group_chat_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles group chat messages where the bot is mentioned"""
    await update.message.reply_text(get_group_chat_menu_commands())


async def group_chat_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles group chat messages where the bot is mentioned"""
    chat = update.message.chat
    user = update.message.from_user
    text = update.message.text

    # Check if the bot is mentioned in the message
    if not context.bot.username in text:
        return

    print(
        f"User: {user.username} mentioned the bot in group chat: {chat.title}, message: {text}"
    )

    # if is menu command
    if "/menu" in text:
        await update.message.reply_text(get_group_chat_menu_commands())
        return
    # if is bill split command
    elif "/bill_split" in text:
        await bill_split_entry(update, context)
        return
    # if is unknown command
    else:
        await update.message.reply_text(
            f"Hello {user.first_name}, I saw you mentioned me in {chat.title}! If you need help, type /menu."
        )
        return


async def unknown(update: Update, context: CallbackContext):
    """Handles unknown commands"""
    await update.message.reply_text("I don't understand that command.")


def main() -> None:
    """Initialize and start the bot."""
    token = config.TELEGRAM_BOT_TOKEN
    application = Application.builder().token(token).build()

    # Register group chat handlers
    application.add_handler(
        MessageHandler(filters.ChatType.GROUP, group_chat_handler)
    )
    application.add_handler(
        CallbackQueryHandler(confirm_bill_split, pattern="^confirm_")
    )

    # Register private chat handlers
    application.add_handler(
        CommandHandler("start", start, filters.ChatType.PRIVATE)
    )
    application.add_handler(
        CommandHandler("menu", private_chat_menu, filters.ChatType.PRIVATE)
    )

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

    # Catch unknown commands (only for private chat)
    application.add_handler(
        CommandHandler("unknown", unknown, filters.ChatType.PRIVATE)
    )

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
