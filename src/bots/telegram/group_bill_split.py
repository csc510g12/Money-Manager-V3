from typing import Dict, List

from loguru import logger
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


class BillSplitTransaction:
    def __init__(self, mmuser_names: List[str], amount: float = None):
        self.confirmed_states = {name: False for name in mmuser_names}
        self.amount = amount


ONGOING_BILL_SPLIT_TRANSACTIONS = {
    int: BillSplitTransaction
}  # Dictionary to track ongoing transactions, group_id: BillSplitTransaction


@authenticate
async def bill_split_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Handle the /bill_split command."""
    group_id = update.message.chat_id

    if group_id in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await update.message.reply_text(
            "A bill split is already in progress in this group. Please complete or cancel it before starting a new one."
        )
        return

    mentioned_users = await extract_mentioned_usernames(
        update, context, keep_at_symbol=False
    )
    mentioned_users = [
        user for user in mentioned_users if user != f"@{context.bot.username}"
    ]

    if not mentioned_users:
        await update.message.reply_text(
            "Please mention the users to split the bill with."
        )
        return

    # Create a new bill split transaction
    ONGOING_BILL_SPLIT_TRANSACTIONS[group_id] = BillSplitTransaction(
        mentioned_users
    )

    await update.message.reply_text(
        f"Users that will be included in the bill split: {', '.join(mentioned_users)}"
    )

    # ask for amount
    amount_message = await update.message.reply_text(
        "Please tell me the amount to be split by replying to this message."
    )

    context.chat_data["amount_request_message_id"] = amount_message.message_id
    return  # Wait for user response before proceeding


async def bill_split_amount_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle user input for bill amount if it is a reply to the request."""
    group_id = update.message.chat_id

    logger.debug(
        f"Group ID: {group_id} - Message ID: {update.message.message_id}"
    )

    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await update.message.reply_text(
            "No active bill split transaction in this group."
        )
        return

    if (
        update.message.reply_to_message
        and update.message.reply_to_message.message_id
        == context.chat_data.get("amount_request_message_id")
    ):
        amount_text = update.message.text
        try:
            amount = float(amount_text)
        except ValueError:
            await update.message.reply_text(
                "Invalid amount. Please enter a valid number."
            )

        ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].amount = amount
        await update.message.reply_text(
            f"The bill amount is set to {amount:.2f}. Now waiting for confirmations."
        )
        mentioned_users = list(
            ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].confirmed_states.keys()
        )
        if not mentioned_users:
            await update.message.reply_text(
                "No users mentioned for the bill split."
            )
            return
        keyboard = [
            [
                InlineKeyboardButton(
                    f"Confirm - {user}",
                    callback_data=f"confirm_bill_split_{user}",
                )
            ]
            for user in mentioned_users
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Each mentioned user, please confirm your participation by clicking the button below:",
            reply_markup=reply_markup,
        )


async def confirm_bill_split(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle confirmation button clicks."""
    query = update.callback_query
    user = query.from_user
    mentioned_username = query.data.split("_", 1)[1].removeprefix(
        "bill_split_"
    )
    group_id = query.message.chat_id

    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await query.answer("No active bill split transaction in this group.")
        return

    transaction = ONGOING_BILL_SPLIT_TRANSACTIONS[group_id]

    # logger.debug(
    #     f"User: {user.username} tried to confirm bill split for {mentioned_username}, the states are {transaction.confirmed_states}"
    # )

    if user.username != mentioned_username:
        await query.answer("You can only confirm your own participation.")
        return

    if mentioned_username not in transaction.confirmed_states:
        await query.answer("You are not part of this bill split.")
        return

    mmuser = await get_user(tg_user_id=user.id)
    if not mmuser:
        await query.answer(
            "You need to be authenticated to confirm. Please send `/login` or `/signup` in private chat with the bot."
        )
        return

    transaction.confirmed_states[mentioned_username] = True

    await query.answer(f"Confirmed: {mentioned_username}")

    # Update button states by removing the confirmed user
    updated_keyboard = [
        [
            InlineKeyboardButton(
                f"Confirm - {user}", callback_data=f"confirm_bill_split_{user}"
            )
        ]
        for user, confirmed in transaction.confirmed_states.items()
        if not confirmed  # Only keep buttons for users who haven't confirmed
    ]

    reply_markup = (
        InlineKeyboardMarkup(updated_keyboard) if updated_keyboard else None
    )

    await query.edit_message_text(
        f"{mentioned_username} has confirmed participation!",
        reply_markup=reply_markup,
    )

    if all(transaction.confirmed_states.values()):
        await query.message.reply_text(
            "All users have confirmed. Proceeding with bill split."
        )
        # todo : proceed with all user's personal account
        del ONGOING_BILL_SPLIT_TRANSACTIONS[group_id]
