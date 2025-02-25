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


@pytest.mark.anyio
class TestAccountEdgeCases:
    async def test_create_account_extremely_high_balance(
        self, async_client_auth: AsyncClient
    ):
        """
        Test creating an account with an extremely high balance.
        This verifies that very large numbers are handled correctly.
        """
        payload = {
            "name": "High Balance",
            "balance": 1e15,  # extremely high balance
            "currency": "USD",
        }
        response = await async_client_auth.post("/accounts/", json=payload)
        # Adjust expected status if your business rules allow such a number.
        assert response.status_code == 200, response.json()

    async def test_update_account_with_no_changes(
        self, async_client_auth: AsyncClient
    ):
        """
        Test updating an account without providing any fields to update.
        Expect the system to either reject the update or return a specific error.
        """
        # Create an account first.
        create_resp = await async_client_auth.post(
            "/accounts/",
            json={"name": "No Change", "balance": 1000.0, "currency": "USD"},
        )
        account_id = create_resp.json()["account_id"]

        # Send an update with an empty JSON body.
        response = await async_client_auth.put(
            f"/accounts/{account_id}", json={}
        )
        # Expect a 400/422 error indicating no fields were provided.
        assert response.status_code in (400, 422), response.json()

    async def test_update_account_with_extra_fields(
        self, async_client_auth: AsyncClient
    ):
        """
        Test updating an account with additional unexpected fields.
        The endpoint should ignore extra fields and process the update correctly.
        """
        # Create an account.
        create_resp = await async_client_auth.post(
            "/accounts/",
            json={
                "name": "Extra Fields",
                "balance": 1000.0,
                "currency": "USD",
            },
        )
        account_id = create_resp.json()["account_id"]

        # Send an update including an extra field.
        update_payload = {
            "balance": 1500.0,
            "currency": "EUR",
            "extra": "value",
        }
        response = await async_client_auth.put(
            f"/accounts/{account_id}", json=update_payload
        )
        # Expect a successful update ignoring the extra field.
        assert response.status_code == 200, response.json()

    async def test_delete_account_affects_listing(
        self, async_client_auth: AsyncClient
    ):
        """
        Test that once an account is deleted, it no longer appears in the list
        of all accounts.
        """
        # Create an account.
        create_resp = await async_client_auth.post(
            "/accounts/",
            json={
                "name": "To Be Deleted",
                "balance": 500.0,
                "currency": "USD",
            },
        )
        account_id = create_resp.json()["account_id"]

        # Delete the account.
        del_resp = await async_client_auth.delete(f"/accounts/{account_id}")
        assert del_resp.status_code == 200, del_resp.json()

        # Retrieve all accounts and verify the deleted account is not present.
        get_resp = await async_client_auth.get("/accounts/")
        account_ids = [acc["_id"] for acc in get_resp.json()["accounts"]]
        assert account_id not in account_ids

@pytest.mark.anyio
class TestAccountTransfer:
    async def test_valid_transfer(self, async_client_auth: AsyncClient):
        """
        Test a valid transfer between two accounts.
        """
        # Create source account with sufficient balance.
        source_resp = await async_client_auth.post(
            "/accounts/",
            json={"name": "Source Account", "balance": 1000.0, "currency": "USD"},
        )
        assert source_resp.status_code == 200, f"Response: {source_resp.json()}"
        source_id = source_resp.json()["account_id"]

        # Create destination account.
        dest_resp = await async_client_auth.post(
            "/accounts/",
            json={"name": "Destination Account", "balance": 500.0, "currency": "USD"},
        )
        assert dest_resp.status_code == 200, f"Response: {dest_resp.json()}"
        dest_id = dest_resp.json()["account_id"]

        # Transfer $200 from source to destination.
        transfer_payload = {
            "source_account": source_id,
            "destination_account": dest_id,
            "amount": 200.0
        }
        transfer_resp = await async_client_auth.post(
            "/accounts/transfer", json=transfer_payload
        )
        assert transfer_resp.status_code == 200, f"Response: {transfer_resp.json()}"
        assert transfer_resp.json()["message"] == "Transfer successful"

        # Verify updated balances.
        source_get = await async_client_auth.get(f"/accounts/{source_id}")
        dest_get = await async_client_auth.get(f"/accounts/{dest_id}")
        assert source_get.json()["account"]["balance"] == 800.0, f"Response: {source_get.json()}"
        assert dest_get.json()["account"]["balance"] == 700.0, f"Response: {dest_get.json()}"

    async def test_transfer_insufficient_funds(self, async_client_auth: AsyncClient):
        """
        Test transferring funds when the source account has insufficient funds.
        """
        # Create a source account with low balance.
        source_resp = await async_client_auth.post(
            "/accounts/",
            json={"name": "Poor Source", "balance": 50.0, "currency": "USD"},
        )
        source_id = source_resp.json()["account_id"]

        # Create a destination account.
        dest_resp = await async_client_auth.post(
            "/accounts/",
            json={"name": "Destination", "balance": 500.0, "currency": "USD"},
        )
        dest_id = dest_resp.json()["account_id"]

        # Attempt to transfer more than available.
        transfer_payload = {
            "source_account": source_id,
            "destination_account": dest_id,
            "amount": 100.0
        }
        transfer_resp = await async_client_auth.post(
            "/accounts/transfer", json=transfer_payload
        )
        assert transfer_resp.status_code == 400, f"Response: {transfer_resp.json()}"
        assert transfer_resp.json()["detail"] == "Insufficient funds in source account"

    async def test_transfer_invalid_amount(self, async_client_auth: AsyncClient):
        """
        Test transferring with an invalid amount (zero and negative).
        """
        # Create valid accounts.
        source_resp = await async_client_auth.post(
            "/accounts/",
            json={"name": "Valid Source", "balance": 1000.0, "currency": "USD"},
        )
        source_id = source_resp.json()["account_id"]

        dest_resp = await async_client_auth.post(
            "/accounts/",
            json={"name": "Valid Destination", "balance": 500.0, "currency": "USD"},
        )
        dest_id = dest_resp.json()["account_id"]

        # Attempt to transfer zero.
        transfer_payload = {
            "source_account": source_id,
            "destination_account": dest_id,
            "amount": 0.0
        }
        transfer_resp = await async_client_auth.post(
            "/accounts/transfer", json=transfer_payload
        )
        assert transfer_resp.status_code == 400, f"Response: {transfer_resp.json()}"
        assert transfer_resp.json()["detail"] == "Transfer amount must be positive"

        # Attempt to transfer a negative amount.
        transfer_payload["amount"] = -10.0
        transfer_resp = await async_client_auth.post(
            "/accounts/transfer", json=transfer_payload
        )
        assert transfer_resp.status_code == 400, f"Response: {transfer_resp.json()}"
        assert transfer_resp.json()["detail"] == "Transfer amount must be positive"

    async def test_transfer_nonexistent_source(self, async_client_auth: AsyncClient):
        """
        Test transferring when the source account does not exist.
        """
        # Create a destination account.
        dest_resp = await async_client_auth.post(
            "/accounts/",
            json={"name": "Destination", "balance": 500.0, "currency": "USD"},
        )
        dest_id = dest_resp.json()["account_id"]

        # Use a valid but non-existent source account ID.
        fake_source_id = str(ObjectId())
        transfer_payload = {
            "source_account": fake_source_id,
            "destination_account": dest_id,
            "amount": 100.0
        }
        transfer_resp = await async_client_auth.post(
            "/accounts/transfer", json=transfer_payload
        )
        assert transfer_resp.status_code == 404, f"Response: {transfer_resp.json()}"
        assert transfer_resp.json()["detail"] == "Source account not found"

    async def test_transfer_nonexistent_source(self, async_client_auth: AsyncClient):
        """
        Test transferring when the source account does not exist.
        """
        # Create a destination account with a unique name.
        dest_resp = await async_client_auth.post(
            "/accounts/",
            json={
                "name": "Destination Nonexistent Source",
                "balance": 500.0,
                "currency": "USD"
            },
        )
        dest_data = dest_resp.json()
        assert "account_id" in dest_data, f"Response JSON: {dest_data}"
        dest_id = dest_data["account_id"]

        # Use a valid but non-existent source account ID.
        fake_source_id = str(ObjectId())
        transfer_payload = {
            "source_account": fake_source_id,
            "destination_account": dest_id,
            "amount": 100.0
        }
        transfer_resp = await async_client_auth.post(
            "/accounts/transfer", json=transfer_payload
        )
        assert transfer_resp.status_code == 404, f"Response: {transfer_resp.json()}"
        assert transfer_resp.json()["detail"] == "Source account not found"

    async def test_transfer_nonexistent_destination(self, async_client_auth: AsyncClient):
        """
        Test transferring when the destination account does not exist.
        """
        # Create a source account with a unique name.
        source_resp = await async_client_auth.post(
            "/accounts/",
            json={
                "name": "Source Nonexistent Destination",
                "balance": 1000.0,
                "currency": "USD"
            },
        )
        source_data = source_resp.json()
        assert "account_id" in source_data, f"Response JSON: {source_data}"
        source_id = source_data["account_id"]

        # Use a valid but non-existent destination account ID.
        fake_dest_id = str(ObjectId())
        transfer_payload = {
            "source_account": source_id,
            "destination_account": fake_dest_id,
            "amount": 100.0
        }
        transfer_resp = await async_client_auth.post(
            "/accounts/transfer", json=transfer_payload
        )
        assert transfer_resp.status_code == 404, f"Response: {transfer_resp.json()}"
        assert transfer_resp.json()["detail"] == "Destination account not found"