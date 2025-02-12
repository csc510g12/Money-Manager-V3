"""
This module provides user-related API routes for the Money Manager application.
"""

import datetime
from typing import Optional
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from loguru import logger
from api.utils.auth import verify_token
from config.config import MONGO_URI, TOKEN_ALGORITHM, TOKEN_SECRET_KEY

ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

router = APIRouter(prefix="/users", tags=["Users"])

# MongoDB setup
client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URI)
db = client.mmdb
users_collection = db.users
tokens_collection = db.tokens
accounts_collection = db.accounts
expenses_collection = db.expenses


class UserCreate(BaseModel):
    """Schema for creating a user."""

    username: str
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    password: Optional[str] = None
    currencies: Optional[list] = None


def format_id(document):
    """Format the MongoDB document ID to string."""
    document["_id"] = str(document["_id"])
    return document


def create_access_token(data: dict, expires_delta: datetime.timedelta):
    """Create an access token with an expiration time."""
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, TOKEN_SECRET_KEY, algorithm=TOKEN_ALGORITHM)
    return encoded_jwt


@router.post("/")
async def create_user(user: UserCreate):
    """Create a new user along with default accounts."""
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    if not user.username or not user.password:
        raise HTTPException(status_code=422, detail="Invalid credential")

    default_categories = {
        "Food": {"monthly_budget": 500.0},
        "Groceries": {"monthly_budget": 200.0},
        "Utilities": {"monthly_budget": 150.0},
        "Transport": {"monthly_budget": 100.0},
        "Shopping": {"monthly_budget": 300.0},
        "Miscellaneous": {"monthly_budget": 50.0},
    }

    default_currencies = ["USD", "INR", "GBP", "EUR"]

    salt = str(uuid4())[-12:]
    user.password = f"{user.password}{salt}"  # append salt
    query_password = f"{hash(user.password)}{salt}"  # hash
    logger.debug(
        f"Salt: {salt}, Password: {user.password}, Hashed+salt: {query_password}"
    ) # disable debug in production

    # Insert the new user
    user_data = {
        "username": user.username,
        "password": query_password,  # hash
        "categories": default_categories,
        "currencies": default_currencies,
    }
    result = await users_collection.insert_one(user_data)
    user_id = result.inserted_id
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Create default accounts for the user
    default_accounts = [
        {
            "user_id": str(user_id),
            "name": "Checking",
            "balance": 1000,
            "currency": "USD",
        },
        {
            "user_id": str(user_id),
            "name": "Savings",
            "balance": 10000,
            "currency": "USD",
        },
    ]

    await accounts_collection.insert_many(default_accounts)

    return {"message": "User and default accounts created successfully"}


@router.get("/")
async def get_user(token: str = Header(None)):
    """Get user details."""
    user_id = await verify_token(token)
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return format_id(user)


@router.put("/")
async def update_user(user_update: UserUpdate, token: str = Header(None)):
    """Update user information such as password, currencies."""
    user_id = await verify_token(token)
    update_fields = user_update.dict(exclude_unset=True)
    user: Optional[dict] = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if "password" in update_fields and update_fields["password"]:
        salt = str(uuid4())[-12:]
        query_password = f"{update_fields['password']}{salt}"  # append salt
        query_password = f"{hash(query_password)}{salt}"  # hash
        update_fields["password"] = query_password
        logger.debug(
            f"Salt: {salt}, Password: {update_fields['password']}, Hashed+salt: {query_password}"
        ) # disable debug in production

    if "currencies" in update_fields and isinstance(update_fields["currencies"], list):
        new_currencies = list(
            set(user.get("currencies", []) + update_fields["currencies"])
        )
        update_fields["currencies"] = new_currencies
    try:
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_fields}
        )
        if result.modified_count == 1:
            updated_user = await users_collection.find_one({"_id": ObjectId(user_id)})
            return {
                "message": "User updated successfully",
                "updated_user": format_id(updated_user),
            }
        raise HTTPException(status_code=400, detail="Nothing to modify")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update user") from e


@router.delete("/")
async def delete_user(token: str = Header(None)):
    """Delete a user and all associated accounts, tokens, and expenses."""
    user_id = await verify_token(token)
    await tokens_collection.delete_many({"user_id": user_id})
    await accounts_collection.delete_many({"user_id": user_id})
    await expenses_collection.delete_many({"user_id": user_id})
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 1:
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=500, detail="Failed to delete user")


@router.post("/token/")
async def create_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    token_expires: float = ACCESS_TOKEN_EXPIRE_MINUTES,
):
    """Create an access token for a user."""
    user = await users_collection.find_one({"username": form_data.username})
    salt = str(user["password"])[-12:]
    query_password = f"{hash(form_data.password+salt)}{salt}"
    logger.debug(
        f"Salt: {salt}, Password: {form_data.password}, Hashed+salt: {query_password}\n real password: {user['password']}"
    ) # disable debug in production

    if not user or user["password"] != query_password:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = datetime.timedelta(minutes=token_expires)
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "username": user["username"]},
        expires_delta=access_token_expires,
    )

    result = await tokens_collection.insert_one(
        {
            "user_id": str(user["_id"]),
            "token": access_token,
            "expires_at": datetime.datetime.now(datetime.UTC) + access_token_expires,
            "token_type": "bearer",
        },
    )

    if result.inserted_id:
        token_data = await tokens_collection.find_one({"_id": result.inserted_id})
        return {
            "message": "Token created successfully",
            "result": format_id(token_data),
        }


@router.get("/token/")
async def get_tokens(token: str = Header(None)):
    """
    Get all tokens for the authenticated user.

    Args:
        token (str): Authentication token.

    Returns:
        dict: List of all tokens for the user.
    """
    user_id = await verify_token(token)
    tokens = await tokens_collection.find({"user_id": user_id}).to_list(1000)
    formatted_tokens = [format_id(token) for token in tokens]
    # Convert datetime to ISO format in each token document
    for tok in formatted_tokens:
        if "expires_at" in tok and isinstance(tok["expires_at"], datetime.datetime):
            tok["expires_at"] = tok["expires_at"].isoformat()

    return {"tokens": formatted_tokens}


@router.get("/token/{token_id}")
async def get_token(token_id: str, token: str = Header(None)) -> dict:
    """
    Get a specific token's details.

    Args:
        token_id (str): The ID of the token.
        token (str): Authentication token.

    Returns:
        dict: Details of the specified token.
    """
    user_id = await verify_token(token)
    token_data = await tokens_collection.find_one(
        {"user_id": user_id, "_id": ObjectId(token_id)}
    )
    if not token_data:
        raise HTTPException(status_code=404, detail="Token not found")

    formatted_token = format_id(token_data)
    # Convert datetime to ISO format
    if "expires_at" in formatted_token and isinstance(
        formatted_token["expires_at"], datetime.datetime
    ):
        formatted_token["expires_at"] = formatted_token["expires_at"].isoformat()

    return formatted_token


@router.put("/token/{token_id}")
async def update_token(token_id: str, new_expiry: float, token: str = Header(None)):
    """
    Update the expiration time for the current token.

    Args:
        token_id (str): The ID of the token.
        new_expiry (float): New expiry time in minutes.
        token (str): Authentication token.

    Returns:
        dict: Success message or error.
    """
    user_id = await verify_token(token)
    updated_expiry = datetime.timedelta(minutes=new_expiry)
    new_expiry_time = datetime.datetime.now(datetime.UTC) + updated_expiry

    # Correct the filter to use _id for the token document
    result = await tokens_collection.update_one(
        {"user_id": user_id, "_id": ObjectId(token_id)},
        {"$set": {"expires_at": new_expiry_time}},
    )

    if result.modified_count == 1:
        return {"message": "Token expiration updated successfully"}

    raise HTTPException(status_code=500, detail="Failed to update token expiration")


@router.delete("/token/{token_id}")
async def delete_token(token_id: str, token: str = Header(None)):
    """
    Delete a specific token by its ID.

    Args:
        token_id (str): The ID of the token to be deleted.
        token (str): Authentication token for verifying the user.

    Returns:
        dict: Message indicating whether the token was successfully deleted.
    """
    user_id = await verify_token(token)
    result = await tokens_collection.delete_one(
        {"user_id": user_id, "_id": ObjectId(token_id)}
    )

    if result.deleted_count == 1:
        return {"message": "Token deleted successfully"}

    raise HTTPException(status_code=404, detail="Token not found")


@router.on_event("shutdown")
async def shutdown_db_client():
    """Shutdown event for MongoDB client."""
    client.close()
