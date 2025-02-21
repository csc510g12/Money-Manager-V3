import datetime
from unittest.mock import patch

import pytest
from bson import ObjectId  # Import ObjectId
from httpx import AsyncClient

from api.app import app


@pytest.fixture
def mock_db_user_not_found(monkeypatch):
    class MockCollection:
        async def find_one(self, query):
            return None

    monkeypatch.setattr(
        "api.routers.categories.users_collection", MockCollection()
    )


@pytest.fixture
def mock_db_category_not_found(monkeypatch):
    class MockCollection:
        async def find_one(self, query):
            return {"_id": ObjectId("507f1f77bcf86cd799439011")}

    monkeypatch.setattr(
        "api.routers.categories.users_collection", MockCollection()
    )


@pytest.mark.anyio
class TestCategoryCreation:
    async def test_create_category(self, async_client_auth: AsyncClient):
        # Create a new category
        response = await async_client_auth.post(
            "/categories/",
            json={"name": "Entertainment", "monthly_budget": 150.0},
        )
        assert response.status_code == 200, response.json()
        assert response.json()["message"] == "Category created successfully"

    async def test_duplicate_category(self, async_client_auth: AsyncClient):
        # Try creating the same category again
        response = await async_client_auth.post(
            "/categories/",
            json={"name": "Entertainment", "monthly_budget": 150.0},
        )
        assert response.status_code == 400, response.json()
        assert response.json()["detail"] == "Category already exists"

    async def test_invalid_category(self, async_client_auth: AsyncClient):
        # Try creating a category with invalid data (missing monthly_budget)
        response = await async_client_auth.post(
            "/categories/", json={"name": "InvalidCategory"}
        )
        assert response.status_code == 422, response.json()

    @patch(
        "api.routers.categories.verify_token",
        return_value="507f1f77bcf86cd799439011",
    )
    async def test_create_category_user_not_found(
        self,
        mock_verify_token,
        async_client_auth: AsyncClient,
        mock_db_user_not_found,
    ):
        # Simulate user not found scenario
        response = await async_client_auth.post(
            "/categories/",
            json={"name": "NonExistentUserCategory", "monthly_budget": 100.0},
        )
        assert response.status_code == 404, response.json()
        assert response.json()["detail"] == "User not found"

    async def test_create_category_missing_name(
        self, async_client_auth: AsyncClient
    ):
        response = await async_client_auth.post(
            "/categories/", json={"monthly_budget": 150.0}
        )
        assert response.status_code == 422

    async def test_create_category_missing_budget(
        self, async_client_auth: AsyncClient
    ):
        response = await async_client_auth.post(
            "/categories/", json={"name": "Entertainment"}
        )
        assert response.status_code == 422


@pytest.mark.anyio
class TestCategoryCases:
    async def test_empty_category_name(self, async_client_auth: AsyncClient):
        # Test creating a category with an empty name
        response = await async_client_auth.post(
            "/categories/", json={"name": "", "monthly_budget": 100.0}
        )
        assert response.status_code == 200, response.json()
        assert response.json()["message"] == "Category created successfully"

    async def test_zero_budget_category(self, async_client_auth: AsyncClient):
        # Test creating a category with a zero budget
        response = await async_client_auth.post(
            "/categories/", json={"name": "ZeroBudget", "monthly_budget": 0.0}
        )
        assert response.status_code == 200, response.json()
        assert response.json()["message"] == "Category created successfully"

    async def test_fetch_empty_category_list(
        self, async_client_auth: AsyncClient
    ):
        # Fetch all categories
        response = await async_client_auth.get("/categories/")
        assert response.status_code == 200, response.json()
        assert isinstance(response.json()["categories"], dict)

    async def test_delete_category_with_empty_name(
        self, async_client_auth: AsyncClient
    ):
        # Try deleting a category with an empty name
        response = await async_client_auth.delete("/categories/")
        assert response.status_code == 405, response.json()

    async def test_get_category_with_unusual_characters(
        self, async_client_auth: AsyncClient
    ):
        # Fetch a category with unusual characters in the name
        response = await async_client_auth.get("/categories/!@#$%^&*()")
        assert response.status_code == 404, response.json()

    async def test_create_category_with_long_name(
        self, async_client_auth: AsyncClient
    ):
        # Try creating a category with an exceptionally long name
        response = await async_client_auth.post(
            "/categories/",
            json={"name": "Entertainment" * 50, "monthly_budget": 100.0},
        )
        assert response.status_code == 200, response.json()

    async def test_create_category_with_special_characters(
        self, async_client_auth: AsyncClient
    ):
        # Try creating a category with special characters in the name
        response = await async_client_auth.post(
            "/categories/",
            json={"name": "!@#%Entertainment", "monthly_budget": 100.0},
        )
        assert response.status_code == 200, response.json()
        assert response.json()["message"] == "Category created successfully"


@pytest.mark.anyio
class TestCategoryUpdate:
    async def test_update_category(self, async_client_auth: AsyncClient):
        # Update the budget of an existing category
        response = await async_client_auth.put(
            "/categories/Entertainment", json={"monthly_budget": 200.0}
        )
        assert response.status_code == 200, response.json()
        assert response.json()["message"] == "Category updated successfully"

    async def test_update_non_existent_category(
        self, async_client_auth: AsyncClient
    ):
        # Try updating a non-existent category
        response = await async_client_auth.put(
            "/categories/NonExistentCategory", json={"monthly_budget": 300.0}
        )
        assert response.status_code == 404, response.json()
        assert response.json()["detail"] == "Category not found"

    async def test_update_category_with_no_changes(
        self, async_client_auth: AsyncClient
    ):
        # Update an existing category with the same data to ensure no errors
        response = await async_client_auth.put(
            "/categories/Entertainment", json={"monthly_budget": 150.0}
        )
        assert response.status_code == 200, response.json()
        assert response.json()["message"] == "Category updated successfully"

    async def test_update_category_negative_budget(
        self, async_client_auth: AsyncClient
    ):
        # Attempt to update a category with a negative budget
        response = await async_client_auth.put(
            "/categories/Entertainment", json={"monthly_budget": -50.0}
        )
        assert response.status_code == 400, response.json()
        assert response.json()["detail"] == "Monthly budget must be positive"

    @patch(
        "api.routers.categories.verify_token",
        return_value="507f1f77bcf86cd799439011",
    )
    async def test_update_category_not_found(
        self,
        mock_verify_token,
        async_client_auth: AsyncClient,
        mock_db_category_not_found,
    ):
        # Simulate category not found scenario
        response = await async_client_auth.put(
            "/categories/NonExistentCategory", json={"monthly_budget": 200.0}
        )
        assert response.status_code == 404, response.json()
        assert response.json()["detail"] == "Category not found"

    async def test_update_category_missing_budget(
        self, async_client_auth: AsyncClient
    ):
        response = await async_client_auth.put(
            "/categories/Entertainment", json={}
        )
        assert response.status_code == 422


@pytest.mark.anyio
class TestGetCategories:
    async def test_get_all_categories(self, async_client_auth: AsyncClient):
        # Fetch all categories
        response = await async_client_auth.get("/categories/")
        assert response.status_code == 200, response.json()
        assert isinstance(response.json()["categories"], dict)

    async def test_get_particular_category(
        self, async_client_auth: AsyncClient
    ):
        # Fetch a specific category by name
        response = await async_client_auth.get("/categories/Entertainment")
        assert response.status_code == 200, response.json()
        assert response.json()["category"]["monthly_budget"] == 150.0

    async def test_get_non_existent_category(
        self, async_client_auth: AsyncClient
    ):
        # Try fetching a non-existent category
        response = await async_client_auth.get(
            "/categories/NonExistentCategory"
        )
        assert response.status_code == 404, response.json()

    async def test_fetch_category_case_insensitive(
        self, async_client_auth: AsyncClient
    ):
        # Fetch a category using a different case to ensure case insensitivity
        response = await async_client_auth.get("/categories/entertainment")
        assert response.status_code == 404
        assert response.json()["detail"] == "Category not found"

    async def test_fetch_large_number_of_categories(
        self, async_client_auth: AsyncClient
    ):
        # Fetch all categories to test performance with a large list
        response = await async_client_auth.get("/categories/")
        assert response.status_code == 200, response.json()
        assert isinstance(response.json()["categories"], dict)
        assert len(response.json()["categories"]) >= 10


@pytest.mark.anyio
class TestCategoryDeletion:
    async def test_delete_category(self, async_client_auth: AsyncClient):
        # Delete an existing category
        response = await async_client_auth.delete("/categories/Entertainment")
        assert response.status_code == 200, response.json()
        assert response.json()["message"] == "Category deleted successfully"

    async def test_delete_non_existent_category(
        self, async_client_auth: AsyncClient
    ):
        # Try deleting a non-existent category
        response = await async_client_auth.delete(
            "/categories/NonExistentCategory"
        )
        assert response.status_code == 404, response.json()

    async def test_delete_category_case_insensitive(
        self, async_client_auth: AsyncClient
    ):
        # Delete a category using a different case to ensure case insensitivity
        response = await async_client_auth.delete("/categories/ENTERTAINMENT")
        assert response.status_code == 404, response.json()

    @patch(
        "api.routers.categories.verify_token",
        return_value="507f1f77bcf86cd799439011",
    )
    async def test_delete_category_not_found(
        self,
        mock_verify_token,
        async_client_auth: AsyncClient,
        mock_db_category_not_found,
    ):
        # Simulate category not found scenario
        response = await async_client_auth.delete(
            "/categories/NonExistentCategory"
        )
        assert response.status_code == 404, response.json()
        assert response.json()["detail"] == "Category not found"

    async def test_delete_category_invalid_name(
        self, async_client_auth: AsyncClient
    ):
        response = await async_client_auth.delete("/categories/invalid_name")
        assert response.status_code == 404


@pytest.mark.anyio
class TestAdditionalCategoryCases:
    async def test_create_multiple_categories_same_budget(
        self, async_client_auth: AsyncClient
    ):
        # Create multiple categories with the same budget value to ensure no conflicts
        categories = ["Food 1", "Transport 1", "Groceries 1"]
        for cat in categories:
            response = await async_client_auth.post(
                "/categories/", json={"name": cat, "monthly_budget": 100.0}
            )
            assert response.status_code == 200, response.json()
            assert (
                response.json()["message"] == "Category created successfully"
            )

    async def test_create_category_invalid_budget_type(
        self, async_client_auth: AsyncClient
    ):
        # Attempt to create a category with a non-numeric budget
        response = await async_client_auth.post(
            "/categories/",
            json={"name": "NonNumericBudget", "monthly_budget": "one hundred"},
        )
        assert response.status_code == 422, response.json()

    async def test_get_category_with_unusual_characters(
        self, async_client_auth: AsyncClient
    ):
        # Fetch a category with unusual characters in the name
        response = await async_client_auth.get("/categories/!(*@(@!()))")
        assert response.status_code == 404, response.json()

    async def test_get_non_existent_category_spl_char_spaces(
        self, async_client_auth: AsyncClient
    ):
        # Try fetching a non-existent category
        response = await async_client_auth.get("/categories/!(*@ (@!()))")
        assert response.status_code == 404, response.json()


@pytest.mark.anyio
class TestCategoryBoundaryValues:
    async def test_category_extremely_high_budget(
        self, async_client_auth: AsyncClient
    ):
        """
        Test creating a category with an extremely high monthly budget.
        """
        payload = {"name": "High Budget Category", "monthly_budget": 1e9}
        response = await async_client_auth.post("/categories/", json=payload)
        # Expect success if the number is within a valid range.
        assert response.status_code == 200, response.json()
