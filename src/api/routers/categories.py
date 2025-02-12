"""
This module provides endpoints for managing categories of a particular user.
"""

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from api.utils.auth import verify_token
from config.config import MONGO_URI

router = APIRouter(prefix="/categories", tags=["Categories"])

# MongoDB setup
client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URI)
db = client.mmdb
users_collection = db.users


class CategoryCreate(BaseModel):
    """Schema for creating a new category."""

    name: str
    monthly_budget: float


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    monthly_budget: float


@router.post("/")
async def create_category(category: CategoryCreate, token: str = Header(None)):
    """
    Create a new category for the authenticated user.

    Args:
        category (CategoryCreate): Category details.
        token (str): Authentication token.

    Returns:
        dict: A message confirming category creation.
    """
    user_id = await verify_token(token)

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if "categories" not in user:
        user["categories"] = {}

    if category.name in user["categories"]:
        raise HTTPException(status_code=400, detail="Category already exists")

    user["categories"][category.name] = {"monthly_budget": category.monthly_budget}

    await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"categories": user["categories"]}}
    )

    return {"message": "Category created successfully"}


@router.put("/{category_name}")
async def update_category(
    category_name: str, category_update: CategoryUpdate, token: str = Header(None)
):
    """
    Update an existing category's monthly budget.

    Args:
        category_name (str): The name of the category to update.
        category_update (CategoryUpdate): New category details.
        token (str): Authentication token.

    Returns:
        dict: A message confirming category update.
    """
    user_id = await verify_token(token)

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user or "categories" not in user or category_name not in user["categories"]:
        raise HTTPException(status_code=404, detail="Category not found")

    if category_update.monthly_budget < 0:
        raise HTTPException(status_code=400, detail="Monthly budget must be positive")

    user["categories"][category_name]["monthly_budget"] = category_update.monthly_budget

    await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"categories": user["categories"]}}
    )

    return {"message": "Category updated successfully"}


@router.get("/")
async def get_all_categories(token: str = Header(None)):
    """
    Get all categories for the authenticated user.

    Args:
        token (str): Authentication token.

    Returns:
        dict: List of all categories.
    """
    user_id = await verify_token(token)

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user or "categories" not in user:
        return {"categories": []}

    return {"categories": user["categories"]}


@router.get("/{category_name}")
async def get_category(category_name: str, token: str = Header(None)):
    """
    Get details of a specific category for the authenticated user.

    Args:
        category_name (str): The name of the category to fetch.
        token (str): Authentication token.

    Returns:
        dict: The category details.
    """
    user_id = await verify_token(token)

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user or "categories" not in user or category_name not in user["categories"]:
        raise HTTPException(status_code=404, detail="Category not found")

    return {"category": user["categories"][category_name]}


@router.delete("/{category_name}")
async def delete_category(category_name: str, token: str = Header(None)):
    """
    Delete an existing category for the authenticated user.

    Args:
        category_name (str): The name of the category to delete.
        token (str): Authentication token.

    Returns:
        dict: A message confirming category deletion.
    """
    user_id = await verify_token(token)

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user or "categories" not in user or category_name not in user["categories"]:
        raise HTTPException(status_code=404, detail="Category not found")

    del user["categories"][category_name]

    await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"categories": user["categories"]}}
    )

    return {"message": "Category deleted successfully"}
