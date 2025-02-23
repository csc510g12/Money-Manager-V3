from unittest.mock import AsyncMock, patch

import pytest
from chat_base import DummyContext, DummyUpdate

from bots.telegram.auth import (
    handle_login_password,
    handle_username,
    login,
)


@pytest.mark.asyncio(loop_scope="session")
async def test_login():
    update = DummyUpdate("/login")
    context = DummyContext()
    await login(update, context)
    assert "Please enter your username:" in update.message.replied_text


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_username():
    update = DummyUpdate("testuser")
    context = DummyContext()
    context.user_data = {}

    await handle_username(update, context)
    assert context.user_data["username"] == "testuser"
    assert "Please enter your password:" in update.message.replied_text


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_login_password():
    update = DummyUpdate("usertestpassword")
    context = DummyContext()
    context.user_data = {"username": "testuser"}

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "result": {"token": "valid_token"}
        }
        await handle_login_password(update, context)

    assert "Login successful!" in update.message.replied_text
