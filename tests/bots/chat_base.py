from telegram import Chat, User


class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.chat = Chat(id=12345, type="private")
        self.from_user = User(
            id=12345, first_name="Test", is_bot=False, username="testuser"
        )
        self.replied_text = None

    async def reply_text(self, text, **kwargs):
        self.replied_text = text
        return text


class DummyUpdate:
    def __init__(self, text):
        self.message = DummyMessage(text)
        # Set effective_user to mimic Telegram's Update structure
        self.effective_user = self.message.from_user
        self.effective_chat = self.message.chat  # Add effective_chat


class DummyBot:
    username = "test_bot"


class DummyContext:
    bot = DummyBot()
