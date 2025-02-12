"""Category management handlers for the Telegram bot."""

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

# States for category conversation
(
    CATEGORY_NAME,
    MONTHLY_BUDGET,
    CONFIRM_DELETE,
    SELECT_CATEGORY,
    NEW_CATEGORY_NAME,
    UPDATE_BUDGET,
) = range(
    6
)  # Added UPDATE_BUDGET


@authenticate
async def categories_view(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """View the list of categories with pagination."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/categories/", headers=headers, timeout=TIMEOUT
    )

    if response.status_code == 200:
        categories_dict = response.json().get("categories", {})
        if not categories_dict:
            await update.message.reply_text("No categories found.")
            return

        # Sort categories by name
        sorted_categories = dict(sorted(categories_dict.items()))

        # Pagination setup
        page = int(context.args[0]) if context.args else 1
        items_per_page = 5
        total_pages = len(sorted_categories) // items_per_page + (
            1 if len(sorted_categories) % items_per_page else 0
        )
        paginator = InlineKeyboardPaginator(
            total_pages, current_page=page, data_pattern="view_categories#{page}"
        )

        # Get categories for current page
        categories_items = list(sorted_categories.items())
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_items = categories_items[start_idx:end_idx]

        # Format message
        message = "📁 *Your Categories:*\n\n"
        for category, details in page_items:
            message += (
                f"📌 *Category:* {category}\n"
                f"💰 *Monthly Budget:* {details['monthly_budget']}\n"
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
        error_message = "Failed to fetch categories."
        if update.message:
            await update.message.reply_text(error_message)
        elif update.callback_query:
            await update.callback_query.message.edit_text(error_message)


@authenticate
async def categories_view_page(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Handle pagination for viewing categories."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("#")[1])
    context.args = [page]
    await categories_view(update, context)


@authenticate
async def categories_add(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the category addition process."""
    await update.message.reply_text("Please enter the category name:")
    return CATEGORY_NAME


async def handle_category_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the category name input."""
    category_name = update.message.text
    context.user_data["category_name"] = category_name
    await update.message.reply_text(
        "Please enter the monthly budget for this category:"
    )
    return MONTHLY_BUDGET


@authenticate
async def handle_monthly_budget(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle the monthly budget input and create the category."""
    try:
        monthly_budget = float(update.message.text)
        category_data = {
            "name": context.user_data["category_name"],
            "monthly_budget": str(monthly_budget),
        }

        headers = {"token": token}
        response = requests.post(
            f"{TELEGRAM_BOT_API_BASE_URL}/categories/",
            json=category_data,
            headers=headers,
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            await update.message.reply_text(
                "Category added successfully!\nClick /categories_view to see the updated list."
            )
        else:
            error_detail = response.json().get("detail", "Unknown error")
            await update.message.reply_text(f"Failed to add category: {error_detail}")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for the monthly budget."
        )
        return MONTHLY_BUDGET


@authenticate
async def categories_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the category deletion process."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/categories/", headers=headers, timeout=TIMEOUT
    )

    if response.status_code == 200:
        categories = response.json().get("categories", {})
        if not categories:
            await update.message.reply_text("No categories found to delete.")
            return ConversationHandler.END

        # Create keyboard with category buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{category} - Budget: {details['monthly_budget']}",
                    callback_data=f"delete_{category}",
                )
            ]
            for category, details in categories.items()
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Select a category to delete:", reply_markup=reply_markup
        )
        return CONFIRM_DELETE
    else:
        await update.message.reply_text("Failed to fetch categories.")
        return ConversationHandler.END


@authenticate
async def confirm_delete_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Confirm the deletion of a specific category."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("delete_"):
        category_name = query.data.split("_")[1]
        context.user_data["category_name"] = category_name

        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data="confirm_delete"),
                InlineKeyboardButton("No", callback_data="cancel_delete"),
            ]
        ]
        await query.message.edit_text(
            f"⚠️ Are you sure you want to delete category '{category_name}'?\n",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRM_DELETE

    elif query.data == "confirm_delete":
        category_name = context.user_data["category_name"]
        headers = {"token": token}
        response = requests.delete(
            f"{TELEGRAM_BOT_API_BASE_URL}/categories/{category_name}",
            headers=headers,
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            await query.message.edit_text(
                "✅ Category deleted successfully!\nClick /categories_view to see the updated list."
            )
        else:
            error_detail = response.json().get("detail", "Unknown error")
            await query.message.edit_text(
                f"❌ Failed to delete category: {error_detail}"
            )

        context.user_data.clear()
        return ConversationHandler.END

    elif query.data == "cancel_delete":
        await query.message.edit_text("Deletion cancelled.")
        context.user_data.clear()
        return ConversationHandler.END


@authenticate
async def categories_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Start the category update process."""
    headers = {"token": token}
    response = requests.get(
        f"{TELEGRAM_BOT_API_BASE_URL}/categories/", headers=headers, timeout=TIMEOUT
    )

    if response.status_code == 200:
        categories = response.json().get("categories", {})
        if not categories:
            await update.message.reply_text("No categories found to update.")
            return ConversationHandler.END

        keyboard = [
            [
                InlineKeyboardButton(
                    f"{category} - Budget: {details['monthly_budget']}",
                    callback_data=f"update_{category}",
                )
            ]
            for category, details in categories.items()
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Select a category to update its monthly budget:", reply_markup=reply_markup
        )
        return SELECT_CATEGORY
    else:
        await update.message.reply_text("Failed to fetch categories.")
        return ConversationHandler.END


async def handle_category_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle category selection and prompt for new budget."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("update_"):
        category_name = query.data.split("_")[1]
        context.user_data["category_name"] = category_name
        await query.message.edit_text(
            f"Please enter the new monthly budget for '{category_name}':"
        )
        return UPDATE_BUDGET


@authenticate
async def handle_budget_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> int:
    """Handle the new budget value and update the category."""
    try:
        new_budget = float(update.message.text)
        category_name = context.user_data["category_name"]

        headers = {"token": token}
        response = requests.put(
            f"{TELEGRAM_BOT_API_BASE_URL}/categories/{category_name}",
            json={"monthly_budget": str(new_budget)},
            headers=headers,
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            await update.message.reply_text(
                f"✅ Monthly budget updated successfully for '{category_name}'!\n"
                "Click /categories_view to see the updated list."
            )
        else:
            error_detail = response.json().get("detail", "Unknown error")
            await update.message.reply_text(
                f"❌ Failed to update category: {error_detail}"
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for the monthly budget."
        )
        return UPDATE_BUDGET


# Handlers for categories
categories_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("categories_add", categories_add)],
    states={
        CATEGORY_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_name)
        ],
        MONTHLY_BUDGET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_monthly_budget)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Add new conversation handler
categories_delete_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("categories_delete", categories_delete)],
    states={
        CONFIRM_DELETE: [CallbackQueryHandler(confirm_delete_category)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Add new conversation handler for updates
categories_update_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("categories_update", categories_update)],
    states={
        SELECT_CATEGORY: [CallbackQueryHandler(handle_category_selection)],
        UPDATE_BUDGET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget_update)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Update the handlers list
categories_handlers = [
    CommandHandler("categories_view", categories_view),
    CallbackQueryHandler(categories_view_page, pattern="^view_categories#"),
    categories_conv_handler,
    categories_delete_conv_handler,
    categories_update_conv_handler,  # Add the new handler
]
