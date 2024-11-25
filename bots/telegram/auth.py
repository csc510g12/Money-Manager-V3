"""Authentication handlers and utilities for the Telegram bot."""

import requests
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bots.telegram.utils import cancel
from config import config

# Constants
TIMEOUT = 10  # seconds

# States for conversation
USERNAME, PASSWORD, LOGIN_PASSWORD, SIGNUP_CONFIRM = range(4)

# MongoDB collection
mongodb_client = AsyncIOMotorClient(config.MONGO_URI)
telegram_collection = mongodb_client.mmdb.telegram_bot


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the login process."""
    await update.message.reply_text("Please enter your username:")
    return USERNAME


async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["is_signup"] = True
    await update.message.reply_text("Please enter your username:")
    return USERNAME


async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["username"] = update.message.text
    await update.message.reply_text("Please enter your password:")
    return PASSWORD if context.user_data.get("is_signup") else LOGIN_PASSWORD


async def handle_login_password(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    try:
        response = requests.post(
            f"{config.TELEGRAM_BOT_API_BASE_URL}/users/token/?token_expires=43200",
            data={
                "username": context.user_data["username"],
                "password": update.message.text,
            },
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            token = response.json()["result"]["token"]
            user_id = update.effective_user.id

            user = await telegram_collection.find_one(
                {"username": context.user_data["username"]}
            )
            if user:
                await telegram_collection.update_one(
                    {"telegram_id": user_id},
                    {
                        "$set": {
                            "token": token,
                            "username": context.user_data["username"],
                        }
                    },
                )
            else:
                user_data = {
                    "username": context.user_data["username"],
                    "token": token,
                    "telegram_id": user_id,
                }
                await telegram_collection.insert_one(user_data)

            await update.message.reply_text("Login successful!")
        else:
            await update.message.reply_text(
                f"Login failed: {response.json()['detail']}\n /signup if you haven't, otherwise /login"
            )
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")
        return ConversationHandler.END


async def handle_signup_password(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data["password"] = update.message.text
    await update.message.reply_text("Please confirm your password:")
    return SIGNUP_CONFIRM


async def handle_signup_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    try:
        if update.message.text != context.user_data["password"]:
            await update.message.reply_text("Passwords don't match. Please try again.")
            return ConversationHandler.END

        signup_data = {
            "username": context.user_data["username"],
            "password": context.user_data["password"],
        }
        response = requests.post(
            f"{config.TELEGRAM_BOT_API_BASE_URL}/users/",
            json=signup_data,
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            login_response = requests.post(
                f"{config.TELEGRAM_BOT_API_BASE_URL}/users/token/?token_expires=43200",
                data={
                    "username": context.user_data["username"],
                    "password": context.user_data["password"],
                },
                timeout=TIMEOUT,
            )

            if login_response.status_code == 200:
                token = login_response.json()["result"]["token"]
                user_id = update.effective_user.id

                user_data = {
                    "username": context.user_data["username"],
                    "token": token,
                    "telegram_id": user_id,
                }
                await telegram_collection.insert_one(user_data)

                await update.message.reply_text(
                    "Signup successful! You are now logged in."
                )
            else:
                await update.message.reply_text(
                    "Account created! Please use /login to access your account."
                )
        else:
            error_msg = response.json().get("detail", "Username may already exist.")
            await update.message.reply_text(f"Signup failed: {error_msg}")

        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(
            "An error occurred during signup. Please try again."
        )
        return ConversationHandler.END


def authenticate(func):
    """Decorator to check if user is authenticated."""

    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user_id = update.effective_user.id
        user = await telegram_collection.find_one({"telegram_id": user_id})
        if user and user.get("token"):
            return await func(update, context, token=user.get("token"), *args, **kwargs)
        await update.message.reply_text("You are not authenticated. Please /login")
        return ConversationHandler.END

    return wrapper


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    result = await telegram_collection.delete_many({"telegram_id": user_id})
    if result.deleted_count > 0:
        await update.message.reply_text("You have been logged out successfully.")
    else:
        await update.message.reply_text("You are not logged in.")


# Handlers for authentication
login_handler = ConversationHandler(
    entry_points=[CommandHandler("login", login)],
    states={
        USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username)],
        LOGIN_PASSWORD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_login_password)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

signup_handler = ConversationHandler(
    entry_points=[CommandHandler("signup", signup)],
    states={
        USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username)],
        PASSWORD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_signup_password)
        ],
        SIGNUP_CONFIRM: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_signup_confirm)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
