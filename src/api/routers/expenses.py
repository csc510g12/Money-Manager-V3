"""
This module provides endpoints for managing user expenses in the Money Manager application.
"""

import datetime
from typing import Optional

from bson import ObjectId
from currency_converter import CurrencyConverter  # type: ignore
from fastapi import APIRouter, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from api.utils.auth import verify_token
from config.config import MONGO_URI

currency_converter = CurrencyConverter()

router = APIRouter(prefix="/expenses", tags=["Expenses"])

# MongoDB setup
client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URI)
db = client.mmdb
users_collection = db.users
expenses_collection = db.expenses
accounts_collection = db.accounts


def format_id(document):
    """Convert MongoDB document ID to string."""
    document["_id"] = str(document["_id"])
    return document


def convert_currency(amount, from_cur, to_cur):
    """Convert currency using the CurrencyConverter library."""
    if from_cur == to_cur:
        return amount
    try:
        return currency_converter.convert(amount, from_cur, to_cur)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Currency conversion failed: {str(e)}"
        ) from e


class ExpenseCreate(BaseModel):
    """Model for creating an expense."""

    amount: float
    currency: str
    category: str
    description: Optional[str] = None
    account_name: str = "Checking"
    date: Optional[datetime.datetime] = None


class ExpenseUpdate(BaseModel):
    """Model for updating an expense."""

    amount: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    # TODO: add account_name changing capability also
    date: Optional[datetime.datetime] = None


@router.post("/")
async def add_expense(expense: ExpenseCreate, token: str = Header(None)):
    """
    Add a new expense for the user.

    Args:
        expense (ExpenseCreate): Expense details.
        token (str): Authentication token.

    Returns:
        dict: Message with expense details and updated balance.
    """
    user_id = await verify_token(token)
    account = await accounts_collection.find_one(
        {"user_id": user_id, "name": expense.account_name}
    )
    if not account:
        raise HTTPException(status_code=400, detail="Invalid account type")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    expense.currency = expense.currency.upper()
    if expense.currency not in user["currencies"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Currency type is not added to user account. "
                f"Available currencies are {user['currencies']}"
            ),
        )
    converted_amount = convert_currency(
        expense.amount, expense.currency, account["currency"]
    )

    if account["balance"] < converted_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance in {expense.account_name} account",
        )

    if expense.category not in user["categories"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Category is not present in the user account. "
                f"Available categories are {list(user['categories'])}"
            ),
        )

    # Deduct amount from user's account balance
    new_balance = account["balance"] - converted_amount
    await accounts_collection.update_one(
        {"_id": account["_id"]}, {"$set": {"balance": new_balance}}
    )

    # Convert date to datetime object or use current datetime if none is provided
    expense_date = expense.date or datetime.datetime.now(datetime.timezone.utc)
    # Record the expense
    expense_data = expense.dict()
    expense_data.update(
        {
            "user_id": user_id,
            "date": expense_date,
        }
    )
    result = await expenses_collection.insert_one(expense_data)

    if result.inserted_id:
        expense_data["date"] = expense_date  # Ensure consistent formatting for response
        return {
            "message": "Expense added successfully",
            "expense": format_id(expense_data),
            "balance": new_balance,
        }
    raise HTTPException(status_code=500, detail="Failed to add expense")


@router.get("/")
async def get_expenses(token: str = Header(None)):
    """
    Get all expenses for a user.

    Args:
        token (str): Authentication token.

    Returns:
        dict: List of expenses.
    """
    user_id = await verify_token(token)
    expenses = await expenses_collection.find({"user_id": user_id}).to_list(1000)
    formatted_expenses = [format_id(expense) for expense in expenses]
    return {"expenses": formatted_expenses}


@router.get("/{expense_id}")
async def get_expense(expense_id: str, token: str = Header(None)):
    """
    Get a specific expense by ID.

    Args:
        expense_id (str): ID of the expense.
        token (str): Authentication token.

    Returns:
        dict: Details of the specified expense.
    """
    user_id = await verify_token(token)
    expense = await expenses_collection.find_one(
        {"user_id": user_id, "_id": ObjectId(expense_id)}
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return format_id(expense)


@router.delete("/all")
async def delete_all_expenses(token: str = Header(None)):
    """
    Delete all expenses for the authenticated user and update account balances.

    Args:
        token (str): Authentication token.

    Returns:
        dict: Message indicating the number of expenses deleted.
    """
    user_id = await verify_token(token)

    # Retrieve all expenses for the user before deletion
    expenses = await expenses_collection.find({"user_id": user_id}).to_list(None)
    if not expenses:
        raise HTTPException(status_code=404, detail="No expenses found to delete")

    # Organize expenses by account name to sum them for each account
    account_adjustments: dict[str, float] = {}
    for expense in expenses:
        account_name = expense.get("account_name")
        amount = expense.get("amount", 0)

        # Find the account ID by name
        account = await accounts_collection.find_one(
            {"name": account_name, "user_id": user_id}
        )
        if account:
            account_id = account["_id"]
            if account_id in account_adjustments:
                account_adjustments[account_id] += amount
            else:
                account_adjustments[account_id] = amount

    # Update each account's balance
    for account_id, total_expense_amount in account_adjustments.items():
        await accounts_collection.update_one(
            {"_id": account_id, "user_id": user_id},
            {"$inc": {"balance": total_expense_amount}},
        )

    # Delete all expenses
    result = await expenses_collection.delete_many({"user_id": user_id})

    return {"message": f"{result.deleted_count} expenses deleted successfully"}


@router.delete("/{expense_id}")
async def delete_expense(expense_id: str, token: str = Header(None)):
    """
    Delete an expense by ID.

    Args:
        expense_id (str): ID of the expense to delete.
        token (str): Authentication token.

    Returns:
        dict: Message with updated balance.
    """
    user_id = await verify_token(token)
    expense = await expenses_collection.find_one({"_id": ObjectId(expense_id)})

    if not expense or expense["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Expense not found")

    account_name = expense["account_name"]
    account = await accounts_collection.find_one(
        {"user_id": user_id, "name": account_name}
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    amount = convert_currency(
        expense["amount"], expense["currency"], account["currency"]
    )

    # Refund the amount to user's account
    new_balance = account["balance"] + amount
    await accounts_collection.update_one(
        {"_id": account["_id"]}, {"$set": {"balance": new_balance}}
    )

    # Delete the expense
    result = await expenses_collection.delete_one({"_id": ObjectId(expense_id)})

    if result.deleted_count == 1:
        return {"message": "Expense deleted successfully", "balance": new_balance}
    raise HTTPException(status_code=500, detail="Failed to delete expense")


@router.put("/{expense_id}")
# pylint: disable=too-many-locals
async def update_expense(
    expense_id: str, expense_update: ExpenseUpdate, token: str = Header(None)
):
    """
    Update an expense by ID.

    Args:
        expense_id (str): ID of the expense to update.
        expense_update (ExpenseUpdate): Expense update details.
        token (str): Authentication token.

    Returns:
        dict: Message with updated expense and balance.
    """
    user_id = await verify_token(token)
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    expense = await expenses_collection.find_one({"_id": ObjectId(expense_id)})
    if not expense or expense["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Expense not found")

    update_fields: dict[str, str | float | datetime.datetime] = {}

    def validate_currency():
        if expense_update.currency:
            expense_update.currency = expense_update.currency.upper()
            if expense_update.currency not in user["currencies"]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Currency type is not added to user account. "
                        f"Available currencies are {user['currencies']}"
                    ),
                )
            update_fields["currency"] = expense_update.currency

    async def validate_amount():
        nonlocal new_balance
        if expense_update.amount is not None:
            update_fields["amount"] = expense_update.amount

            # Adjust the user's balance
            # Convert old and new amounts to the account currency to determine balance adjustment
            original_amount_converted = convert_currency(
                expense["amount"], expense["currency"], account["currency"]
            )
            new_amount_converted = convert_currency(
                expense_update.amount,
                expense_update.currency or expense["currency"],
                account["currency"],
            )

            difference = new_amount_converted - original_amount_converted
            new_balance = account["balance"] - difference

            if new_balance < 0:
                raise HTTPException(
                    status_code=400, detail="Insufficient balance to update the expense"
                )
            await accounts_collection.update_one(
                {"_id": account["_id"]}, {"$set": {"balance": new_balance}}
            )

    def validate_category():
        if expense_update.category:
            if expense_update.category not in user["categories"]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Category is not present in the user account. "
                        f"Available categories are {list(user['categories'])}"
                    ),
                )
            update_fields["category"] = expense_update.category

    def validate_description():
        if expense_update.description:
            update_fields["description"] = expense_update.description

    def validate_date():
        if expense_update.date:
            update_fields["date"] = expense_update.date

    # Run validations
    validate_currency()
    account_name = expense["account_name"]
    account = await accounts_collection.find_one(
        {"user_id": user_id, "name": account_name}
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    new_balance = account["balance"]
    await validate_amount()
    validate_category()
    validate_description()
    validate_date()

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await expenses_collection.update_one(
        {"_id": ObjectId(expense_id)}, {"$set": update_fields}
    )
    if result.modified_count == 1:
        updated_expense = await expenses_collection.find_one(
            {"_id": ObjectId(expense_id)}
        )
        return {
            "message": "Expense updated successfully",
            "updated_expense": format_id(updated_expense),
            "balance": new_balance,
        }
    raise HTTPException(status_code=500, detail="Failed to update expense")
