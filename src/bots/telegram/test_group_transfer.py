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

from bots.telegram.auth import authenticate, get_user
from bots.telegram.reply_handlers import ReplyWaiters
from bots.telegram.utils import (
    extract_mentioned_usernames,
    wrap_text_for_markdown_v2,
)
from config.config import TELEGRAM_BOT_API_BASE_URL

ONGOING_TRANSFER: Dict[
    int, "TransferTransaction"
] = (
    {}
)

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
        if self.idnetifier in self.__class__.TIMEOUT_THREADS:
            self.__class__.TIMEOUT_THREADS[self.identifier].cancel()
            del self.__class__.TIMEOUT_THREADS[self.identifier]

    def __init__(
        self,
        issuer: ComplexUser = None,
        recipient: ComplexUser = None,
        amount: float = None
        anchor_update = None
    ):
        self.issuer = issuer
        self.recipient = recipient
        self.amount = amount
        self.identifier = str(uuid4())

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
    issuer = ComplexUser(
        tg_username=issuer_tg_name,
        mm_user=await get_user(tg_user_id=issuer_tg_id),
    )

    transfer = TransferTransaction(
        recipient = {tg_username: {} for tg_username in mentioned_users},
        issuer=issuer,
        anchor_update = update,
    )

    ONGOING_TRANSFER[group_id] = transfer
    await update.message.reply_text(
        f"Users that will be included in the transfer: @{', @'.join(mentioned_users)}"
    )

    amount = await update.message.reply_text(
        "Please enter the amount to transfer."
    )

    context.chat_data["amount_message_id"] = amount.message_id
    ReplyWaiters[
        (group_id, amount.message_id)
    ] = # Create transfer method later