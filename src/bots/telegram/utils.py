"""Utility functions for the Telegram bot."""

import re

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config.config import TELEGRAM_SET_COMMAND_TEXT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current conversation and clear user data.

    Args:
        update: Update from Telegram
        context: CallbackContext for this update

    Returns:
        ConversationHandler.END to end the conversation
    """
    await update.message.reply_text("Operation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands."""
    await update.message.reply_text("Sorry, I didn't understand that command.")


def get_menu_commands() -> str:
    commands = TELEGRAM_SET_COMMAND_TEXT.strip().split("\n")
    grouped_commands = {
        "Helper Commands": {
            "pattern": re.compile(r"^(start|menu|cancel)$"),
            "commands": [],
        },
        "User Commands": {
            "pattern": re.compile(r"^(login|signup|logout)$"),
            "commands": [],
        },
        "Expense Commands": {"pattern": re.compile(r"^expenses_"), "commands": []},
        "Categories|Budget Commands": {
            "pattern": re.compile(r"^categories_"),
            "commands": [],
        },
        "Accounts Commands": {"pattern": re.compile(r"^accounts_"), "commands": []},
        "Other Commands": {"pattern": re.compile(r".*"), "commands": []},
    }

    for cmd in commands:
        if cmd:
            command, description = cmd.split(" - ")
            for group, data in grouped_commands.items():
                if data["pattern"].match(command):
                    data["commands"].append(f"/{command} - {description}")
                    break

    pretty_commands = ""
    for group, data in grouped_commands.items():
        if data["commands"]:
            if group == "Helper Commands":
                pretty_commands += "\n".join(data["commands"]) + "\n\n"
            else:
                pretty_commands += f"{group}:\n" + "\n".join(data["commands"]) + "\n\n"

    return f"Here are the available commands:\n\n{pretty_commands.strip()}"
