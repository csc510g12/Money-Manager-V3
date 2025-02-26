# test_user_expenses.py
import datetime
from copy import deepcopy

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from api.app import app
from config.config import TOKEN_ALGORITHM, TOKEN_SECRET_KEY


@pytest.mark.anyio
class TestUserCreation:
    async def test_invalid_data(self, async_client: AsyncClient):
        response = await async_client.post(
            "/users/", json={"username": "", "password": ""}  # Invalid data
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "Invalid credential"

    async def test_valid(self, async_client: AsyncClient):
        response = await async_client.post(
            "/users/",
            json={"username": "usertestuser", "password": "usertestpassword"},
        )
        assert response.status_code == 200, response.json()
        assert (
            response.json()["message"]
            == "User and default accounts created successfully"
        )

    async def test_duplicate(self, async_client: AsyncClient):
        response = await async_client.post(
            "/users/",
            json={"username": "usertestuser", "password": "usertestpassword"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Username already exists"

    async def test_missing_username(self, async_client: AsyncClient):
        response = await async_client.post(
            "/users/", json={"username": "", "password": "password"}
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "Invalid credential"

    async def test_missing_password(self, async_client: AsyncClient):
        response = await async_client.post(
            "/users/", json={"username": "username", "password": ""}
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "Invalid credential"


@pytest.mark.anyio
class TestTokenCreation:
    async def test_create_token_invalid_credentials(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/users/token/",
            data={"username": "usertestuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"

    async def test_verify_token_non_existence(self, async_client: AsyncClient):
        response = await async_client.post(
            "/users/token/",
            data={"username": "usertestuser", "password": "usertestpassword"},
        )
        assert response.status_code == 200, response
        token_id = response.json()["result"]["_id"]
        token = response.json()["result"]["token"]
        response = await async_client.delete(
            f"/users/token/{token_id}", headers={"token": token}
        )
        assert response.status_code == 200, response
        response = await async_client.get("/users/", headers={"token": token})
        assert response.status_code == 401, response.json()
        assert response.json()["detail"] == "Token does not exist"

    async def test_create_token(self, async_client: AsyncClient):
        response = await async_client.post(
            "/users/token/",
            data={"username": "usertestuser", "password": "usertestpassword"},
        )
        assert response.status_code == 200
        assert "_id" in response.json()["result"]
        assert response.json()["result"]["token_type"] == "bearer"
        # Save token for future tests
        # async_client.headers.update({"Authorization": f"Bearer {response.json()['result']['token']}"})
        async_client.headers.update(
            {"token": response.json()["result"]["token"]}
        )

    async def test_create_token_missing_username(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/users/token/",
            data={"username": "", "password": "password"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"

    async def test_create_token_missing_password(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/users/token/",
            data={"username": "username", "password": ""},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.anyio
class TestTokenGetter:
    async def test_get_tokens(self, async_client: AsyncClient):
        response = await async_client.get("/users/token/")
        assert response.status_code == 200
        assert "tokens" in response.json()
        assert isinstance(response.json()["tokens"], list)

    async def test_get_token(self, async_client: AsyncClient):
        response = await async_client.get("/users/token/")
        assert response.status_code == 200
        token_id = response.json()["tokens"][0]["_id"]
        response = await async_client.get(f"/users/token/{token_id}")
        assert response.status_code == 200
        assert response.json()["_id"] == token_id

    async def test_token_expired(self, async_client: AsyncClient):
        # Create a fake token with an expired timestamp
        payload = {
            "sub": "507f1f77bcf86cd799439011",
            "username": "expired_user",
            "exp": datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1),
        }
        expired_token = jwt.encode(
            payload, TOKEN_SECRET_KEY, algorithm=TOKEN_ALGORITHM
        )
        headers = {"token": expired_token}

        # Try to access user details with the expired token
        response = await async_client.get("/users/", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Token has expired"


@pytest.mark.anyio
class TestTokenUpdate:
    async def test_update_token_expiration(self, async_client: AsyncClient):
        response = await async_client.get("/users/token/")
        assert response.status_code == 200
        token_id = response.json()["tokens"][0]["_id"]
        response = await async_client.put(
            f"/users/token/{token_id}", params={"new_expiry": 60}
        )
        assert response.status_code == 200, response.json()
        assert (
            response.json()["message"]
            == "Token expiration updated successfully"
        )


@pytest.mark.anyio
class TestTokenDelete:
    async def test_delete_token(self, async_client: AsyncClient):
        response = await async_client.post(
            "/users/token/",
            data={"username": "usertestuser", "password": "usertestpassword"},
        )
        assert response.status_code == 200
        token_id = response.json()["result"]["_id"]
        response = await async_client.delete(f"/users/token/{token_id}")
        assert response.status_code == 200, response
        assert (
            response.json()["message"] == "Token deleted successfully"
        ), response.json()

        response = await async_client.get(f"/users/token/{token_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Token not found"


@pytest.mark.anyio
class TestUserGetter:
    async def test_get_user(self, async_client: AsyncClient):
        response = await async_client.get("/users/")
        assert response.status_code == 200
        assert "username" in response.json()
        assert response.json()["username"] == "usertestuser"


@pytest.mark.anyio
class TestUserUpdate:
    async def test_empty(self, async_client: AsyncClient):
        response = await async_client.put("/users/", json={})
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to update user"

    async def test_invalid_input(self, async_client: AsyncClient):
        response = await async_client.put(
            "/users/", json={"invalid?": "haha..."}
        )
        assert response.status_code == 500, response.json()
        assert response.json()["detail"] == "Failed to update user"

    async def test_update_password(self, async_client: AsyncClient):
        response = await async_client.put(
            "/users/",
            json={
                "password": "pswd",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "User updated successfully"
        assert "updated_user" in response.json()

    async def test_valid(self, async_client: AsyncClient):
        response = await async_client.put(
            "/users/",
            json={
                "password": "newpassword",
                "currencies": ["INR"],
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "User updated successfully"
        assert "updated_user" in response.json()


@pytest.mark.anyio
class TestUserUnauthenticated:
    async def test_login_with_nonexistent_user(
        self, async_client: AsyncClient
    ):
        # Create a fake token for a nonexistent user
        payload = {
            "sub": None,
            "username": "nonexistent_user",
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=30),
        }
        fake_token = jwt.encode(
            payload, TOKEN_SECRET_KEY, algorithm=TOKEN_ALGORITHM
        )
        headers = {"token": fake_token}

        # Try to access user details with the fake token
        response = await async_client.get("/users/", headers=headers)
        assert response.status_code == 401, response.json()
        assert (
            response.json()["detail"] == "Invalid authentication credentials"
        ), response.json()

    async def test_get_user(self, async_client: AsyncClient):
        # Make a deep copy of the original headers to restore later
        original_headers = deepcopy(async_client.headers)

        # Temporarily remove the "token" header
        if "token" in async_client.headers:
            async_client.headers.pop("token")

        response = await async_client.get("/users/")
        assert response.status_code == 401
        assert response.json()["detail"] == "Token is missing"

        # Restore the original headers
        async_client.headers.update(original_headers)

    async def test_delete_user(self, async_client: AsyncClient):
        # Make a deep copy of the original headers to restore later
        original_headers = deepcopy(async_client.headers)

        # Temporarily remove the "token" header
        if "token" in async_client.headers:
            async_client.headers.pop("token")

        response = await async_client.delete("/users/")
        assert response.status_code == 401
        assert response.json()["detail"] == "Token is missing"

        # Restore the original headers
        async_client.headers.update(original_headers)


@pytest.mark.anyio
class TestUserDelete:
    async def test_delete_user(self, async_client: AsyncClient):
        response = await async_client.delete("/users/")
        assert response.status_code == 200, response.json()
        assert (
            response.json()["message"] == "User deleted successfully"
        ), response.json()

