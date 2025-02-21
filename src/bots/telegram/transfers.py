from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import requests
from bots.telegram.auth import authenticate
from bots.telegram.utils import private_chat_cancel
from config.config import TELEGRAM_BOT_API_BASE_URL

TRANSFER_SOURCE, TRANSFER_DESTINATION, TRANSFER_AMOUNT, TRANSFER_CONFIRM = range(4)

@authenticate
async def transfer_start(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> int:
    headers = {"token": token}
    response = requests.get(f"{TELEGRAM_BOT_API_BASE_URL}/accounts/", headers=headers)
    if response.status_code == 200:
        accounts = response.json().get("accounts", [])
        if not accounts:
            await update.message.reply_text("No accounts available for transfer.")
            return ConversationHandler.END
        keyboard = [
            [InlineKeyboardButton(account["name"], callback_data=f"source_{account['_id']}")]
            for account in accounts
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select the source account:", reply_markup=reply_markup)
        return TRANSFER_SOURCE
    else:
        await update.message.reply_text("Failed to fetch accounts.")
        return ConversationHandler.END

@authenticate
async def select_source(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> int:
    query = update.callback_query
    await query.answer()
    source_account_id = query.data.split("_")[1]
    context.user_data["source_account"] = source_account_id

    # Fetch accounts again to list potential destination accounts
    headers = {"token": token}
    response = requests.get(f"{TELEGRAM_BOT_API_BASE_URL}/accounts/", headers=headers)
    if response.status_code == 200:
        accounts = response.json().get("accounts", [])
        # Exclude the source account
        dest_accounts = [acct for acct in accounts if acct["_id"] != source_account_id]
        if not dest_accounts:
            await query.message.edit_text("No other accounts available for transfer.")
            return ConversationHandler.END
        keyboard = [
            [InlineKeyboardButton(account["name"], callback_data=f"dest_{account['_id']}")]
            for account in dest_accounts
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("Select the destination account:", reply_markup=reply_markup)
        return TRANSFER_DESTINATION
    else:
        await query.message.edit_text("Failed to fetch accounts.")
        return ConversationHandler.END

@authenticate
async def select_destination(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> int:
    query = update.callback_query
    await query.answer()
    dest_account_id = query.data.split("_")[1]
    context.user_data["dest_account"] = dest_account_id
    await query.message.edit_text("Enter the amount to transfer:")
    return TRANSFER_AMOUNT

@authenticate
async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> int:
    try:
        amount = float(update.message.text)
        context.user_data["amount"] = amount
        confirmation_text = (
            f"Transfer {amount} from account {context.user_data['source_account']} "
            f"to {context.user_data['dest_account']}. Confirm?"
        )
        keyboard = [[
            InlineKeyboardButton("Yes", callback_data="confirm_yes"),
            InlineKeyboardButton("No", callback_data="confirm_no")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
        return TRANSFER_CONFIRM
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return TRANSFER_AMOUNT
    
@authenticate 
async def confirm_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "confirm_yes":
        payload = {
            "source_account": context.user_data["source_account"],
            "destination_account": context.user_data["dest_account"],
            "amount": context.user_data["amount"]
        }
        headers = {"token": token}
        response = requests.post(f"{TELEGRAM_BOT_API_BASE_URL}/accounts/transfer", json=payload, headers=headers)
        if response.status_code == 200:
            await query.message.edit_text("Transfer successful!")
        else:
            error_detail = response.json().get("detail", "Unknown error")
            await query.message.edit_text(f"Transfer failed: {error_detail}")
    else:
        await query.message.edit_text("Transfer cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

transfer_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("accounts_transfer", transfer_start)],
    states={
        TRANSFER_SOURCE: [CallbackQueryHandler(select_source, pattern="^source_")],
        TRANSFER_DESTINATION: [CallbackQueryHandler(select_destination, pattern="^dest_")],
        TRANSFER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
        TRANSFER_CONFIRM: [CallbackQueryHandler(confirm_transfer, pattern="^confirm_")],
    },
    fallbacks=[CommandHandler("cancel", private_chat_cancel)],
)