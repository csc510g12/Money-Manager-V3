import pytest
from chat_base import *

from bots.telegram.main import start


@pytest.mark.asyncio(loop_scope="session")
async def test_start_handler_with_user(monkeypatch):
    # Simulate a user already logged in
    async def fake_get_user(update):
        return {"username": "testuser"}

    monkeypatch.setattr("bots.telegram.auth.get_user", fake_get_user)

    update = DummyUpdate("/start")
    context = DummyContext()
    await start(update, context)

    # Check that the bot replies with a welcome message for a returning user
    assert update.message.replied_text is not None
    assert (
        "Welcome to Money Manager Telegram Bot!" in update.message.replied_text
        or "Welcome back, testuser" in update.message.replied_text
    )
    return


@pytest.mark.asyncio(loop_scope="session")
async def test_start_handler_without_user(monkeypatch):
    # Simulate no user found (not logged in)
    async def fake_get_user(update):
        return None

    monkeypatch.setattr("bots.telegram.auth.get_user", fake_get_user)

    update = DummyUpdate("/start")
    context = DummyContext()
    await start(update, context)

    # Check that the bot instructs the user to login or signup
    assert update.message.replied_text is not None
    # write the message to file
    # with open("test_log.txt", "a") as f:
    #     f.write(update.message.replied_text)
    assert (
        "Please /login or /signup to continue." in update.message.replied_text
        or "Welcome back, testuser" in update.message.replied_text
    )
