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
from config.config import TELEGRAM_BOT_API_BASE_URL, TIME_ZONE

API_TIMEOUT = 10  # seconds
TRANSACTION_TIMEOUT = 600  # seconds

ComplexUser = namedtuple("ComplexUser", ["tg_username", "mm_user"])

ONGOING_BILL_SPLIT_TRANSACTIONS: Dict[
    int, "BillSplitTransaction"
] = (
    {}
)  # Dictionary to track ongoing transactions, group_id: BillSplitTransaction


class BillSplitTransaction:
    """Class to represent a bill split transaction.

    Attributes:
        participants (Dict[str, Union[Dict, None]]): The participants in the bill split transaction.
        issuer (ComplexUser): The user who initiated the bill split.
        amount (float): The amount to be split.
        category (str): The category of the transaction.
        currency (str): The currency of the transaction.
        timestamp (str): The timestamp of the transaction.
        description (str): The description of the transaction.
        anchor_update (Update): The corresponding update in tg group chat.
        identifier (str): The unique identifier for the transaction.
    """

    # class properties
    TIMEOUT_THREADS = {str: threading.Timer}  # identifier: Timer

    def __del__(self):
        """Destructor to cancel the timeout thread if it exists."""
        if self.identifier in self.__class__.TIMEOUT_THREADS:
            self.__class__.TIMEOUT_THREADS[self.identifier].cancel()
            del self.__class__.TIMEOUT_THREADS[self.identifier]

    def __init__(
        self,
        participants: Dict[str, Union[Dict, None]],
        issuer: ComplexUser = None,
        amount: float = None,
        category=None,
        currency=None,
        timestamp=datetime.now(pytz_timezone(TIME_ZONE)).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        ),
        description="Bill Split",
        anchor_update=None,
    ):
        """Initialize the BillSplitTransaction object.

        Args:
            participants (Dict[str, Union[Dict, None]]): The participants in the bill split transaction.
            issuer (ComplexUser, optional): issuer of the bill split. Defaults to None.
            amount (float, optional): The amount to be split. Defaults to 0.0.
            category (str, optional): The category of the transaction. Defaults to "Bill Split".
            currency (str, optional): The currency of the transaction. Defaults to "USD".
            timestamp (_type_, optional): The timestamp of the transaction. Defaults to current time.
            description (str, optional): The description of the transaction. Defaults to "Bill Split".
            anchor_update (_type_, optional): The corresponding update in tg group chat. Defaults to None.
        """
        self.issuer = issuer  # the user who initiated the bill split
        self.participants = participants
        self.confirmed_states = (
            {name: False for name in participants.keys()}
            if isinstance(participants, dict)
            else {name: False for name in participants}
        )
        self.amount = amount
        self.category = category
        self.currency = currency
        self.timestamp = timestamp
        self.description = description
        self.anchor_update: Update = (
            anchor_update  # Placeholder for the update object
        )
        self.identifier = str(uuid4())  # Unique identifier for the transaction

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
            "description": self.description,
            "category": self.category,
            "currency": self.currency,
            "date": self.timestamp,
            "issuer": self.issuer,
            "participants": self.participants,
            "confirmed_states": self.confirmed_states,
        }


@authenticate
async def bill_split_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Entry point for the bill split process.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.
        token (str): The user token.

    Raises:
        ValueError: If the user is not the issuer of the bill split.

    Returns:
        None

    Behavior:
        1. Check if there is an ongoing bill split transaction in the group.
        2. Extract the mentioned users.
        3. Create a new bill split transaction.
        4. Ask for the amount to be split.
        5. Wait for the user response before proceeding.
    """
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
        user for user in mentioned_users if user != f"{context.bot.username}"
    ]

    if not mentioned_users:
        await update.message.reply_text(
            "Please mention the users to split the bill with."
        )
        return

    # issuer of the bill split
    issuer_tg_id = update.effective_user.id
    issuer_tg_name = update.effective_user.username
    issuer = ComplexUser(
        tg_username=issuer_tg_name,
        mm_user=await get_user(tg_user_id=issuer_tg_id),
    )

    # Create a new bill split transaction
    transaction = BillSplitTransaction(
        participants={tg_username: {} for tg_username in mentioned_users},
        issuer=issuer,
        anchor_update=update,
    )
    ONGOING_BILL_SPLIT_TRANSACTIONS[group_id] = transaction
    await update.message.reply_text(
        f"Transaction `{transaction.identifier}` has been created",
        parse_mode="MarkdownV2",
    )
    await update.message.reply_text(
        f"Users that will be included in the bill split: @{', @'.join(mentioned_users)}"
    )

    # ask for amount
    amount_message = await update.message.reply_text(
        "Please tell me the amount to be split by replying to this message."
    )

    context.chat_data["amount_request_message_id"] = amount_message.message_id
    ReplyWaiters[
        (group_id, amount_message.message_id)
    ] = bill_split_amount_handler
    return  # Wait for user response before proceeding


async def bill_split_amount_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the amount to be split for the bill split transaction.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Raises:
        ValueError: If the user is not the issuer of the bill split.
        e: If the amount entered is invalid.

    Returns:
        None

    Behavior:
        1. Check if the user is the issuer of the bill split.
        2. Extract the amount from the user response.
        3. Store the amount in the bill split transaction.
        4. Ask for the currency to be used for the transaction.
        5. Wait for the user response before
    """
    group_id = update.message.chat_id

    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await update.message.reply_text(
            "No active bill split transaction in this group."
        )
        return

    # check if the replier is the same user who initiated the bill split
    if (
        update.message.from_user.id
        != ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].issuer.mm_user[
            "telegram_id"
        ]
    ):
        await update.message.reply_text(
            "You are not the issuer of this bill split."
        )
        raise ValueError(
            "The user who replied to the message is not the issuer of the bill split."
        )

    if (
        update.message.reply_to_message
        and update.message.reply_to_message.message_id
        == context.chat_data.get("amount_request_message_id")
    ):
        amount_text = update.message.text
        try:
            amount = float(amount_text)
        except ValueError as e:
            await update.message.reply_text(
                "Invalid amount. Please enter a valid number."
            )
            raise e  # raise to external handler

        ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].amount = amount

        await show_select_currency(
            update, context
        )  # Show available currencies to the user


@authenticate
async def show_select_currency(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Show the available currencies to the user for the bill split.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.
        token (str): The user token.

    Returns:
        None

    Behavior:
        1. Check if the user is the issuer of the bill split.
        2. Fetch the available currencies from the API.
        3. Show the available currencies to the user.
    """

    # check if the user is the issuer of the bill split
    group_id = update.message.chat_id
    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await update.message.reply_text(
            "No active bill split transaction in this group."
        )
        return
    if (
        update.message.from_user.id
        != ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].issuer.mm_user[
            "telegram_id"
        ]
    ):
        await update.message.reply_text(
            "You are not the issuer of this bill split."
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
                currency, callback_data=f"currency_bill_split_{currency}"
            )
        ]
        for currency in currencies
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select the currency for the bill split from the list below:",
        reply_markup=reply_markup,
    )


async def bill_split_currency_selection_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle currency selection for bill split.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        None

    Behavior:
        1. Check if the user is the issuer of the bill split.
        2. Extract the selected currency.
        3. Store the selected currency in the bill split transaction.
        4. Ask for the category to be used for the transaction.
        5. Wait for the user response before proceeding.
    """
    query = update.callback_query
    group_id = query.message.chat_id

    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await query.answer("No active bill split transaction in this group.")
        return

    # check if the user is the issuer of the bill split
    if (
        query.from_user.id
        != ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].issuer.mm_user[
            "telegram_id"
        ]
    ):
        await query.answer("You are not the issuer of this bill split.")
        return

    selected_currency = query.data.removeprefix("currency_bill_split_")
    ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].currency = selected_currency

    await show_select_category(update, context)


@authenticate
async def show_select_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Show the available categories to the user for the bill split.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.
        token (str): The user token.

    Returns:
        None

    Behavior:
        1. Check if the user is the issuer of the bill split.
        2. Fetch the available categories from the API.
        3. Show the available categories to the user
    """
    query = update.callback_query
    group_id = query.message.chat_id

    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await query.answer("No active bill split transaction in this group.")
        return

    # check if the user is the issuer of the bill split
    if (
        query.from_user.id
        != ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].issuer.mm_user[
            "telegram_id"
        ]
    ):
        await query.answer("You are not the issuer of this bill split.")
        return

    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/categories/",
        headers=headers,
        timeout=API_TIMEOUT,
    )
    if response.status_code == 200:
        categories = response.json().get("categories", [])
        if not categories:
            message = "No categories found."
            if update.message:
                await query.answer(message)
            elif update.callback_query:
                await update.callback_query.message.edit_text(message)
            return

    # Show available categories to the user
    keyboard = [
        [
            InlineKeyboardButton(
                category, callback_data=f"category_bill_split_{category}"
            )
        ]
        for category in categories
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await ONGOING_BILL_SPLIT_TRANSACTIONS[
        group_id
    ].anchor_update.message.reply_text(
        "Please select the category for the bill split from the list below:",
        reply_markup=reply_markup,
    )


async def bill_split_category_selection_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle category selection for bill split.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        None

    Behavior:
        1. Check if the user is the issuer of the bill split.
        2. Extract the selected category.
        3. Store the selected category in the bill split transaction.
        4. Ask for the confirmation of the bill split.
        5. Wait for the user response before proceeding.
    """
    query = update.callback_query
    group_id = query.message.chat_id

    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await query.answer("No active bill split transaction in this group.")
        return

    # check if the user is the issuer of the bill split
    if (
        query.from_user.id
        != ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].issuer.mm_user[
            "telegram_id"
        ]
    ):
        await query.answer("You are not the issuer of this bill split.")
        return

    selected_category = query.data.removeprefix("category_bill_split_")
    ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].category = selected_category

    await show_confirm_bill_split(update, context)


async def show_confirm_bill_split(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the confirmation message for the bill split.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        None

    Behavior:
        1. Confirm the amount and proceed with the bill split.
        2. Send a new message instead of replying to the message.
    """

    chat_id = update.callback_query.message.chat_id

    # Confirm the amount and proceed with the bill split
    # Instead of replying to the message, send a new message

    await update.callback_query.message.reply_text(
        f"The amount to be split is: {ONGOING_BILL_SPLIT_TRANSACTIONS[chat_id].amount} "
        + f"{ONGOING_BILL_SPLIT_TRANSACTIONS[chat_id].currency}. "
        + f"Each participant will pay {ONGOING_BILL_SPLIT_TRANSACTIONS[chat_id].amount / len(ONGOING_BILL_SPLIT_TRANSACTIONS[chat_id].participants)} "
        # + f"Category: {ONGOING_BILL_SPLIT_TRANSACTIONS[chat_id].category}."
        + "Please confirm the bill split by clicking the button below."
    )
    mentioned_users = list(
        ONGOING_BILL_SPLIT_TRANSACTIONS[chat_id].confirmed_states.keys()
    )
    if not mentioned_users:
        await update.callback_query.message.reply_text(
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
    await update.callback_query.message.reply_text(
        "Each mentioned user, please confirm your participation by clicking the button below:",
        reply_markup=reply_markup,
    )


async def confirm_bill_split_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the confirmation of the bill split.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        None

    Behavior:
        1. Confirm the bill split for the mentioned user.
        2. Update the button states by removing the confirmed user.
        3. Proceed with the bill split process if all users have confirmed.
    """
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
    #     f"User: {user.username} tried to confirm bill split for {mentioned_username}, "+
    #     f"the states are {transaction.confirmed_states}"
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
    else:
        transaction.participants[mentioned_username] = mmuser

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

        await bill_split_proceed_handler(
            update, context, check_status=False, group_id=group_id
        )  # Proceed with the bill split process


@authenticate
async def bill_split_proceed_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    check_status: bool = True,
    group_id=None,
    token: str = None,
) -> None:
    """Proceed with the bill split process.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.
        check_status (bool, optional): Flag to check the status of the bill split. Defaults to True.
        group_id (_type_, optional): The group ID where the transaction is taking place. Defaults to None.
        token (str, optional): The user token. Defaults to None.

    Returns:
        None

    Behavior:
        1. Check if the user is the issuer of the bill split.
        2. Process the bill split transaction
    """
    group_id = group_id or update.message.chat_id

    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await update.message.reply_text(
            "No active bill split transaction in this group."
        )
        return

    transaction = ONGOING_BILL_SPLIT_TRANSACTIONS[group_id]
    update = update if check_status else transaction.anchor_update

    if check_status:
        # check if the user is the issuer of the bill split
        if (
            update.message.from_user.id
            != ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].issuer.mm_user[
                "telegram_id"
            ]
        ):
            await update.message.reply_text(
                "You are not the issuer of this bill split."
            )
            return

    transaction.timestamp = datetime.now(pytz_timezone(TIME_ZONE)).strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )
    group_name = update.message.chat.title
    transaction.description = f"Bill Split in group {group_name} issued by @{transaction.issuer.tg_username}"

    try:
        await process_bill_split(group_id, transaction)
        assert (
            group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS
        ), "Transaction not deleted after processing"
        await update.message.reply_text(
            f"Bill split transaction has been successfully processed.\n"
            f"Transaction ID: {transaction.identifier}\n"
            f"💵 Amount: {transaction.amount} {transaction.currency}\n"
            f"📌 Category: {transaction.category}\n"
            f"📝 Description: {transaction.description}\n"
            f"Participants: {'@'+', @'.join(transaction.participants.keys())}\n"
        )
    except Exception as e:
        logger.error(f"Error while processing bill split: {e}")
        # reply with status
        await bill_split_status_handler(update, context)
        # reply with error message
        reply_message = (
            f"An error occurred while processing the bill split :\n"
            + f"❌ **{e}**\n"
            + f"If you want to try again, please mention me with command /bill\_split\_proceed"
        )
        reply_message = re.sub(r"\.", r"\\.", reply_message)
        await update.message.reply_text(reply_message, parse_mode="MarkdownV2")
        return


async def bill_split_status_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Print the status of the bill split transaction.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        None

    Behavior:
        This will not check if the user is the issuer of the bill split.
        It will print the status of the ongoing bill split transaction in this group chat.
    """

    group_id = update.message.chat_id

    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await update.message.reply_text(
            "No active bill split transaction in this group."
        )
        return

    transaction = ONGOING_BILL_SPLIT_TRANSACTIONS[group_id]
    reply_text = ""
    reply_text += re.sub(
        r"\-", r"\\-", f"Transaction ID: {transaction.identifier}\n"
    )
    reply_text += f"💵 Amount: {transaction.amount or 'Unknown'} with currency {transaction.currency or 'Unknown'}\n"
    reply_text += f"📌 Category: {transaction.category or 'Unknown'}\n"
    reply_text += f"Created by @{transaction.issuer.tg_username} at `{transaction.timestamp}`\n"
    # confirm states
    reply_text += "\nConfirmation Status:\n"
    for user, confirmed in transaction.confirmed_states.items():
        reply_text += wrap_text_for_markdown_v2(
            f"👤 @{user}: {'Confirmed ✅' if confirmed else 'Not Confirmed ❌'}\n"
        )
    # when will the transaction timeout, timeout time = transaction.timestamp + TRANSACTION_TIMEOUT
    timeout_time = datetime.strptime(
        transaction.timestamp, "%Y-%m-%dT%H:%M:%S.%f"
    ) + timedelta(seconds=TRANSACTION_TIMEOUT)
    seconds_to_timeout = (
        timeout_time - datetime.now().replace(tzinfo=None)
    ).total_seconds()
    seconds_to_timeout = int(seconds_to_timeout)
    reply_text += f"\nThis transaction will timeout within {seconds_to_timeout} seconds\n"
    reply_text += wrap_text_for_markdown_v2(
        "If you want to proceed with the bill split, please mention me with command /bill_split_proceed\n"
    )
    reply_text = re.sub(r"\.", r"\\.", reply_text)
    await update.message.reply_text(reply_text, parse_mode="MarkdownV2")


async def cancel_bill_split_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Cancel the bill split process.

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        None

    Behavior:
        1. Check if the user is the issuer of the bill split.
        2. Cancel the bill split process.
    """

    group_id = update.message.chat_id

    if group_id not in ONGOING_BILL_SPLIT_TRANSACTIONS:
        await update.message.reply_text(
            "No active bill split transaction in this group."
        )
        return

    if group_id in ONGOING_BILL_SPLIT_TRANSACTIONS:
        # check if the issuer of cancel command is the same user who initiated the bill split
        if (
            update.message.from_user.id
            != ONGOING_BILL_SPLIT_TRANSACTIONS[group_id].issuer.mm_user[
                "telegram_id"
            ]
        ):
            await update.message.reply_text(
                "You are not the issuer of this bill split."
            )
            return

        del ONGOING_BILL_SPLIT_TRANSACTIONS[group_id]
        await update.message.reply_text(
            "Bill split process has been canceled."
        )
    else:
        await update.message.reply_text(
            "No active bill split transaction to cancel."
        )


async def process_bill_split(
    group_id: int, transaction: BillSplitTransaction
) -> None:
    """Process the bill split transaction.

    1. Check the confirmation states, and check through all the participants if they are authenticated
    2. Check accounts for each participant, make sure in any of their account, there is target currency, and with enough balance
    3. Check accounts for each participant, during which
        3.1 If category is not found, create it for the user
        3.2 If category is created, inform the user
    4. If any of previous steps failed, return error message
    5. If all steps passed, proceed with the transaction

    Args:
        group_id (int): The group ID where the transaction is taking place.
        transaction (BillSplitTransaction): The bill split transaction to process.
    """

    # Check if all participants have confirmed
    try:
        # Check the confirmation states
        assert all(
            transaction.confirmed_states.values()
        ), f"Not all participants have confirmed"
        # Check if all participants are authenticated
        participants_not_confirmed = [
            tg_username
            for tg_username, participant in transaction.participants.items()
            if not participant
        ]
        if participants_not_confirmed:
            raise ValueError(
                f"@{', @'.join(participants_not_confirmed)} have not confirmed this transaction."
            )

        # Check if all participants have accounts with the target currency
        tgusername2account: Dict[
            str, List[Dict]
        ] = {}  # mm username: List[Dict], any account with target currency
        for tg_username, participant in transaction.participants.items():
            headers = {"token": participant["token"]}
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
                        f"Participant {participant} has no account with currency {transaction.currency}."
                    )
            else:
                raise ValueError(
                    # f"Failed to fetch accounts for participant {participant}."
                    "Failed to fetch accounts for some participants."  # for privacy reasons, do not show the participant
                )
            # Store the accounts with the target currency
            tgusername2account[tg_username] = [
                account
                for account in accounts_list
                if account["currency"] == transaction.currency
            ]

        # Check if all participants have enough balance in corresponding accounts
        for tg_username, accounts in tgusername2account.items():
            if all(
                account["balance"] < transaction.amount for account in accounts
            ):
                logger.error(
                    f"Participant tg user @{tg_username} does not have enough {transaction.currency} balance in their accounts."
                )
                raise ValueError(
                    # f"Participant {tg_username} does not have enough balance in their accounts."
                    f"Some participants do not have enough {transaction.currency} balance in their accounts."  # for privacy reasons, do not show the participant
                )
            else:
                # only store the first account with enough balance
                tgusername2account[tg_username] = [
                    account
                    for account in accounts
                    if account["balance"] >= transaction.amount
                ][0]
                logger.debug(
                    f"Using account {tgusername2account[tg_username]['name']} for participant tg user @{tg_username}."
                )

        # Check if all participants have the target category
        category_creation_flag = False
        for tg_username, participant in transaction.participants.items():
            headers = {"token": participant["token"]}
            response = requests.get(
                f"{TELEGRAM_BOT_API_BASE_URL}/categories/",
                headers=headers,
                timeout=API_TIMEOUT,
            )
            if response.status_code == 200:
                category_list = response.json().get("categories", {})
                if (
                    not category_list
                    or transaction.category not in category_list
                ):  # Create the category if it doesn't exist
                    logger.debug(
                        f"Creating category {transaction.category} for tg user {tg_username}."
                    )
                    category_creation_flag = True
                    response = requests.post(
                        f"{TELEGRAM_BOT_API_BASE_URL}/categories/",
                        headers=headers,
                        json={
                            "name": transaction.category,
                            "monthly_budget": 0,
                        },
                        timeout=API_TIMEOUT,
                    )
                    if response.status_code != 200:
                        logger.error(
                            f"Failed to create category {transaction.category} for participant {tg_username}."
                        )
                        raise ValueError(
                            # f"Failed to create category {transaction.category} for participant {tg_username}."
                            "Failed to create category for some participants."  # for privacy reasons, do not show the participant
                        )
        if category_creation_flag:
            transaction.anchor_update.message.reply_text(
                f"Some participants did not have the category {transaction.category}, so it has been created for them. You can manage your categories in the private chat with me."
            )

        # Proceed with the transaction
        for tg_username, participant in transaction.participants.items():
            headers = {"token": participant["token"]}
            response = requests.post(
                f"{TELEGRAM_BOT_API_BASE_URL}/expenses/",
                headers=headers,
                json={
                    "amount": transaction.amount
                    / len(transaction.participants),
                    "description": transaction.description,
                    "category": transaction.category,
                    "currency": transaction.currency,
                    "date": transaction.timestamp,
                    "account": tgusername2account[tg_username]["name"],
                },
                timeout=API_TIMEOUT,
            )
            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error")
                logger.error(
                    f"Failed to create transaction for participant {tg_username}: {error_detail}"
                )
                raise ValueError(
                    # f"Failed to create transaction for participant {tg_username}."
                    f"Failed to create transaction for some participants: {error_detail}"  # for privacy reasons, do not show the participant
                )  # todo should have rollback mechanism

        # finally, delete the transaction
        del ONGOING_BILL_SPLIT_TRANSACTIONS[group_id]

    except Exception as e:
        raise e
