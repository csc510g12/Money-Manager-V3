"""Expense management handlers for the Telegram bot."""

from datetime import datetime

import requests
from pytz import timezone  # type: ignore
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram_bot_calendar import DetailedTelegramCalendar
from telegram_bot_pagination import InlineKeyboardPaginator

from bots.telegram.auth import authenticate
from bots.telegram.utils import cancel
from config.config import MONGO_URI, TELEGRAM_BOT_API_BASE_URL, TIME_ZONE

# Constants
TIMEOUT = 10  # seconds

# States for conversation
(
    AMOUNT,
    DESCRIPTION,
    CATEGORY,
    DATE_OPTION,  # New state
    DATE,
    CURRENCY,
    ACCOUNT,
    CONFIRM_DELETE,
    DELETE_ALL_CONFIRM,
    SELECT_EXPENSE,  # New states for update flow
    SELECT_FIELD,
    UPDATE_VALUE,
) = range(12)


@authenticate
async def expenses_add(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the expense addition process."""
    await update.message.reply_text("Please enter the amount:")
    return AMOUNT


async def amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the amount input from the user."""
    try:
        amount = float(update.message.text)
        context.user_data["amount"] = amount
        await update.message.reply_text("Please enter a description:")
        return DESCRIPTION
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return AMOUNT


async def description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the description input from the user."""
    context.user_data["description"] = update.message.text
    await fetch_and_show_categories(update, context)
    return CATEGORY


@authenticate
async def fetch_and_show_categories(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Fetch and display categories for the user to select."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/categories/", headers=headers, timeout=TIMEOUT
    )
    if response.status_code == 200:
        categories = response.json().get("categories", [])
        if not categories:
            message = "No categories found."
            if update.message:
                await update.message.reply_text(message)
            elif update.callback_query:
                await update.callback_query.message.edit_text(message)
            return

        keyboard = [
            [InlineKeyboardButton(category, callback_data=category)]
            for category in categories
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "Please select a category:"

        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(
                message, reply_markup=reply_markup
            )
    else:
        message = "Failed to fetch categories."
        if update.message:
            await update.message.reply_text(message)
        elif update.callback_query:
            await update.callback_query.message.edit_text(message)


async def category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the category selection from the user."""
    query = update.callback_query
    await query.answer()
    context.user_data["category"] = query.data
    await fetch_and_show_currencies(update, context)
    return CURRENCY


@authenticate
async def fetch_and_show_currencies(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Fetch and display currencies for the user to select."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/users/", headers=headers, timeout=TIMEOUT
    )
    if response.status_code == 200:
        currencies = response.json().get("currencies", [])
        if not currencies:
            await update.callback_query.message.edit_text("No currencies found.")
            return

        keyboard = [
            [InlineKeyboardButton(currency, callback_data=currency)]
            for currency in currencies
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            "Please select a currency:", reply_markup=reply_markup
        )
    else:
        await update.callback_query.message.edit_text("Failed to fetch currencies.")


async def currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the currency selection from the user."""
    query = update.callback_query
    await query.answer()
    context.user_data["currency"] = query.data
    await fetch_and_show_accounts(update, context)
    return ACCOUNT


@authenticate
async def fetch_and_show_accounts(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Fetch and display accounts for the user to select."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/accounts/", headers=headers, timeout=TIMEOUT
    )
    if response.status_code == 200:
        accounts = response.json().get("accounts", [])
        if not accounts:
            await update.callback_query.message.edit_text("No accounts found.")
            return

        keyboard = [
            [InlineKeyboardButton(account["name"], callback_data=account["name"])]
            for account in accounts
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            "Please select an account:", reply_markup=reply_markup
        )
    else:
        await update.callback_query.message.edit_text("Failed to fetch accounts.")


@authenticate
async def account(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle the account selection from the user and ask for date option."""
    query = update.callback_query
    await query.answer()
    context.user_data["account"] = query.data
    keyboard = [
        [
            InlineKeyboardButton("Now", callback_data="date_now"),
            InlineKeyboardButton("Custom", callback_data="date_custom"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Please choose the date option:", reply_markup=reply_markup
    )
    return DATE_OPTION


@authenticate
async def handle_date_option(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle the user's date option choice."""
    query = update.callback_query
    await query.answer()
    if query.data == "date_now":
        tz = timezone(TIME_ZONE)
        context.user_data["date"] = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S.%f")
        # ...existing code to finalize expense addition...
        expense_data = {
            "amount": str(float(context.user_data["amount"])),
            "description": context.user_data["description"],
            "category": context.user_data["category"],
            "currency": context.user_data["currency"],
            "account": context.user_data["account"],
            "date": context.user_data["date"],
        }
        headers = {"token": token}
        response = requests.post(
            f"{TELEGRAM_BOT_API_BASE_URL}/expenses/",
            json=expense_data,
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code == 200:
            await query.message.edit_text(
                "Expense added successfully!\nClick /expenses_view to see updated list."
            )
        else:
            error_detail = response.json().get("detail", "Unknown error")
            await query.message.edit_text(f"Failed to add expense: {error_detail}")
        context.user_data.clear()
        return ConversationHandler.END
    elif query.data == "date_custom":
        calendar, step = DetailedTelegramCalendar().build()
        await query.edit_message_text(
            f"Please select the date: {step}", reply_markup=calendar
        )
        return DATE


@authenticate
async def date(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> int:
    """Handle the date selection from the user and finalize the expense addition."""
    result, key, step = DetailedTelegramCalendar().process(update.callback_query.data)
    if not result and key:
        await update.callback_query.message.edit_text(
            f"Please select the date: {step}", reply_markup=key
        )
        return DATE
    elif result:
        # Format the amount as string and ensure it's a valid number
        amount_str = str(float(context.user_data["amount"]))

        expense_data = {
            "amount": amount_str,
            "description": context.user_data["description"],
            "category": context.user_data["category"],
            "currency": context.user_data["currency"],
            "account": context.user_data["account"],
            "date": result.strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            ),  # Save date in the specified format
        }

        headers = {"token": token}
        response = requests.post(
            f"{TELEGRAM_BOT_API_BASE_URL}/expenses/",
            json=expense_data,
            headers=headers,
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            await update.callback_query.message.edit_text(
                "Expense added successfully!\nClick /expenses_view to see updated list."
            )
        else:
            error_detail = response.json().get("detail", "Unknown error")
            await update.callback_query.message.edit_text(
                f"Failed to add expense: {error_detail}"
            )

        context.user_data.clear()
        return ConversationHandler.END


@authenticate
async def expenses_view(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """View the list of expenses with pagination."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/expenses/", headers=headers, timeout=TIMEOUT
    )
    if response.status_code == 200:
        expenses = response.json()["expenses"]
        if not expenses:
            await update.message.reply_text("No expenses found.")
            return

        # Pagination setup
        page = int(context.args[0]) if context.args else 1
        items_per_page = 5
        paginator = InlineKeyboardPaginator(
            len(expenses) // items_per_page
            + (1 if len(expenses) % items_per_page else 0),
            current_page=page,
            data_pattern="view_expenses#{page}",
        )

        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        expenses_page = expenses[start_idx:end_idx]

        message = "💰 *Your Expenses:*\n\n"
        for expense in expenses_page:
            # Convert date to human-readable format, handling datetime strings with time components
            try:
                date = datetime.strptime(
                    expense["date"], "%Y-%m-%dT%H:%M:%S.%f"
                ).strftime("%B %d, %Y")
            except ValueError:
                date = datetime.strptime(expense["date"], "%Y-%m-%dT%H:%M:%S").strftime(
                    "%B %d, %Y"
                )
            message += (
                f"💵 *Amount:* {expense['amount']} {expense['currency']}\n"
                f"📝 *Description:* {expense['description']}\n"
                f"📂 *Category:* {expense['category']}\n"
                f"📅 *Date:* {date}\n"
                "-------------------\n"
            )

        if update.message:
            await update.message.reply_text(
                message, parse_mode="Markdown", reply_markup=paginator.markup
            )
        elif update.callback_query:
            await update.callback_query.message.edit_text(
                message, parse_mode="Markdown", reply_markup=paginator.markup
            )
    else:
        if update.message:
            await update.message.reply_text("Failed to fetch expenses.")
        elif update.callback_query:
            await update.callback_query.message.edit_text("Failed to fetch expenses.")


@authenticate
async def expenses_view_page(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Handle pagination for viewing expenses."""
    query = update.callback_query
    page = int(query.data.split("#")[1])
    context.args = [page]
    await expenses_view(update, context)


@authenticate
async def expenses_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the expense deletion process."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/expenses/", headers=headers, timeout=TIMEOUT
    )
    if response.status_code == 200:
        expenses = response.json()["expenses"]
        if not expenses:
            message = "No expenses found to delete."
            if update.message:
                await update.message.reply_text(message)
            elif update.callback_query:
                await update.callback_query.message.edit_text(message)
            return ConversationHandler.END

        # Pagination setup
        page = int(context.args[0]) if context.args else 1
        items_per_page = 2
        total_pages = len(expenses) // items_per_page + (
            1 if len(expenses) % items_per_page else 0
        )

        # Create pagination buttons manually
        pagination_buttons = []
        if total_pages > 1:
            if page > 1:
                pagination_buttons.append(
                    InlineKeyboardButton("⬅️", callback_data=f"delete_expenses#{page-1}")
                )
            if page < total_pages:
                pagination_buttons.append(
                    InlineKeyboardButton("➡️", callback_data=f"delete_expenses#{page+1}")
                )

        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        expenses_page = expenses[start_idx:end_idx]

        keyboard = []
        for expense in expenses_page:
            button_text = (
                f"{expense['description']} - {expense['amount']} {expense['currency']}"
            )
            callback_data = f"delete_{expense['_id']}"
            keyboard.append(
                [InlineKeyboardButton(button_text, callback_data=callback_data)]
            )

        # Add pagination row to keyboard if there are pagination buttons
        if pagination_buttons:
            keyboard.append(pagination_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "Select an expense to delete:"

        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(
                message, reply_markup=reply_markup
            )
        return CONFIRM_DELETE
    else:
        message = "Failed to fetch expenses."
        if update.message:
            await update.message.reply_text(message)
        elif update.callback_query:
            await update.callback_query.message.edit_text(message)
        return ConversationHandler.END


@authenticate
async def expenses_delete_page(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle pagination for deleting expenses."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("#")[1])
    context.args = [page]
    return await expenses_delete(update, context)


@authenticate
async def confirm_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Confirm the deletion of a specific expense."""
    query = update.callback_query
    await query.answer()

    # If it's a pagination callback, let it pass through
    if query.data.startswith("delete_expenses#"):
        return CONFIRM_DELETE

    if query.data.startswith("delete_"):
        context.user_data["expense_id"] = query.data.split("_")[1]
        await query.message.edit_text(
            "Are you sure you want to delete this expense?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Yes", callback_data="confirm_delete"),
                        InlineKeyboardButton("No", callback_data="cancel_delete"),
                    ]
                ]
            ),
        )
        return CONFIRM_DELETE
    elif query.data == "confirm_delete":
        expense_id = context.user_data.get("expense_id")
        headers = {"token": token}
        response = requests.delete(
            f"{TELEGRAM_BOT_API_BASE_URL}/expenses/{expense_id}",
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code == 200:
            await query.message.edit_text(
                "Expense deleted successfully!\nClick /expenses_view to see updated list."
            )
        else:
            await query.message.edit_text("Failed to delete expense.")
        context.user_data.clear()
        return ConversationHandler.END
    elif query.data == "cancel_delete":
        await query.message.edit_text("Deletion cancelled.")
        context.user_data.clear()
        return ConversationHandler.END


@authenticate
async def expenses_delete_all(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the process to delete all expenses."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/expenses/", headers=headers, timeout=TIMEOUT
    )
    if response.status_code == 200:
        expenses = response.json()["expenses"]
        if not expenses:
            await update.message.reply_text("No expenses found to delete.")
            return ConversationHandler.END

        total_expenses = len(expenses)
        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data="confirm_delete_all"),
                InlineKeyboardButton("No", callback_data="cancel_delete_all"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"⚠️ Are you sure you want to delete all {total_expenses} expenses? This action cannot be undone!",
            reply_markup=reply_markup,
        )
        return DELETE_ALL_CONFIRM
    else:
        await update.message.reply_text("Failed to fetch expenses.")
        return ConversationHandler.END


@authenticate
async def confirm_delete_all(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Confirm the deletion of all expenses."""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_delete_all":
        headers = {"token": token}
        response = requests.delete(
            f"{TELEGRAM_BOT_API_BASE_URL}/expenses/all",
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code == 200:
            await query.message.edit_text("✅ All expenses deleted successfully!")
        else:
            await query.message.edit_text("❌ Failed to delete expenses.")
        return ConversationHandler.END
    elif query.data == "cancel_delete_all":
        await query.message.edit_text("Deletion cancelled.")
        return ConversationHandler.END


@authenticate
async def expenses_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the expense update process by showing list of expenses."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/expenses/", headers=headers, timeout=TIMEOUT
    )

    if response.status_code == 200:
        expenses = response.json()["expenses"]
        if not expenses:
            await update.message.reply_text("No expenses found to update.")
            return ConversationHandler.END

        # Pagination setup
        page = int(context.args[0]) if context.args else 1
        items_per_page = 5
        total_pages = len(expenses) // items_per_page + (
            1 if len(expenses) % items_per_page else 0
        )

        # Create pagination buttons
        pagination_buttons = []
        if total_pages > 1:
            if page > 1:
                pagination_buttons.append(
                    InlineKeyboardButton("⬅️", callback_data=f"update_expenses#{page-1}")
                )
            if page < total_pages:
                pagination_buttons.append(
                    InlineKeyboardButton("➡️", callback_data=f"update_expenses#{page+1}")
                )

        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        expenses_page = expenses[start_idx:end_idx]

        keyboard = []
        for expense in expenses_page:
            button_text = (
                f"{expense['description']} - {expense['amount']} {expense['currency']}"
            )
            callback_data = f"update_{expense['_id']}"
            keyboard.append(
                [InlineKeyboardButton(button_text, callback_data=callback_data)]
            )

        # Add pagination row if there are pagination buttons
        if pagination_buttons:
            keyboard.append(pagination_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "Select an expense to update:"

        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(
                message, reply_markup=reply_markup
            )
        return SELECT_EXPENSE
    else:
        message = "Failed to fetch expenses."
        if update.message:
            await update.message.reply_text(message)
        elif update.callback_query:
            await update.callback_query.message.edit_text(message)
        return ConversationHandler.END


@authenticate
async def expenses_update_page(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle pagination for updating expenses."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("#")[1])
    context.args = [page]
    return await expenses_update(update, context)


async def select_update_field(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Show options for which field to update."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("update_"):
        expense_id = query.data.split("_")[1]
        context.user_data["expense_id"] = expense_id

        keyboard = [
            [InlineKeyboardButton("Amount", callback_data="field_amount")],
            [InlineKeyboardButton("Description", callback_data="field_description")],
            [InlineKeyboardButton("Category", callback_data="field_category")],
            [InlineKeyboardButton("Currency", callback_data="field_currency")],
            [InlineKeyboardButton("Account", callback_data="field_account")],
            [InlineKeyboardButton("Date", callback_data="field_date")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "What would you like to update?", reply_markup=reply_markup
        )
        return SELECT_FIELD


@authenticate
async def handle_field_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle the selected field and prompt for new value."""
    query = update.callback_query
    await query.answer()

    field = query.data.split("_")[1]
    context.user_data["update_field"] = field

    if field == "category":
        await fetch_and_show_categories(update, context)
    elif field == "currency":
        await fetch_and_show_currencies(update, context)
    elif field == "account":
        await fetch_and_show_accounts(update, context)
    elif field == "date":
        calendar, step = DetailedTelegramCalendar().build()
        await query.edit_message_text(f"Select new date:", reply_markup=calendar)
    else:
        await query.message.edit_text(f"Please enter new {field}:")

    return UPDATE_VALUE


@authenticate
async def handle_update_value(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle the new value and update the expense."""
    field = context.user_data["update_field"]
    expense_id = context.user_data["expense_id"]

    if update.callback_query:  # For category, currency, account, date selections
        query = update.callback_query
        await query.answer()

        if field == "date":
            result, key, step = DetailedTelegramCalendar().process(query.data)
            if not result and key:
                await query.message.edit_text(f"Select date: {step}", reply_markup=key)
                return UPDATE_VALUE
            new_value = result.strftime("%Y-%m-%dT%H:%M:%S.%f")
        else:
            new_value = query.data
    else:  # For text input (amount, description)
        new_value = update.message.text
        if field == "amount":
            try:
                new_value = str(float(new_value))
            except ValueError:
                await update.message.reply_text("Please enter a valid number.")
                return UPDATE_VALUE

    # Update the expense
    headers = {"token": token}
    update_data = {field: new_value}
    response = requests.put(
        f"{TELEGRAM_BOT_API_BASE_URL}/expenses/{expense_id}",
        json=update_data,
        headers=headers,
        timeout=TIMEOUT,
    )

    message = (
        "Expense updated successfully!\nClick /expenses_view to see updated list."
        if response.status_code == 200
        else f"Failed to update expense: {response.json()['detail']}"
    )

    if update.callback_query:
        await update.callback_query.message.edit_text(message)
    else:
        await update.message.reply_text(message)

    context.user_data.clear()
    return ConversationHandler.END


# Handlers for expenses
expenses_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("expenses_add", expenses_add)],
    states={
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
        CATEGORY: [CallbackQueryHandler(category)],
        CURRENCY: [CallbackQueryHandler(currency)],
        ACCOUNT: [CallbackQueryHandler(account)],
        DATE_OPTION: [CallbackQueryHandler(handle_date_option)],
        DATE: [CallbackQueryHandler(date)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Add the new handlers
expenses_delete_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("expenses_delete", expenses_delete)],
    states={
        CONFIRM_DELETE: [
            CallbackQueryHandler(
                expenses_delete_page, pattern=r"^delete_expenses#\d+$"
            ),
            CallbackQueryHandler(confirm_delete),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Add the delete all conversation handler
expenses_delete_all_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("expenses_delete_all", expenses_delete_all)],
    states={
        DELETE_ALL_CONFIRM: [CallbackQueryHandler(confirm_delete_all)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Add this new conversation handler at the bottom with other handlers
expenses_update_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("expenses_update", expenses_update)],
    states={
        SELECT_EXPENSE: [
            CallbackQueryHandler(
                expenses_update_page, pattern=r"^update_expenses#\d+$"
            ),
            CallbackQueryHandler(select_update_field, pattern=r"^update_"),
        ],
        SELECT_FIELD: [
            CallbackQueryHandler(handle_field_selection, pattern=r"^field_")
        ],
        UPDATE_VALUE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_update_value),
            CallbackQueryHandler(handle_update_value),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Handlers for expenses
expenses_handlers = [
    CommandHandler("expenses_view", expenses_view),
    CallbackQueryHandler(expenses_view_page, pattern="^view_expenses#"),
    expenses_conv_handler,
    expenses_delete_conv_handler,
    expenses_delete_all_conv_handler,
    expenses_update_conv_handler,
    CallbackQueryHandler(expenses_delete_page, pattern=r"^delete_expenses#\d+$"),
]
