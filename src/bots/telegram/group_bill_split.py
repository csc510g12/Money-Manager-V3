from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bots.telegram.auth import authenticate, get_user
from bots.telegram.utils import cancel, extract_mentioned_usernames


@authenticate
async def bill_split_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Handle the /bill_split command."""

    mentioned_users = await extract_mentioned_usernames(update, context)
    # remove the bot itself from the list of mentioned users
    mentioned_users = [
        user for user in mentioned_users if user != f"@{context.bot.username}"
    ]

    if not mentioned_users:
        await update.message.reply_text(
            "Please mention the users to split the bill with."
        )
        return
    else:
        await update.message.reply_text(
            f"Users that will be included in the bill split: {', '.join(mentioned_users)}"
        )

        # Create inline keyboard buttons for each mentioned user
        keyboard = [
            [
                InlineKeyboardButton(
                    f"Confirm - {user}", callback_data=f"confirm_{user}"
                )
            ]
            for user in mentioned_users
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send message with inline keyboard
        await update.message.reply_text(
            "Each mentioned user, please confirm your participation by clicking the button below:",
            reply_markup=reply_markup,
        )


# Callback handler for button clicks
async def confirm_bill_split(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle confirmation button clicks."""
    query = update.callback_query
    user = query.from_user  # The user who clicked the button
    mentioned_username = query.data.split("_", 1)[
        1
    ]  # Extract mentioned username

    # todo : Store the confirmation in a context
    if "confirmed_users" not in context.chat_data:
        context.chat_data["confirmed_users"] = {}
    context.chat_data["confirmed_users"][mentioned_username] = user.id
    # todo : after all users confirm, proceed with the bill split logic

    # Acknowledge the button press
    await query.answer(f"Confirmed: {mentioned_username}")

    # Notify the group or update the message
    # todo : Notify the bill split creator or the group, this requires a bill split pull to manage it per group
    await query.edit_message_text(
        f"{mentioned_username} has confirmed participation!"
    )
