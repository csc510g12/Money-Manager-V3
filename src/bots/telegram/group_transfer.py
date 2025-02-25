import re
import threading
from collections import namedtuple
from datetime import datetime
from uuid import uuid4

import requests
from loguru import logger
from pytz import timezone as pytz_timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bots.telegram.auth import authenticate, get_user, get_user_by_username
from bots.telegram.reply_handlers import ReplyWaiters
from bots.telegram.utils import extract_mentioned_usernames, wrap_text_for_markdown_v2
from config.config import TELEGRAM_BOT_API_BASE_URL, TIME_ZONE

API_TIMEOUT = 60

# Using the same ComplexUser tuple as in your private transfers
ComplexUser = namedtuple("ComplexUser", ["tg_username", "mm_user"])

# Global dictionary to track ongoing group transfer transactions per group chat
ONGOING_GROUP_TRANSFER_TRANSACTIONS = {}

# Timeout for each transaction (seconds)
TRANSACTION_TIMEOUT = 600

class GroupTransferTransaction:
    """
    Represents a group transfer transaction.
    
    Attributes:
      sender: The user initiating the transfer.
      recipients: Dictionary mapping each recipient's username to a dict holding their chosen account and confirmation status.
      sender_account: The account chosen by the sender (source account).
      amount: The transfer amount.
      currency: The currency (default: USD).
      timestamp: Transaction timestamp.
      identifier: Unique transaction ID.
      anchor_update: The original update that started the transaction.
    """
    def __init__(self, sender: ComplexUser, recipients: list, anchor_update: Update):
        self.sender = sender
        self.recipients = {username: {"account": None, "confirmed": False} for username in recipients}
        self.sender_account = None
        self.amount = None
        self.currency = "USD"
        self.timestamp = datetime.now(pytz_timezone(TIME_ZONE)).strftime("%Y-%m-%dT%H:%M:%S.%f")
        self.anchor_update = anchor_update
        self.identifier = str(uuid4())
        self.timeout_thread = threading.Timer(TRANSACTION_TIMEOUT, self.__del__)
        self.timeout_thread.start()

    def __del__(self):
        self.timeout_thread.cancel()

    @property
    def all_recipient_accounts_confirmed(self):
        return all(info["account"] is not None for info in self.recipients.values())

# ---------------------------------------------------------------------
# Step 1: Entry Point for Group Transfer
# ---------------------------------------------------------------------
@authenticate
async def group_transfer_entry(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> None:
    """
    Initiates a group transfer. The sender must mention one or more recipients.
    """
    group_id = update.message.chat_id
    if group_id in ONGOING_GROUP_TRANSFER_TRANSACTIONS:
        await update.message.reply_text("A group transfer is already in progress. Please complete or cancel it first.")
        return

    mentioned_users = await extract_mentioned_usernames(update, context, keep_at_symbol=False)
    mentioned_users = [user for user in mentioned_users if user != context.bot.username]
    if not mentioned_users:
        await update.message.reply_text("Please mention at least one recipient for the group transfer.")
        return

    sender_tg_id = update.effective_user.id
    sender_tg_name = update.effective_user.username
    sender = ComplexUser(
        tg_username=sender_tg_name,
        mm_user=await get_user(tg_user_id=sender_tg_id)
    )
    transaction = GroupTransferTransaction(sender=sender, recipients=mentioned_users, anchor_update=update)
    ONGOING_GROUP_TRANSFER_TRANSACTIONS[group_id] = transaction

    await update.message.reply_text(
        f"Group transfer initiated by @{sender.tg_username} to: {', '.join(mentioned_users)}.\nPlease enter the transfer amount."
    )
    # Set a reply waiter for the amount input.
    context.chat_data["group_transfer_amount_message_id"] = update.message.message_id
    ReplyWaiters[(group_id, update.message.message_id)] = group_transfer_amount_handler

# ---------------------------------------------------------------------
# Step 2: Handle Amount Input
# ---------------------------------------------------------------------
async def group_transfer_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the transfer amount input from the sender.
    """
    group_id = update.message.chat_id
    if group_id not in ONGOING_GROUP_TRANSFER_TRANSACTIONS:
        await update.message.reply_text("No active group transfer transaction.")
        return
    transaction = ONGOING_GROUP_TRANSFER_TRANSACTIONS[group_id]
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a valid number.")
        return

    transaction.amount = amount
    await update.message.reply_text(f"Amount set to {transaction.amount} {transaction.currency}.\nNow, please choose your source account:")

    # Prompt sender for source account selection.
    keyboard = [
        [
            InlineKeyboardButton("Checking", callback_data="group_source_Checking"),
            InlineKeyboardButton("Savings", callback_data="group_source_Savings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose your source account:", reply_markup=reply_markup)

# ---------------------------------------------------------------------
# Step 3: Handle Sender's Source Account Selection
# ---------------------------------------------------------------------
@authenticate
async def group_transfer_source_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> None:
    """
    Handles the sender's source account choice via inline button.
    """
    query = update.callback_query
    await query.answer()
    group_id = query.message.chat_id
    if group_id not in ONGOING_GROUP_TRANSFER_TRANSACTIONS:
        await query.message.reply_text("No active group transfer transaction.")
        return
    transaction = ONGOING_GROUP_TRANSFER_TRANSACTIONS[group_id]
    # Callback data format: "group_source_<Account>"
    account_choice = query.data.split("_", 2)[-1]
    transaction.sender_account = account_choice
    await query.edit_message_text(f"Your source account is set to {account_choice}.")

    # Now prompt each recipient to select their destination account.
    for recipient in transaction.recipients.keys():
        keyboard = [
            [
                InlineKeyboardButton("Checking", callback_data=f"group_dest_{recipient}_Checking"),
                InlineKeyboardButton("Savings", callback_data=f"group_dest_{recipient}_Savings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(f"@{recipient}, please select the account to receive funds:", reply_markup=reply_markup)

# ---------------------------------------------------------------------
# Step 4: Handle Recipient's Destination Account Selection
# ---------------------------------------------------------------------
@authenticate
async def group_transfer_recipient_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> None:
    """
    Handles a recipient's destination account choice.
    Expected callback data: "group_dest_<username>_<Account>"
    """
    query = update.callback_query
    await query.answer()
    group_id = query.message.chat_id
    if group_id not in ONGOING_GROUP_TRANSFER_TRANSACTIONS:
        await query.message.reply_text("No active group transfer transaction.")
        return
    transaction = ONGOING_GROUP_TRANSFER_TRANSACTIONS[group_id]
    data_parts = query.data.split("_")
    recipient_username = data_parts[2]
    account_choice = data_parts[3]
    if recipient_username not in transaction.recipients:
        await query.answer("You are not a participant in this transfer.")
        return
    transaction.recipients[recipient_username]["account"] = account_choice
    transaction.recipients[recipient_username]["confirmed"] = True
    await query.edit_message_text(f"@{recipient_username}, you selected {account_choice} as your destination account.")

    # If all recipients have chosen, send a final confirmation summary to the sender.
    if transaction.all_recipient_accounts_confirmed:
        recipient_details = "\n".join([f"@{user}: {info['account']}" for user, info in transaction.recipients.items()])
        summary = (
            f"Transfer Summary:\n"
            f"Sender: @{transaction.sender.tg_username} (Account: {transaction.sender_account})\n"
            f"Amount: {transaction.amount} {transaction.currency}\n"
            f"Recipients:\n{recipient_details}\n\n"
            "Do you confirm this group transfer?"
        )
        keyboard = [
            [
                InlineKeyboardButton("Confirm Transfer", callback_data=f"group_confirm_{transaction.identifier}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(summary, reply_markup=reply_markup)

# ---------------------------------------------------------------------
# Step 5: Final Confirmation and Processing
# ---------------------------------------------------------------------
@authenticate
async def group_transfer_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> None:
    """
    Handles the final confirmation for the group transfer and processes transfers for each recipient.
    """
    query = update.callback_query
    await query.answer()
    group_id = query.message.chat_id
    if group_id not in ONGOING_GROUP_TRANSFER_TRANSACTIONS:
        await query.message.reply_text("No active group transfer transaction.")
        return
    transaction = ONGOING_GROUP_TRANSFER_TRANSACTIONS[group_id]
    if not transaction.sender_account or not transaction.all_recipient_accounts_confirmed:
        await query.message.reply_text("Transfer is incomplete. Please ensure all account selections are made.")
        return

    try:
        sender_token = transaction.sender.mm_user["token"]
        transfer_results = []
        # Process a separate transfer for each recipient.
        for recipient, details in transaction.recipients.items():
            payload = {
                "source_account": transaction.sender_account,
                "destination_account": details["account"],
                "amount": transaction.amount,  # Adjust if you want different amounts per recipient.
            }
            response = requests.post(
                f"{TELEGRAM_BOT_API_BASE_URL}/transfers/",
                json=payload,
                headers={"token": sender_token},
                timeout=API_TIMEOUT,
            )
            if response.status_code == 200:
                transfer_results.append(f"Transfer to @{recipient} successful.")
            else:
                err = response.json().get("detail", "Unknown error")
                transfer_results.append(f"Transfer to @{recipient} failed: {err}")

        result_summary = "\n".join(transfer_results)
        await query.message.reply_text(f"Group Transfer Results:\n{result_summary}")
        del ONGOING_GROUP_TRANSFER_TRANSACTIONS[group_id]
    except Exception as e:
        logger.error(f"Error during group transfer: {e}")
        await query.message.reply_text(f"An error occurred during the transfer: {str(e)}")
