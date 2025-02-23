from unittest.mock import AsyncMock, patch

import pytest
from chat_base import DummyContext, DummyUpdate

from bots.telegram.accounts import (
    accounts_add,
    accounts_delete,
    accounts_update,
    accounts_view,
    confirm_delete_account,
    handle_account_name,
    handle_account_selection,
    handle_balance_update,
    handle_currency_selection,
    handle_initial_balance,
    handle_name_update,
    handle_update_type_selection,
)
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


@pytest.mark.asyncio(loop_scope="session")
async def test_accounts_view():
    update = DummyUpdate("/accounts_view")
    context = DummyContext()
    await accounts_view(update, context)
    assert "Failed to fetch accounts." in update.message.replied_text


@pytest.mark.asyncio(loop_scope="session")
async def test_accounts_add():
    update = DummyUpdate("/accounts_add")
    context = DummyContext()
    await accounts_add(update, context)
    assert "Please enter the account name:" in update.message.replied_text


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_account_name():
    update = DummyUpdate("Test Account")
    context = DummyContext()
    context.user_data = {}

    await handle_account_name(update, context)
    assert context.user_data["account_name"] == "Test Account"
    assert (
        "Please enter the initial balance for this account:"
        in update.message.replied_text
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_initial_balance():
    update = DummyUpdate("1000")
    context = DummyContext()
    context.user_data = {}

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "currencies": ["USD", "EUR"]
        }
        await handle_initial_balance(update, context)

    assert context.user_data["balance"] == "1000.0"
    assert "Please select the currency:" in update.message.replied_text


@pytest.mark.asyncio(loop_scope="session")
async def test_accounts_delete():
    update = DummyUpdate("/accounts_delete")
    context = DummyContext()

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"accounts": []}
        await accounts_delete(update, context)

    assert "No accounts found to delete." in update.message.replied_text


@pytest.mark.asyncio(loop_scope="session")
async def test_confirm_delete_account():
    update = DummyUpdate("delete_12345")
    update.callback_query = AsyncMock()
    update.callback_query.data = "delete_12345"
    context = DummyContext()
    context.user_data = {}

    await confirm_delete_account(update, context)
    assert (
        "Are you sure you want to delete"
        in update.callback_query.message.edit_text.call_args[0][0]
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_accounts_update():
    update = DummyUpdate("/accounts_update")
    context = DummyContext()

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"accounts": []}
        await accounts_update(update, context)

    assert "No accounts found to update." in update.message.replied_text


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_update_type_selection():
    update = DummyUpdate("change_name")
    update.callback_query = AsyncMock()
    update.callback_query.data = "change_name"
    context = DummyContext()

    await handle_update_type_selection(update, context)
    assert (
        "Please enter the new name:"
        in update.callback_query.message.edit_text.call_args[0][0]
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_name_update():
    update = DummyUpdate("New Account Name")
    context = DummyContext()
    context.user_data = {"account_id": "12345"}

    with patch("requests.put") as mock_put:
        mock_put.return_value.status_code = 200
        await handle_name_update(update, context)

    assert "Account name updated successfully!" in update.message.replied_text
