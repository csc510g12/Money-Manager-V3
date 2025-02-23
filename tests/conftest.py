# test_expenses.py
import asyncio
from asyncio import get_event_loop
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from api.app import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(scope="session")
async def async_client_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create a user and log in to use for expenses tests
        await client.post(
            "/users/",
            json={"username": "testuser", "password": "testpassword"},
        )
        response = await client.post(
            "/users/token/",
            data={"username": "testuser", "password": "testpassword"},
        )
        token = response.json()["result"]["token"]
        client.headers.update({"token": token})

        account_response = await client.get("/accounts/")

        accounts = account_response.json()["accounts"]
        for account in accounts:
            if account["name"] == "Checking":
                account_id = account["_id"]
                # Update the balance of the Checking account
                await client.put(
                    f"/accounts/{account_id}",
                    json={
                        "balance": 1000.0,
                        "currency": "USD",
                        "name": "Checking",
                    },
                )

        yield client

        # Teardown: Delete the user after the tests in this module
        response = await client.delete("/users/")
        assert response.status_code == 200, response.json()
        assert (
            response.json()["message"] == "User deleted successfully"
        ), response.json()
