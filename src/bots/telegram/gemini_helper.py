import io
import json
import logging
import re
from datetime import datetime

import google.generativeai as genai
import PIL.Image
from api_helper import APIHelper
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import config

# Configure Gemini and logging
genai.configure(api_key=config.GEMINI_API_KEY)
vision_model = genai.GenerativeModel("gemini-1.5-flash")
logger = logging.getLogger(__name__)


def parse_receipt_response(response_text: str) -> dict:
    """Parse Gemini's response into structured data"""
    default_data = {
        "store": "Unknown Store",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total": 0.0,
        "items": [],
    }

    try:
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            parsed = json.loads(json_match.group())
            return {**default_data, **parsed}
    except Exception as e:
        logger.error(f"Error parsing receipt response: {e}")
    return default_data


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle receipt photos"""
    try:
        # Process image
        photo = await update.message.photo[-1].get_file()
        image_bytes = await photo.download_as_bytearray()
        image = PIL.Image.open(io.BytesIO(image_bytes))

        # Generate Gemini prompt and get response
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

        # Parse and store receipt data
        receipt_data = parse_receipt_response(response.text)
        context.user_data["last_receipt"] = receipt_data

        # Send response to user
        message = (
            f"📄 Receipt Details:\n\n"
            f"💰 Amount: {receipt_data['total']}\n"
            f"🏪 Store: {receipt_data['store']}\n"
            f"📅 Date: {receipt_data['date']}\n\n"
            f"Save this expense?"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Yes", callback_data="save_receipt_yes"),
                InlineKeyboardButton("❌ No", callback_data="save_receipt_no"),
            ]
        ]

        await update.message.reply_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error processing receipt: {str(e)}")
        await update.message.reply_text(f"Error processing receipt: {str(e)}")


async def handle_receipt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle receipt callback queries"""
    query = update.callback_query
    await query.answer()

    receipt_data = context.user_data.get("last_receipt")
    if not receipt_data:
        await query.edit_message_text("Receipt data not found. Please try again.")
        return

    if query.data == "save_receipt_yes":
        try:
            response = await APIHelper.save_expense(
                user_id=update.effective_user.id, expense_data=receipt_data
            )

            if response.get("success"):
                await query.edit_message_text(
                    f"✅ Expense saved successfully!\n\n"
                    f"Amount: {receipt_data['total']}\n"
                    f"Store: {receipt_data['store']}\n"
                    f"Date: {receipt_data['date']}"
                )
            else:
                raise Exception(response.get("message", "Failed to save expense"))
        except Exception as e:
            logger.error(f"Error saving expense: {e}")
            await query.edit_message_text(f"Failed to save expense: {e}")
    else:
        await query.edit_message_text("❌ Expense not saved")
