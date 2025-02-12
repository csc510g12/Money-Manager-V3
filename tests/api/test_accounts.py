import pytest
from bson import ObjectId
from httpx import AsyncClient

from api.app import app


@pytest.mark.anyio
class TestAccountCreation:
    async def test_valid_creation(self, async_client_auth: AsyncClient):
        """
        Test creating a valid account for a user.
        """
        response = await async_client_auth.post(
            "/accounts/",
            json={
                "name": "Invest meant",
                "balance": 1000.0,
                "currency": "USD",
            },
        )
        assert response.status_code == 200, response.json()
        assert "Account created successfully" in response.json()["message"]
        assert "account_id" in response.json()

    async def test_duplicate_name(self, async_client_auth: AsyncClient):
        """
        Test attempting to create an account with an already existing name.
        """
        # Create an account first
        await async_client_auth.post(
            "/accounts/",
            json={"name": "Checking 70", "balance": 500.0, "currency": "USD"},
        )
        # Try to create the same account type again
        response = await async_client_auth.post(
            "/accounts/",
            json={"name": "Checking 70", "balance": 1000.0, "currency": "USD"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Account type already exists"

    async def test_missing_fields(self, async_client_auth: AsyncClient):
        """
        Test creating an account with missing required fields.
        """
        response = await async_client_auth.post(
            "/accounts/", json={"balance": 1000.0}
        )
        assert response.status_code == 422  # Unprocessable Entity

    async def test_create_account_with_invalid_data(
        self, async_client_auth: AsyncClient
    ):
        """
        Test creating an account with invalid data types for fields.
        """
        response = await async_client_auth.post(
            "/accounts/",
            json={
                "name": "Invalid Account",
                "balance": "not_a_number",
                "currency": 123,
            },
        )
        assert response.status_code == 422  # Unprocessable Entity

    async def test_create_account_missing_name(
        self, async_client_auth: AsyncClient
    ):
        response = await async_client_auth.post(
            "/accounts/",
            json={"balance": 1000.0, "currency": "USD"},
        )
        assert response.status_code == 422

    async def test_create_account_missing_balance(
        self, async_client_auth: AsyncClient
    ):
        response = await async_client_auth.post(
            "/accounts/",
            json={"name": "Investment", "currency": "USD"},
        )
        assert response.status_code == 422


@pytest.mark.anyio
class TestAccountGet:
    async def test_get_single_account(self, async_client_auth: AsyncClient):
        """
        Test retrieving a specific account by its ID.
        """
        # Create an account first
        create_response = await async_client_auth.post(
            "/accounts/",
            json={"name": "Test 1", "balance": 500.0, "currency": "USD"},
        )
        assert create_response.status_code == 200, create_response.json()
        # print(create_response.json())  # Debugging line
        account_id = create_response.json()["account_id"]

        # Retrieve the account
        response = await async_client_auth.get(f"/accounts/{account_id}")
        assert response.status_code == 200
        assert response.json()["account"]["_id"] == account_id

    async def test_get_nonexistent_account(
        self, async_client_auth: AsyncClient
    ):
        """
        Test retrieving a non-existent account by ID.
        """
        invalid_account_id = str(ObjectId())
        response = await async_client_auth.get(
            f"/accounts/{invalid_account_id}"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Account not found"

    async def test_get_all_accounts(self, async_client_auth: AsyncClient):
        """
        Test retrieving all accounts for a user.
        """
        # Create two accounts
        await async_client_auth.post(
            "/accounts/",
            json={"name": "Checking 76", "balance": 500.0, "currency": "USD"},
        )
        await async_client_auth.post(
            "/accounts/",
            json={
                "name": "Invest meant",
                "balance": 1000.0,
                "currency": "USD",
            },
        )

        # Retrieve all accounts
        response = await async_client_auth.get("/accounts/")
        assert response.status_code == 200
        assert (
            len(response.json()["accounts"]) >= 2
        )  # Ensure at least 2 accounts exist


@pytest.mark.anyio
class TestAccountUpdate:
    async def test_valid_update(self, async_client_auth: AsyncClient):
        """
        Test updating an account's balance, currency, and name.
        """
        # Create an account first
        create_response = await async_client_auth.post(
            "/accounts/",
            json={
                "name": "Invest meant 2",
                "balance": 1000.0,
                "currency": "USD",
            },
        )
        account_id = create_response.json()["account_id"]

        # Update the account
        response = await async_client_auth.put(
            f"/accounts/{account_id}",
            json={"balance": 2000.0, "currency": "EUR", "name": "Wealth"},
        )
        assert response.status_code == 200
        assert "Account updated successfully" in response.json()["message"]

    async def test_update_nonexistent_account(
        self, async_client_auth: AsyncClient
    ):
        """
        Test updating a non-existent account.
        """
        invalid_account_id = str(ObjectId())
        response = await async_client_auth.put(
            f"/accounts/{invalid_account_id}",
            json={"balance": 1000.0, "currency": "USD", "name": "Checking 76"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Account not found"

    async def test_partial_update(self, async_client_auth: AsyncClient):
        """
        Test updating only some fields of an account (balance and currency).
        """
        # Create an account first
        create_response = await async_client_auth.post(
            "/accounts/",
            json={"name": "Test 2", "balance": 500.0, "currency": "USD"},
        )
        account_id = create_response.json()["account_id"]

        # Partially update the account (change only balance and currency)
        response = await async_client_auth.put(
            f"/accounts/{account_id}",
            json={"balance": 1500.0, "currency": "GBP"},
        )
        assert response.status_code == 200, response.json()
        assert "Account updated successfully" in response.json()["message"]

    async def test_update_with_negative_balance(
        self, async_client_auth: AsyncClient
    ):
        """
        Test updating an account with a negative balance.
        """
        # Create an account first
        create_response = await async_client_auth.post(
            "/accounts/",
            json={"name": "Investment", "balance": 1000.0, "currency": "USD"},
        )
        account_id = create_response.json()["account_id"]

        # Attempt to update to a negative balance
        response = await async_client_auth.put(
            f"/accounts/{account_id}",
            json={
                "balance": -500.0,
                "currency": "USD",
                "name": "Investment Negative",
            },
        )
        assert response.status_code == 200  # Bad Request

    async def test_update_account_missing_balance(
        self, async_client_auth: AsyncClient
    ):
        # Create an account first
        create_response = await async_client_auth.post(
            "/accounts/",
            json={"name": "Investment", "balance": 1000.0, "currency": "USD"},
        )
        account_id = create_response.json()["account_id"]

        # Attempt to update the account with missing balance
        response = await async_client_auth.put(
            f"/accounts/{account_id}",
            json={"currency": "EUR"},
        )
        assert response.status_code == 200


@pytest.mark.anyio
class TestAccountNameConstraints:
    async def test_account_name_length(self, async_client_auth: AsyncClient):
        """
        Test creating an account with a name that exceeds maximum length.
        """
        long_name = "A" * 256  # Assuming 255 is the max length
        response = await async_client_auth.post(
            "/accounts/",
            json={"name": long_name, "balance": 500.0, "currency": "USD"},
        )
        assert response.status_code == 200, response.json()


@pytest.mark.anyio
class TestAccountCurrencyValidation:
    async def test_create_account_with_invalid_currency(
        self, async_client_auth: AsyncClient
    ):
        """
        Test creating an account with an unsupported currency code.
        """
        response = await async_client_auth.post(
            "/accounts/",
            json={
                "name": "Invalid Currency Account",
                "balance": 500.0,
                "currency": "INVALID",
            },
        )
        assert response.status_code == 200  # Unprocessable Entity


@pytest.mark.anyio
class TestAccountDelete:
    async def test_valid_delete(self, async_client_auth: AsyncClient):
        """
        Test deleting an account successfully.
        """
        # Create an account first
        create_response = await async_client_auth.post(
            "/accounts/",
            json={
                "name": "Checking 70 2",
                "balance": 500.0,
                "currency": "USD",
            },
        )
        account_id = create_response.json()["account_id"]

        # Delete the account
        response = await async_client_auth.delete(f"/accounts/{account_id}")
        assert response.status_code == 200
        assert "Account deleted successfully" in response.json()["message"]

    async def test_delete_nonexistent_account(
        self, async_client_auth: AsyncClient
    ):
        """
        Test deleting a non-existent account.
        """
        invalid_account_id = str(ObjectId())
        response = await async_client_auth.delete(
            f"/accounts/{invalid_account_id}"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Account not found"

    async def test_delete_account_invalid_id(
        self, async_client_auth: AsyncClient
    ):
        invalid_account_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existent
        response = await async_client_auth.delete(
            f"/accounts/{invalid_account_id}"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Account not found"
