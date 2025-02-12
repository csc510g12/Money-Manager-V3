import io
import logging
from datetime import datetime

import google.generativeai as genai
from PIL import Image
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .api_helper import APIHelper  # Add this import at the top
from .auth import get_user
from .gemini_helper import parse_receipt_response, vision_model

# Add logger configuration
logger = logging.getLogger(__name__)

UPLOAD_PHOTO = 1
CONFIRM_DATA = 2

receipts_handlers = []


async def scan_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the receipt scanning process."""
    user = await get_user(update)
    if not user:
        await update.message.reply_text("Please login first to scan receipts.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Please send a photo of your receipt. Make sure the image is clear and well-lit."
    )
    return UPLOAD_PHOTO


async def handle_receipt_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Process the receipt photo."""
    try:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(photo_bytes))

        # Send processing message
        await update.message.reply_text("Processing your receipt... Please wait.")

        # Analyze receipt with Gemini
        prompt = """Analyze this receipt image and extract in JSON format:
        {
            "store": "store name",
            "date": "receipt date (DD/MM/YY)",
            "total": total amount as number,
            "items": [
                {"name": "item name", "price": price as number}
            ]
        }
        Ensure all numbers are numeric values, not strings."""

        response = vision_model.generate_content(
            [prompt, image],
            generation_config={
                "max_output_tokens": 2048,
                "temperature": 0.4,
                "top_p": 0.8,
                "top_k": 40,
            },
        )

        if not response or not response.text:
            raise Exception("Invalid response from Gemini API")

        # Parse receipt data
        receipt_data = parse_receipt_response(response.text)
        context.user_data["receipt_data"] = receipt_data

        # Show extracted data and ask for confirmation
        message = (
            f"📄 Receipt Details:\n\n"
            f"💰 Amount: {receipt_data['total']}\n"
            f"🏪 Store: {receipt_data['store']}\n"
            f"📅 Date: {receipt_data['date']}\n\n"
            "Is this correct?"
        )

        await update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True),
        )
        return CONFIRM_DATA

    except Exception as e:
        logger.error(f"Error processing receipt: {str(e)}")
        await update.message.reply_text(f"Error processing receipt: {str(e)}")
        return ConversationHandler.END


async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user confirmation of extracted data."""
    response = update.message.text.lower()

    if response == "yes":
        try:
            receipt_data = context.user_data.get("receipt_data", {})
            user = await get_user(update)

            if not user:
                raise Exception("User not authenticated")

            # Convert date from DD/MM/YY to ISO format
            receipt_date = datetime.strptime(receipt_data["date"], "%d/%m/%y")
            iso_date = receipt_date.strftime("%Y-%m-%dT%H:%M:%S.%f")

            expense_data = {
                "amount": str(receipt_data["total"]),
                "description": f"Receipt from {receipt_data['store']}",
                "category": "Food",
                "currency": "USD",
                "account": "Checking",
                "date": iso_date,  # Use converted ISO date
            }

            # Save expense via API using token
            api_response = await APIHelper.save_expense(
                token=user["token"], expense_data=expense_data
            )

            if api_response.get("success"):
                await update.message.reply_text(
                    f"✅ Expense saved successfully!\n\n"
                    f"Amount: {receipt_data['total']}\n"
                    f"Store: {receipt_data['store']}\n"
                    f"Date: {receipt_data['date']}",
                    reply_markup=ReplyKeyboardRemove(),
                )
            else:
                raise Exception(api_response.get("message", "Failed to save expense"))

        except Exception as e:
            logger.error(f"Failed to save expense: {str(e)}")
            await update.message.reply_text(
                f"❌ Failed to save expense: {str(e)}",
                reply_markup=ReplyKeyboardRemove(),
            )
    else:
        await update.message.reply_text(
            "Receipt data discarded. Please try scanning again.",
            reply_markup=ReplyKeyboardRemove(),
        )

    context.user_data.pop("receipt_data", None)
    return ConversationHandler.END


# Create conversation handler
receipt_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("scanreceipt", scan_receipt)],
    states={
        UPLOAD_PHOTO: [MessageHandler(filters.PHOTO, handle_receipt_photo)],
        CONFIRM_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_data)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)

# Register handlers
receipts_handlers.append(receipt_conv_handler)
