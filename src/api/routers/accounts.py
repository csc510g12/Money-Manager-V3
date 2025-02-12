"""
This module provides account-related API routes for the Money Manager application.
"""

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from api.utils.auth import verify_token
from config.config import MONGO_URI

router = APIRouter(prefix="/accounts", tags=["Accounts"])

# MongoDB setup
client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URI)
db = client.mmdb
accounts_collection = db.accounts


class AccountCreate(BaseModel):
    """Schema for creating a new account."""

    name: str
    balance: float
    currency: str


class AccountUpdate(BaseModel):
    """Schema for updating account information."""

    name: Optional[str] = None
    balance: Optional[float] = None
    currency: Optional[str] = None


@router.post("/")
async def create_account(account: AccountCreate, token: str = Header(None)):
    """
    Create a new account for the authenticated user.

    Args:
        account (AccountCreate): The account details.
        token (str): Authentication token.

    Returns:
        dict: A message confirming the account creation.
    """
    user_id = await verify_token(token)
    existing_account = await accounts_collection.find_one(
        {"user_id": user_id, "name": account.name}
    )

    if existing_account:
        raise HTTPException(status_code=400, detail="Account type already exists")

    account_data = {
        "user_id": user_id,
        "name": account.name,
        "balance": account.balance,
        "currency": account.currency.upper(),
    }

    result = await accounts_collection.insert_one(account_data)
    if result.inserted_id:
        return {
            "message": "Account created successfully",
            "account_id": str(result.inserted_id),
        }

    raise HTTPException(status_code=500, detail="Failed to create account")


@router.get("/")
async def get_accounts(token: str = Header(None)):
    """
    Get all accounts for the authenticated user.

    Args:
        token (str): Authentication token.

    Returns:
        dict: A list of all accounts for the user.
    """
    user_id = await verify_token(token)
    accounts = await accounts_collection.find({"user_id": user_id}).to_list(100)
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts found for the user")

    # Convert ObjectId to string for better readability
    formatted_accounts = [
        {**account, "_id": str(account["_id"])} for account in accounts
    ]
    return {"accounts": formatted_accounts}


@router.get("/{account_id}")
async def get_account(account_id: str, token: str = Header(None)):
    """
    Get details of a specific account for the authenticated user.

    Args:
        account_id (str): The account ID.
        token (str): Authentication token.

    Returns:
        dict: The account details.
    """
    user_id = await verify_token(token)
    account = await accounts_collection.find_one(
        {"_id": ObjectId(account_id), "user_id": user_id}
    )

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account["_id"] = str(
        account["_id"]
    )  # Convert ObjectId to string for better readability
    return {"account": account}


@router.put("/{account_id}")
async def update_account(
    account_id: str, account_update: AccountUpdate, token: str = Header(None)
):
    """
    Edit an existing account for the authenticated user.

    Args:
        account_id (str): The account ID.
        account_update (AccountUpdate): The updated account details.
        token (str): Authentication token.

    Returns:
        dict: A message confirming the account update.
    """
    user_id = await verify_token(token)
    account = await accounts_collection.find_one(
        {"_id": ObjectId(account_id), "user_id": user_id}
    )

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account_update.currency:
        account_update.currency = account_update.currency.upper()

    # Update account details (balance, currency, and name)

    update_data = {}
    if account_update.balance:
        update_data["balance"] = float(account_update.balance)  # type: ignore
    if account_update.currency:
        update_data["currency"] = account_update.currency  # type: ignore
    if account_update.name:
        update_data["name"] = account_update.name  # type: ignore

    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    result = await accounts_collection.update_one(
        {"_id": ObjectId(account_id)}, {"$set": update_data}
    )

    if result.modified_count == 1:
        return {"message": "Account updated successfully"}

    raise HTTPException(status_code=500, detail="Failed to update account")


@router.delete("/{account_id}")
async def delete_account(account_id: str, token: str = Header(None)):
    """
    Delete an existing account for the authenticated user.

    Args:
        account_id (str): The account ID.
        token (str): Authentication token.

    Returns:
        dict: A message confirming the account deletion.
    """
    user_id = await verify_token(token)
    account = await accounts_collection.find_one(
        {"_id": ObjectId(account_id), "user_id": user_id}
    )

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    result = await accounts_collection.delete_one({"_id": ObjectId(account_id)})

    if result.deleted_count == 1:
        return {"message": "Account deleted successfully"}

    raise HTTPException(status_code=500, detail="Failed to delete account")
