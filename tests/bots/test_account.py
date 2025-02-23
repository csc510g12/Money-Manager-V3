# from loguru import logger
# import pytest
# from unittest.mock import AsyncMock, patch
# from chat_base import DummyUpdate, DummyContext
# from bots.telegram.accounts import (
#     accounts_view,
#     accounts_add,
#     handle_account_name,
#     handle_initial_balance,
#     handle_currency_selection,
#     accounts_delete,
#     confirm_delete_account,
#     accounts_update,
#     handle_account_selection,
#     handle_update_type_selection,
#     handle_name_update,
#     handle_balance_update,
# )

# from telegram.ext import (
#     CallbackQueryHandler,
#     CommandHandler,
#     ContextTypes,
#     ConversationHandler,
#     MessageHandler,
#     filters,
# )

# @pytest.mark.asyncio(loop_scope="session")
# async def test_accounts_view(monkeypatch):
#     async def fake_get_user(update):
#         return {"username": "testuser"}

#     monkeypatch.setattr("bots.telegram.auth.get_user", fake_get_user)

#     update = DummyUpdate("/accounts_view")
#     context = DummyContext()

#     with patch("requests.get") as mock_get:
#         mock_get.return_value.status_code = 200
#         mock_get.return_value.json.return_value = {"accounts": []}
#         await accounts_view(update, context)

#     logger.debug(update.message.replied_text)
#     assert "Please /login or /signup to continue." in update.message.replied_text


# @pytest.mark.asyncio(loop_scope="session")
# async def test_accounts_add():
#     update = DummyUpdate("/accounts_add")
#     context = DummyContext()
#     await accounts_add(update, context)
#     assert "Please enter the account name:" in update.message.replied_text


# @pytest.mark.asyncio(loop_scope="session")
# async def test_handle_account_name():
#     update = DummyUpdate("Test Account")
#     context = DummyContext()
#     context.user_data = {}

#     await handle_account_name(update, context)
#     assert context.user_data["account_name"] == "Test Account"
#     assert (
#         "Please enter the initial balance for this account:"
#         in update.message.replied_text
#     )


# @pytest.mark.asyncio(loop_scope="session")
# async def test_handle_initial_balance():
#     update = DummyUpdate("1000")
#     context = DummyContext()
#     context.user_data = {}

#     with patch("requests.get") as mock_get:
#         mock_get.return_value.status_code = 200
#         mock_get.return_value.json.return_value = {
#             "currencies": ["USD", "EUR"]
#         }
#         await handle_initial_balance(update, context, "fake_token")

#     assert context.user_data["balance"] == "1000.0"
#     assert "Please select the currency:" in update.message.replied_text


# @pytest.mark.asyncio(loop_scope="session")
# async def test_handle_currency_selection():
#     update = DummyUpdate("currency_USD")
#     update.callback_query = AsyncMock()
#     update.callback_query.data = "currency_USD"
#     context = DummyContext()
#     context.user_data = {"account_name": "Test Account", "balance": "1000"}

#     with patch("requests.post") as mock_post:
#         mock_post.return_value.status_code = 200
#         result = await handle_currency_selection(update, context, "fake_token")

#     logger.debug(f"context.user_data: {context.user_data}")
#     assert result == ConversationHandler.END


# @pytest.mark.asyncio(loop_scope="session")
# async def test_accounts_delete():
#     update = DummyUpdate("/accounts_delete")
#     context = DummyContext()

#     with patch("requests.get") as mock_get:
#         mock_get.return_value.status_code = 200
#         mock_get.return_value.json.return_value = {"accounts": []}
#         await accounts_delete(update, context, "fake_token")

#     assert "No accounts found to delete." in update.message.replied_text


# @pytest.mark.asyncio(loop_scope="session")
# async def test_confirm_delete_account():
#     update = DummyUpdate("delete_12345")
#     update.callback_query = AsyncMock()
#     update.callback_query.data = "delete_12345"
#     context = DummyContext()
#     context.user_data = {}

#     await confirm_delete_account(update, context, "fake_token")
#     assert (
#         "Are you sure you want to delete"
#         in update.callback_query.message.edit_text.call_args[0][0]
#     )


# @pytest.mark.asyncio(loop_scope="session")
# async def test_accounts_update():
#     update = DummyUpdate("/accounts_update")
#     context = DummyContext()

#     with patch("requests.get") as mock_get:
#         mock_get.return_value.status_code = 200
#         mock_get.return_value.json.return_value = {"accounts": []}
#         await accounts_update(update, context, "fake_token")

#     assert "No accounts found to update." in update.message.replied_text


# @pytest.mark.asyncio(loop_scope="session")
# async def test_handle_update_type_selection():
#     update = DummyUpdate("change_name")
#     update.callback_query = AsyncMock()
#     update.callback_query.data = "change_name"
#     context = DummyContext()

#     await handle_update_type_selection(update, context)
#     assert (
#         "Please enter the new name:"
#         in update.callback_query.message.edit_text.call_args[0][0]
#     )


# @pytest.mark.asyncio(loop_scope="session")
# async def test_handle_name_update():
#     update = DummyUpdate("New Account Name")
#     context = DummyContext()
#     context.user_data = {"account_id": "12345"}

#     with patch("requests.put") as mock_put:
#         mock_put.return_value.status_code = 200
#         await handle_name_update(update, context, "fake_token")

#     assert "Account name updated successfully!" in update.message.replied_text
