from unittest.mock import AsyncMock, patch

import pytest
from chat_base import DummyContext, DummyUpdate
from httpx import AsyncClient

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
from bots.telegram.transfers import (
    transfer_start,
    transfer_amount,
    select_source,
    confirm_transfer,
    send_confirmed_transfer,
)

@pytest.mark.asyncio(loop_scope="session")
async def test_transfer_start():
    update = DummyUpdate("/transfer")
    context = DummyContext()
    await transfer_start(update, context)
    assert "Select the source account:" in update.essage.replied_text

@pytest.mark.asyncio(loop_scope="session")
async def test_transfer_amount():
    update = DummyUpdate("")

    