from unittest.mock import AsyncMock, patch
import pytest
from chat_base import DummyContext, DummyUpdate
from bots.telegram.transfers import (
    transfer_start,
    select_source,
    transfer_amount,
    confirm_transfer,
    send_confirmed_transfer,
)

@pytest.mark.asyncio(loop_scope="session")
async def test_transfer_start():
    update = DummyUpdate("/accounts_transfer")
    context = DummyContext()
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "accounts": [{"_id": "123", "name": "Checking"}]
        }
        await transfer_start(update, context, token="valid_token")
    assert "Select the source account:" in update.message.replied_text


@pytest.mark.asyncio(loop_scope="session")
async def test_select_source():
    update = DummyUpdate(callback_data="source_123")
    context = DummyContext()
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "accounts": [{"_id": "456", "name": "Savings"}]
        }
        await select_source(update, context, token="valid_token")
    assert context.user_data["source_account"] == "123"
    assert "Select the destination account:" in update.callback_query.message.text


@pytest.mark.asyncio(loop_scope="session")
async def test_transfer_amount():
    update = DummyUpdate(callback_data="dest_456")
    context = DummyContext()
    await transfer_amount(update, context, token="valid_token")
    assert context.user_data["dest_account"] == "456"
    assert "Enter the amount to transfer:" in update.callback_query.message.text


@pytest.mark.asyncio(loop_scope="session")
async def test_confirm_transfer():
    update = DummyUpdate("100")
    context = DummyContext()
    context.user_data = {
        "source_account": "123",
        "dest_account": "456",
    }
    await confirm_transfer(update, context, token="valid_token")
    assert context.user_data["amount"] == 100.0
    assert "Transfer 100.0 from account 123 to 456. Confirm?" in update.message.replied_text


@pytest.mark.asyncio(loop_scope="session")
async def test_send_confirmed_transfer():
    update = DummyUpdate(callback_data="confirm_yes")
    context = DummyContext()
    context.user_data = {
        "source_account": "123",
        "dest_account": "456",
        "amount": 100.0,
    }
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        await send_confirmed_transfer(update, context, token="valid_token")
    assert "Transfer successful!" in update.callback_query.message.text
