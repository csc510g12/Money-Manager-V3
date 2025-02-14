from typing import Callable, Tuple

from loguru import logger
from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


class ReplyWaiters:
    """
    A class to manage reply waiters for Telegram bot messages.
    """

    def __init__(self):
        self.waiters = {
            Tuple[int, int]: Callable
        }  # Dictionary to store waiters

    def __getitem__(self, key):
        """
        Get the callback function for a specific chat and message ID.

        :param key: A tuple containing the chat ID and message ID.
        :return: The callback function associated with the key.
        """
        return self.waiters.get(key)

    def __setitem__(self, key, value):
        """
        Set the callback function for a specific chat and message ID.

        :param key: A tuple containing the chat ID and message ID.
        :param value: The callback function to be associated with the key.
        """
        self.waiters[key] = value

    def __delitem__(self, key):
        """
        Delete the callback function for a specific chat and message ID.

        :param key: A tuple containing the chat ID and message ID.
        """
        if key in self.waiters:
            del self.waiters[key]

    def keys(self):
        """
        Get all keys in the waiters dictionary.

        :return: A list of keys in the waiters dictionary.
        """
        return self.waiters.keys()

    def items(self):
        """
        Get all items in the waiters dictionary.

        :return: A list of items in the waiters dictionary.
        """
        return self.waiters.items()


ReplyWaiters = ReplyWaiters()  # singleton


async def reply_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle replies to messages in the Telegram bot.

    :param update: The update containing the message.
    :param context: The context of the update.
    """
    chat_id = update.message.reply_to_message.chat.id
    message_id = update.message.reply_to_message.message_id

    logger.debug(
        f"Chat ID: {chat_id} - Reply to Message ID: {message_id}"
    )  # todo : remove this line after testing

    if (chat_id, message_id) in ReplyWaiters.keys():
        await ReplyWaiters[(chat_id, message_id)](update, context)
        del ReplyWaiters[(chat_id, message_id)]
    # else:
    #     await update.message.reply_text("This message is not waiting for a reply.")
    return ConversationHandler.END
