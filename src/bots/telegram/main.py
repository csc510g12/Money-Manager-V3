"""Main module for the Telegram bot."""

import logging
import os
import sys
from ast import Call

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
from bots.telegram.group_bill_split import (
    bill_split_category_selection_handler,
    bill_split_currency_selection_handler,
    bill_split_entry,
    bill_split_proceed_handler,
    bill_split_status_handler,
    cancel_bill_split_handler,
    confirm_bill_split_callback_handler,
)
from bots.telegram.group_transfer import (
    cancel_transfer_handler,
    confirm_transfer_handler,
    group_transfer_entry,
    transfer_currency_selection_handler,
)
from bots.telegram.receipts import receipts_handlers  # New import
from bots.telegram.reply_handlers import reply_handler
from bots.telegram.transfers import transfer_conv_handler
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

    # if its a reply message
    if update.message.reply_to_message:
        # get chat id and message id of the replied message
        await reply_handler(update=update, context=context)

    # Check if the bot is mentioned in the message
    if not context.bot.username in text:
        return

    # if is menu command
    if "/menu" in text:
        await update.message.reply_text(get_group_chat_menu_commands())
        return
    # if is bill split proceed command
    elif "/bill_split_proceed" in text:
        await bill_split_proceed_handler(update, context)
        return
    # if is bill split proceed command
    elif "/bill_split_status" in text:
        await bill_split_status_handler(update, context)
        return
    # if is bill split command
    elif "/bill_split" in text:
        await bill_split_entry(update, context)
        return
    elif "/transfer" in text:
        await group_transfer_entry(update, context)
        return
    # if is cancel command
    elif "/cancel_bill_split" in text:
        await cancel_bill_split_handler(update, context)
        return
    elif "/cancel_transfer" in text:
        await cancel_transfer_handler(update, context)
        return
    # if is unknown command
    else:
        await update.message.reply_text(
            f"Hello {user.first_name}, I saw you mentioned me in {chat.title}! If you need help, please mention me with command /menu for available commands."
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
        MessageHandler(filters.ChatType.GROUP, group_chat_handler)
    )
    application.add_handler(
        CallbackQueryHandler(
            confirm_bill_split_callback_handler, pattern="^confirm_bill_split_"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            bill_split_currency_selection_handler,
            pattern="^currency_bill_split_",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            bill_split_category_selection_handler,
            pattern="^category_bill_split_",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            transfer_currency_selection_handler, pattern="^currency_transfer_"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            confirm_transfer_handler, pattern="^confirm_transfer_"
        )
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

    # Transfer conversation handler
    application.add_handler(transfer_conv_handler)

    # Catch unknown commands (only for private chat)
    application.add_handler(
        CommandHandler("unknown", unknown, filters.ChatType.PRIVATE)
    )

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
