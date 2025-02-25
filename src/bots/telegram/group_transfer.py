import re
import threading
from collections import namedtuple
from datetime import datetime, timedelta
from typing import Dict, List, NamedTuple, Union
from uuid import uuid4

import requests
from loguru import logger
from matplotlib.pylab import f
from pytz import timezone as pytz_timezone
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from bots.telegram.auth import authenticate, get_user
from bots.telegram.reply_handlers import ReplyWaiters
from bots.telegram.utils import (
    extract_mentioned_usernames,
    wrap_text_for_markdown_v2,
)
from config.config import TELEGRAM_BOT_API_BASE_URL

ONGOING_TRANSFER: Dict[int, "TransferTransaction"] = {}

API_TIMEOUT = 10
TRANSACTION_TIMEOUT = 600

(
    TRANSFER_SOURCE,
    TRANSFER_DESTINATION,
    TRANSFER_AMOUNT,
    TRANSFER_CONFIRM,
) = range(4)

ComplexUser = namedtuple("ComplexUser", ["tg_username", "mm_user"])


class TransferTransaction:
    """
    Class to represent a transfer.

    Attributes:
    """

    TIMEOUT_THREADS = {str: threading.Timer}

    def __del__(self):
        """Destructor to cancel transaction"""
        if self.identifier in self.__class__.TIMEOUT_THREADS:
            self.__class__.TIMEOUT_THREADS[self.identifier].cancel()
            del self.__class__.TIMEOUT_THREADS[self.identifier]

    def __init__(
        self,
        issuer: ComplexUser = None,
        recipient: ComplexUser = None,
        amount: float = None,
        currency=None,
        anchor_update=None,
    ):
        self.issuer = issuer
        self.recipient = recipient
        self.amount = amount
        self.identifier = str(uuid4())
        self.currency = currency
        self.category = "Transfer"
        if isinstance(recipient, dict):
            self.confirmed_states = {name: False for name in recipient.keys()}
        elif isinstance(recipient, list):
            self.confirmed_states = {name: False for name in recipient}
        elif isinstance(recipient, ComplexUser):
            self.confirmed_states = {recipient.tg_username: False}
        self.anchor_update: Update = anchor_update

        # start the timeout thread
        self.__class__.TIMEOUT_THREADS[self.identifier] = threading.Timer(
            TRANSACTION_TIMEOUT, self.__del__
        )
        self.__class__.TIMEOUT_THREADS[self.identifier].start()

    @property
    def json(self):
        return {
            "id": self.identifier,
            "amount": self.amount,
            "issuer": self.issuer,
            "recipient": self.recipient,
        }


@authenticate
async def group_transfer_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Entry point for the group transfer"""

    group_id = update.message.chat_id

    if group_id in ONGOING_TRANSFER:
        await update.message.reply_text(
            "A transfer is already in progress in this group. Please complete or cancel it before starting a new one."
        )
        return

    mentioned_users = await extract_mentioned_usernames(
        update, context, keep_at_symbol=False
    )
    mentioned_users = [
        user for user in mentioned_users if user != f"{context.bot.username}"
    ]

    if not mentioned_users:
        await update.message.reply_text(
            "Please mention the user you want to begin a transfer with."
        )
        return

    issuer_tg_id = update.effective_user.id
    issuer_tg_name = update.effective_user.username

    if len(mentioned_users) > 1:
        await update.message.reply_text(
            f"You can only transfer to one user at a time, but you specified {len(mentioned_users)} users."
        )
        return

    transfer = TransferTransaction(
        recipient=ComplexUser(tg_username=mentioned_users[0], mm_user=None),
        issuer=ComplexUser(
            tg_username=issuer_tg_name,
            mm_user=await get_user(tg_user_id=issuer_tg_id),
        ),
        anchor_update=update,
    )

    ONGOING_TRANSFER[group_id] = transfer
    await update.message.reply_text(
        f"You will transfer to: @{', @'.join(mentioned_users)}"
    )

    amount_message = await update.message.reply_text(
        "Please enter the amount to transfer by replying to this message."
    )

    context.chat_data["amount_message_id"] = amount_message.message_id
    ReplyWaiters[
        (group_id, amount_message.message_id)
    ] = transfer_amount_handler
    return


async def transfer_amount_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the amount to be transferred between users"""

    group_id = update.message.chat_id
    if group_id not in ONGOING_TRANSFER:
        await update.message.reply_text("No active transfer in this group.")
        return

    if (
        update.message.from_user.id
        != ONGOING_TRANSFER[group_id].issuer.mm_user["telegram_id"]
    ):
        await update.message.reply_text(
            "You are not the owner of this transfer."
        )
        raise ValueError(
            "User who replied to the message is not the owner of the transfer."
        )

    if (
        update.message.reply_to_message
        and update.message.reply_to_message.message_id
        == context.chat_data.get("amount_message_id")
    ):
        amount_text = update.message.text
        try:
            amount = float(amount_text)
        except ValueError as e:
            await update.message.reply_text(
                "Invalid amount. Please neter a valid number."
            )
            raise e

    ONGOING_TRANSFER[group_id].amount = amount

    await show_select_currency(
        update, context
    )  # Show available currencies to the user


@authenticate
async def show_select_currency(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Show the available currencies to the user for the transfer.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.
        token (str): The user token.

    Returns:
        None

    Behavior:
        1. Check if the user is the issuer of the transfer.
        2. Fetch the available currencies from the API.
        3. Show the available currencies to the user.
    """

    # check if the user is the issuer of the transfer
    group_id = update.message.chat_id
    if group_id not in ONGOING_TRANSFER:
        await update.message.reply_text(
            "No active transfer transaction in this group."
        )
        return
    if (
        update.message.from_user.id
        != ONGOING_TRANSFER[group_id].issuer.mm_user["telegram_id"]
    ):
        await update.message.reply_text(
            "You are not the issuer of this transfer."
        )
        return

    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/users/",
        headers=headers,
        timeout=API_TIMEOUT,
    )
    if response.status_code == 200:
        currencies = response.json().get("currencies", [])
        if not currencies:
            await update.callback_query.message.edit_text(
                "No currencies found."
            )
            return

    # Show available currencies to the user
    keyboard = [
        [
            InlineKeyboardButton(
                currency, callback_data=f"currency_transfer_{currency}"
            )
        ]
        for currency in currencies
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select the currency for the transfer from the list below:",
        reply_markup=reply_markup,
    )


async def transfer_currency_selection_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle currency selection for transfer.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        None

    Behavior:
        1. Check if the user is the issuer of the transfer.
        2. Extract the selected currency.
        3. Store the selected currency in the transfer transaction.
        4. Ask for the category to be used for the transaction.
        5. Wait for the user response before proceeding.
    """
    query = update.callback_query
    group_id = query.message.chat_id

    if group_id not in ONGOING_TRANSFER:
        await query.answer("No active transfer transaction in this group.")
        return

    # check if the user is the issuer of the transfer
    if (
        query.from_user.id
        != ONGOING_TRANSFER[group_id].issuer.mm_user["telegram_id"]
    ):
        await query.answer("You are not the issuer of this transfer.")
        return

    selected_currency = query.data.removeprefix("currency_transfer_")
    ONGOING_TRANSFER[group_id].currency = selected_currency

    await show_confirm_transaction(update, context)


async def show_confirm_transaction(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Displays a confirmation message for users in transfer to accept"""

    chat_id = update.callback_query.message.chat_id

    await update.callback_query.message.reply_text(
        f"The amount to be transfer: {ONGOING_TRANSFER[chat_id].amount} {ONGOING_TRANSFER[chat_id].currency}. "
        + "Please confirm the transfer."
    )
    mentioned_users = list(ONGOING_TRANSFER[chat_id].confirmed_states.keys())
    if not mentioned_users:
        await update.callback_query.message.reply_text(
            "No users mentioned for the transfer."
        )
        return
    keyboard = [
        [
            InlineKeyboardButton(
                f"Confirm - {user}", callback_data=f"confirm_transfer_{user}"
            )
        ]
        for user in mentioned_users
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        "Each user please confirm the transfer.",
        reply_markup=reply_markup,
    )


async def confirm_transfer_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles the transfer confirmation"""
    query = update.callback_query
    group_id = query.message.chat_id
    user = query.from_user
    mentioned_username = query.data.split("_", 1)[1].removeprefix("transfer_")

    if group_id not in ONGOING_TRANSFER:
        await query.answer("No active transfer in this group.")
        return

    transfer = ONGOING_TRANSFER[group_id]

    if user.username != mentioned_username:
        await query.answer("You can only confirm yourself.")

    if mentioned_username not in transfer.confirmed_states:
        await query.answer("You are not part of this transfer.")

    mmuser = await get_user(tg_user_id=user.id)
    if not mmuser:
        await query.answer(
            "You need to be authenticated to confirm. Please send `/login` or `/signup` in private chat with the bot."
        )
        return

    if mentioned_username != transfer.recipient.tg_username:
        await query.answer("Only the recipient can confirm the transfer.")
        return

    transfer.confirmed_states[mentioned_username] = True
    transfer.recipient = ComplexUser(
        tg_username=mentioned_username, mm_user=mmuser
    )

    await query.answer(f"Confirmed: {mentioned_username}")

    updated_keyboard = [
        [
            InlineKeyboardButton(
                f"Confirm - {user}", callback_data=f"conrim_transfer_{user}"
            )
        ]
        for user, confirmed in transfer.confirmed_states.items()
        if not confirmed
    ]

    reply_markup = (
        InlineKeyboardMarkup(updated_keyboard) if updated_keyboard else None
    )

    await query.edit_message_text(
        f"{mentioned_username} has confirmed.",
        reply_markup=reply_markup,
    )

    if all(transfer.confirmed_states.values()):
        await transfer_handler(
            update, context, check_status=False, group_id=group_id
        )


@authenticate
async def transfer_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    check_status: bool = True,
    group_id=None,
    token: str = None,
) -> None:
    """Handles the transfer process"""

    group_id = group_id or update.message.chat_id

    if group_id not in ONGOING_TRANSFER:
        await update.message.reply_text("No active transfer in this group.")
        return

    transaction = ONGOING_TRANSFER[group_id]
    update = update if check_status else transaction.anchor_update

    if check_status:
        if (
            update.message.from_user.id
            != ONGOING_TRANSFER[group_id].issuer.mm_user["telegram_id"]
        ):
            await update.message.reply_text(
                "You are not the owner of this transfer."
            )
            return

    try:
        await process_transfer(group_id, transaction)
        assert (
            group_id not in ONGOING_TRANSFER
        ), "Transfer not deleted after processing"
        await update.message.reply_text(
            f"Transfer has been successfully processed.\n"
            f"💵 Amount: {transaction.amount} {transaction.currency}\n"
            f"To: @{transaction.recipient.tg_username}"
        )
    except Exception as e:
        logger.error(f"Error while processing Transfer: {e}")
        # reply with status
        await transfer_status_handler(update, context, token)
        # reply with error message
        reply_message = f"An error occurred while processing the transfer :\n"
        reply_message = re.sub(r"\.", r"\\.", reply_message)
        await update.message.reply_text(reply_message, parse_mode="MarkdownV2")
        return


async def process_transfer(
    group_id: int, transaction: TransferTransaction
) -> None:
    try:
        # Ensure that all participants have confirmed.
        assert all(
            transaction.confirmed_states.values()
        ), "Not all participants have confirmed"

        recipient_tg_username, recipient_data = transaction.recipient
        print(recipient_tg_username, recipient_data)
        issuer_tg_username, issuer_data = transaction.issuer
        if not recipient_data or "_id" not in recipient_data:
            raise ValueError(
                f"Recipient @{recipient_tg_username} has not properly confirmed the transfer."
            )

        def get_accounts_with_currency(transaction, recipient_data):
            headers = {"token": recipient_data["token"]}
            response = requests.get(
                f"{TELEGRAM_BOT_API_BASE_URL}/accounts/",
                headers=headers,
                timeout=API_TIMEOUT,
            )
            if response.status_code == 200:
                accounts_list = response.json().get("accounts", [])
                if not accounts_list:
                    raise ValueError(
                        # f"Participant {participant} has no accounts."
                        "Some participants have no accounts."  # for privacy reasons, do not show the participant
                    )
                # Check if any account has the target currency
                if not any(
                    account["currency"] == transaction.currency
                    for account in accounts_list
                ):
                    raise ValueError(
                        f"Some participant has no account with currency {transaction.currency}."
                    )
            else:
                raise ValueError(
                    "Failed to fetch accounts for some participants."  # for privacy reasons, do not show the participant
                )
            # Return the accounts with the target currency
            return [
                account
                for account in accounts_list
                if account["currency"] == transaction.currency
            ]

        # Get the accounts of the recipient
        recipient_accounts = get_accounts_with_currency(
            transaction, recipient_data
        )
        # Get the accounts of the issuer
        issuer_accounts = get_accounts_with_currency(transaction, issuer_data)

        # Check if all participants have enough balance in corresponding accounts
        def get_accounts_with_enough_balance(accounts):
            if all(
                account["balance"] < transaction.amount for account in accounts
            ):
                logger.error(
                    f"Participant tg user @{recipient_tg_username} does not have enough {transaction.currency} balance in their accounts."
                )
                raise ValueError(
                    # f"Participant {tg_username} does not have enough balance in their accounts."
                    f"Some participants do not have enough {transaction.currency} balance in their accounts."  # for privacy reasons, do not show the participant
                )
            else:
                # only store the first account with enough balance
                account_with_enough_balance = [
                    account
                    for account in accounts
                    if account["balance"] >= transaction.amount
                ][0]
                logger.debug(
                    f"Using account {account_with_enough_balance} for participant tg user @{recipient_tg_username}."
                )
                return account_with_enough_balance

        recipient_account = recipient_accounts[0]  # only one account
        issuer_account = get_accounts_with_enough_balance(issuer_accounts)

        # Perform the transfer, reduce the balance of the issuer and increase the balance of the recipient
        try:
            # get old balance of the issuer
            old_balance = issuer_account["balance"]
            # update the balance of the issuer
            headers = {"token": issuer_data["token"]}
            response = requests.put(
                f"{TELEGRAM_BOT_API_BASE_URL}/accounts/{issuer_account['_id']}",
                json={"balance": str(old_balance - transaction.amount)},
                headers=headers,
                timeout=API_TIMEOUT,
            )
            if response.status_code != 200:
                raise ValueError(
                    # f"Failed to update balance of issuer @{issuer_tg_username}."
                    "Failed to update balance of some participants."  # for privacy reasons, do not show the participant
                )

            # get old balance of the recipient
            old_balance = recipient_account["balance"]
            # update the balance of the recipient
            headers = {"token": recipient_data["token"]}
            response = requests.put(
                f"{TELEGRAM_BOT_API_BASE_URL}/accounts/{recipient_account['_id']}",
                json={"balance": str(old_balance + transaction.amount)},
                headers=headers,
                timeout=API_TIMEOUT,
            )
            if response.status_code != 200:
                raise ValueError(
                    # f"Failed to update balance of recipient @{recipient_tg_username}."
                    "Failed to update balance of some participants."  # for privacy reasons, do not show the participant
                )
        except Exception as e:
            raise e

        # Finally, remove the transaction.
        del ONGOING_TRANSFER[group_id]

    except Exception as e:
        raise e


async def transfer_status_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Status of the transfer"""
    group_id = update.message.chat_id

    if group_id not in ONGOING_TRANSFER:
        await update.message.reply_text(
            "No active transfer transaction in this group."
        )
        return

    transaction = ONGOING_TRANSFER[group_id]

    reply_text = ""
    reply_text += f"💵 Amount: {transaction.amount or 'Unknown'} with currency {transaction.currency or 'Unknown'}\n"
    reply_text += f"Created by @{transaction.issuer.tg_username}`\n"
    # confirm states
    reply_text += "\nConfirmation Status:\n"
    for user, confirmed in transaction.confirmed_states.items():
        reply_text += wrap_text_for_markdown_v2(
            f"👤 @{user}: {'Confirmed ✅' if confirmed else 'Not Confirmed ❌'}\n"
        )

    reply_text += wrap_text_for_markdown_v2(
        "If you want to proceed with the transfer, please mention me with command /transfer_proceed \n"
    )

    reply_text = reply_text = re.sub(r"\.", r"\\.", reply_text)
    await update.message.reply_text(reply_text, parse_mode="MarkdownV2")


async def cancel_transfer_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Cancel the transfer"""
    group_id = update.message.chat_id

    if group_id not in ONGOING_TRANSFER:
        await update.message.reply_text("No active transfer in this group.")
        return

    if group_id in ONGOING_TRANSFER:
        # check if the issuer of cancel command is the same user who initiated the transfer
        if (
            update.message.from_user.id
            != ONGOING_TRANSFER[group_id].issuer.mm_user["telegram_id"]
        ):
            await update.message.reply_text(
                "You are not the ownver of this transfer."
            )
            return

        del ONGOING_TRANSFER[group_id]
        await update.message.reply_text("Transfer process has been canceled.")
    else:
        await update.message.reply_text("No active transfers to cancel.")
