"""Utilities to manage authentication"""

from fastapi import HTTPException
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorClient

from config.config import MONGO_URI, TOKEN_ALGORITHM, TOKEN_SECRET_KEY

client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URI)
db = client.mmdb
users_collection = db.users
tokens_collection = db.tokens


async def verify_token(token: str):
    """Verify the validity of an access token."""
    if token is None:
        raise HTTPException(status_code=401, detail="Token is missing")
    try:
        payload = jwt.decode(token, TOKEN_SECRET_KEY, algorithms=[TOKEN_ALGORITHM])
        user_id = payload.get("sub")
        token_exists = await tokens_collection.find_one(
            {"user_id": user_id, "token": token}
        )
        if not token_exists:
            raise HTTPException(status_code=401, detail="Token does not exist")
        return user_id
    except JWTError as e:
        if "Signature has expired" in str(e):
            await tokens_collection.delete_one({"token": token})
            raise HTTPException(status_code=401, detail="Token has expired") from e
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        ) from e
