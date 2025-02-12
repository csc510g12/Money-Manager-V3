"""
Utility functions for database operations.
"""

import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

from config.config import MONGO_URI

# Shared MongoDB client
client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URI)
db = client.mmdb
users_collection = db.users
expenses_collection = db.expenses
accounts_collection = db.accounts
tokens_collection = db.tokens


async def fetch_data(
    user_id: str, from_date: Optional[datetime.date], to_date: Optional[datetime.date]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Fetch user data from the database based on user ID and date range.
    """
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=422,
            detail="Invalid date range: 'from_date' must be before 'to_date'",
        )

    from_dt = (
        datetime.datetime.combine(from_date, datetime.time.min) if from_date else None
    )
    to_dt = datetime.datetime.combine(to_date, datetime.time.max) if to_date else None

    query = {"user_id": user_id}
    if from_dt and to_dt:
        query["date"] = {"$gte": from_dt, "$lte": to_dt}  # type: ignore
    elif from_dt:
        query["date"] = {"$gte": from_dt}  # type: ignore
    elif to_dt:
        query["date"] = {"$lte": to_dt}  # type: ignore

    expenses = await expenses_collection.find(query).to_list(1000)
    accounts = await accounts_collection.find({"user_id": user_id}).to_list(100)
    user = await users_collection.find_one({"_id": ObjectId(user_id)})

    return expenses, accounts, user


def calculate_days_in_range(
    from_date: Optional[datetime.date],
    to_date: Optional[datetime.date],
    first_expense_date: Optional[datetime.date],
    last_expense_date: Optional[datetime.date],
) -> int:
    """Calculate number of days in a date range."""
    if from_date and to_date:
        days_in_range = (to_date - from_date).days + 1
    elif from_date:
        days_in_range = (
            (last_expense_date - from_date).days + 1
            if last_expense_date
            else (datetime.date.today() - from_date).days + 1
        )
    elif to_date:
        days_in_range = (
            (to_date - first_expense_date).days + 1
            if first_expense_date
            else (to_date - datetime.date(1970, 1, 1)).days + 1
        )
    else:
        days_in_range = 30

    return days_in_range
