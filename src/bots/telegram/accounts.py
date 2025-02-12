"""Account management handlers for the Telegram bot."""

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram_bot_pagination import InlineKeyboardPaginator

from bots.telegram.auth import authenticate
from bots.telegram.utils import cancel
from config.config import TELEGRAM_BOT_API_BASE_URL

# Constants
TIMEOUT = 10  # seconds

# States for account conversation
(
    ACCOUNT_NAME,
    INITIAL_BALANCE,
    SELECT_CURRENCY,  # Add new state
    CONFIRM_DELETE,
    SELECT_ACCOUNT,
    SELECT_UPDATE_TYPE,  # New state
    UPDATE_NAME,  # Add this
    UPDATE_BALANCE,
    SELECT_CATEGORY,  # Add new state
) = range(
    9
)  # Update range to 9


@authenticate
async def accounts_view(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """View the list of accounts with pagination."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/accounts/", headers=headers, timeout=TIMEOUT
    )

    if response.status_code == 200:
        accounts_list = response.json().get("accounts", [])
        if not accounts_list:
            await update.message.reply_text("No accounts found.")
            return

        # Sort accounts by name
        sorted_accounts = sorted(accounts_list, key=lambda x: x["name"])

        # Pagination setup
        page = int(context.args[0]) if context.args else 1
        items_per_page = 5
        total_pages = len(sorted_accounts) // items_per_page + (
            1 if len(sorted_accounts) % items_per_page else 0
        )
        paginator = InlineKeyboardPaginator(
            total_pages, current_page=page, data_pattern="view_accounts#{page}"
        )

        # Get accounts for current page
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_items = sorted_accounts[start_idx:end_idx]

        # Format message
        message = "💳 *Your Accounts:*\n\n"
        for account in page_items:
            message += (
                f"🏦 *Account:* {account['name']}\n"
                f"💰 *Balance:* {round(account['balance'], 2)} {account['currency']}\n"
                "-------------------\n"
            )

        # Send or edit message with pagination
        if update.message:
            await update.message.reply_text(
                message, parse_mode="Markdown", reply_markup=paginator.markup
            )
        elif update.callback_query:
            await update.callback_query.message.edit_text(
                message, parse_mode="Markdown", reply_markup=paginator.markup
            )
    else:
        error_message = "Failed to fetch accounts."
        if update.message:
            await update.message.reply_text(error_message)
        elif update.callback_query:
            await update.callback_query.message.edit_text(error_message)


@authenticate
async def accounts_view_page(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Handle pagination for viewing accounts."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("#")[1])
    context.args = [page]
    await accounts_view(update, context)


@authenticate
async def accounts_add(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the account addition process."""
    await update.message.reply_text("Please enter the account name:")
    return ACCOUNT_NAME


async def handle_account_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the account name input."""
    account_name = update.message.text
    context.user_data["account_name"] = account_name
    await update.message.reply_text(
        "Please enter the initial balance for this account:"
    )
    return INITIAL_BALANCE


@authenticate
async def handle_initial_balance(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle the initial balance input."""
    try:
        initial_balance = float(update.message.text)
        context.user_data["balance"] = str(initial_balance)

        # Fetch available currencies
        headers = {"token": token}
        response = requests.get(
            f"{TELEGRAM_BOT_API_BASE_URL}/users/", headers=headers, timeout=TIMEOUT
        )
        if response.status_code == 200:
            currencies = response.json().get("currencies", [])
        else:
            await update.message.reply_text(
                "Failed to fetch currencies. Please try again later."
            )
            return ConversationHandler.END

        # Create keyboard with available currency options
        keyboard = []
        for currency in currencies:
            keyboard.append(
                [InlineKeyboardButton(currency, callback_data=f"currency_{currency}")]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please select the currency:", reply_markup=reply_markup
        )
        return SELECT_CURRENCY

    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for the initial balance."
        )
        return INITIAL_BALANCE


@authenticate
async def handle_currency_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle currency selection and create the account."""
    query = update.callback_query
    await query.answer()
    context.user_data["currency"] = query.data.split("_")[1]

    account_data = {
        "name": context.user_data["account_name"],
        "balance": context.user_data["balance"],
        "currency": context.user_data.get("currency", "USD"),
    }

    response = requests.post(
        f"{TELEGRAM_BOT_API_BASE_URL}/accounts/",
        json=account_data,
        headers={"token": token},
        timeout=TIMEOUT,
    )

    if response.status_code == 200:
        await query.message.edit_text(
            "Account added successfully!\nClick /accounts_view to see the updated list."
        )
    else:
        error_detail = response.json().get("detail", "Unknown error")
        await query.message.edit_text(f"Failed to add account: {error_detail}")

    context.user_data.clear()
    return ConversationHandler.END


@authenticate
async def accounts_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the account deletion process."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/accounts/", headers=headers, timeout=TIMEOUT
    )

    if response.status_code == 200:
        accounts = response.json().get("accounts", [])
        if not accounts:
            await update.message.reply_text("No accounts found to delete.")
            return ConversationHandler.END

        # Create keyboard with account buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{account['name']} : {(round(account['balance'], 2))} {account['currency']}",
                    callback_data=f"delete_{account['_id']}",
                )
            ]
            for account in accounts
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Select an account to delete:", reply_markup=reply_markup
        )
        return CONFIRM_DELETE
    else:
        await update.message.reply_text("Failed to fetch accounts.")
        return ConversationHandler.END


@authenticate
async def confirm_delete_account(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Confirm the deletion of a specific account."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("delete_"):
        account_id = query.data.split("_")[1]
        context.user_data["account_name"] = account_id

        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data="confirm_delete"),
                InlineKeyboardButton("No", callback_data="cancel_delete"),
            ]
        ]
        await query.message.edit_text(
            f"⚠️ Are you sure you want to delete account with id '{account_id}'?\n",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRM_DELETE

    elif query.data == "confirm_delete":
        account_id = context.user_data["account_name"]
        headers = {"token": token}
        response = requests.delete(
            f"{TELEGRAM_BOT_API_BASE_URL}/accounts/{account_id}",
            headers=headers,
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            await query.message.edit_text(
                "✅ Account deleted successfully!\nClick /accounts_view to see the updated list."
            )
        else:
            error_detail = response.json().get("detail", "Unknown error")
            await query.message.edit_text(
                f"❌ Failed to delete account: {error_detail}"
            )

        context.user_data.clear()
        return ConversationHandler.END

    elif query.data == "cancel_delete":
        await query.message.edit_text("Deletion cancelled.")
        context.user_data.clear()
        return ConversationHandler.END


@authenticate
async def accounts_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the account update process."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/accounts/", headers=headers, timeout=TIMEOUT
    )

    if response.status_code == 200:
        accounts = response.json().get("accounts", [])
        if not accounts:
            await update.message.reply_text("No accounts found to update.")
            return ConversationHandler.END

        keyboard = [
            [
                InlineKeyboardButton(
                    f"{account['name']} : {round(account['balance'], 2)} {account['currency']}",
                    callback_data=f"update_{account['_id']}",
                )
            ]
            for account in accounts
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Select an account to update its balance:", reply_markup=reply_markup
        )
        return SELECT_ACCOUNT
    else:
        await update.message.reply_text("Failed to fetch accounts.")
        return ConversationHandler.END


async def handle_account_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle account selection and show update options."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("update_"):
        account_id = query.data.split("_")[1]
        context.user_data["account_id"] = account_id

        keyboard = [
            [
                InlineKeyboardButton("Update Name", callback_data="change_name"),
                InlineKeyboardButton("Update Balance", callback_data="change_balance"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "What would you like to update?", reply_markup=reply_markup
        )
        return SELECT_UPDATE_TYPE


async def handle_update_type_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the selection of what to update."""
    query = update.callback_query
    await query.answer()

    if query.data == "change_name":
        await query.message.edit_text("Please enter the new name:")
        return UPDATE_NAME
    elif query.data == "change_balance":
        await query.message.edit_text("Please enter the new balance:")
        return UPDATE_BALANCE


@authenticate
async def handle_name_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle the name update."""
    new_name = update.message.text
    account_id = context.user_data["account_id"]

    headers = {"token": token}
    response = requests.put(
        f"{TELEGRAM_BOT_API_BASE_URL}/accounts/{account_id}",
        json={"name": new_name},
        headers=headers,
        timeout=TIMEOUT,
    )

    if response.status_code == 200:
        await update.message.reply_text(
            "✅ Account name updated successfully!\nClick /accounts_view to see the updated list."
        )
    else:
        error_detail = response.json().get("detail", "Unknown error")
        await update.message.reply_text(f"❌ Failed to update account: {error_detail}")

    context.user_data.clear()
    return ConversationHandler.END


@authenticate
async def handle_balance_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle the balance update."""
    try:
        new_balance = float(update.message.text)
        account_id = context.user_data["account_id"]

        headers = {"token": token}
        response = requests.put(
            f"{TELEGRAM_BOT_API_BASE_URL}/accounts/{account_id}",
            json={"balance": str(new_balance)},
            headers=headers,
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            await update.message.reply_text(
                "✅ Account balance updated successfully!\nClick /accounts_view to see the updated list."
            )
        else:
            error_detail = response.json().get("detail", "Unknown error")
            await update.message.reply_text(
                f"❌ Failed to update account: {error_detail}"
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Please enter a valid number for the balance.")
        return UPDATE_BALANCE


# Handlers for accounts
accounts_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("accounts_add", accounts_add)],
    states={
        ACCOUNT_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_name)
        ],
        INITIAL_BALANCE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_initial_balance)
        ],
        SELECT_CURRENCY: [CallbackQueryHandler(handle_currency_selection)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Add new conversation handler
accounts_delete_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("accounts_delete", accounts_delete)],
    states={
        CONFIRM_DELETE: [CallbackQueryHandler(confirm_delete_account)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Update the accounts_update_conv_handler
accounts_update_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("accounts_update", accounts_update)],
    states={
        SELECT_ACCOUNT: [CallbackQueryHandler(handle_account_selection)],
        SELECT_UPDATE_TYPE: [CallbackQueryHandler(handle_update_type_selection)],
        UPDATE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_update)
        ],
        UPDATE_BALANCE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_balance_update)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Update the handlers list
accounts_handlers = [
    CommandHandler("accounts_view", accounts_view),
    CallbackQueryHandler(accounts_view_page, pattern="^view_accounts#"),
    accounts_conv_handler,
    accounts_delete_conv_handler,
    accounts_update_conv_handler,
]
