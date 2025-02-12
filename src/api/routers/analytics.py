"""
This module provides analytics endpoints for retrieving and visualizing expense data.
"""

import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Response

from api.utils.auth import verify_token
from api.utils.db import calculate_days_in_range, fetch_data
from api.utils.plots import (
    create_budget_vs_actual,
    create_category_bar,
    create_category_pie,
    create_expense_bar,
    create_monthly_line,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/expense/bar")
async def expense_bar(
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
    token: str = Header(None),
):
    """Generate bar chart of daily expenses."""
    user_id = await verify_token(token)
    expenses, _, _ = await fetch_data(user_id, from_date, to_date)

    if not expenses:
        raise HTTPException(status_code=404, detail="No expenses found")

    buf = create_expense_bar(expenses, from_date, to_date)
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/category/pie")
async def category_pie(
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
    token: str = Header(None),
):
    """
    Endpoint to generate a pie chart of categories categorized by type.
    Returns a PNG image file directly.
    """
    user_id = await verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    expenses, _, _ = await fetch_data(user_id, from_date, to_date)

    if not expenses:
        raise HTTPException(
            status_code=404, detail="No expenses found for the specified period"
        )

    buf = create_category_pie(expenses, from_date, to_date)
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/expense/line-monthly", response_class=Response)
async def expense_line_monthly(
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
    token: str = Header(None),
):
    """
    Endpoint to generate a line chart of monthly expenses within a date range.
    Returns a PNG image file directly.
    """
    user_id = await verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    expenses, _, _ = await fetch_data(user_id, from_date, to_date)

    if not expenses:
        raise HTTPException(
            status_code=404, detail="No expenses found for the specified period"
        )

    buf = create_monthly_line(expenses, from_date, to_date)
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/category/bar", response_class=Response)
async def category_bar(
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
    token: str = Header(None),
):
    """
    Endpoint to generate a bar chart of expenses categorized by type within a date range.
    Returns a PNG image file directly.
    """
    user_id = await verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    expenses, _, _ = await fetch_data(user_id, from_date, to_date)

    if not expenses:
        raise HTTPException(
            status_code=404, detail="No expenses found for the specified period"
        )

    buf = create_category_bar(expenses, from_date, to_date)
    return Response(content=buf.getvalue(), media_type="image/png")


def prorate_budget(
    budget: float,
    from_date: Optional[datetime.date],
    to_date: Optional[datetime.date],
    first_expense_date: Optional[datetime.date],
    last_expense_date: Optional[datetime.date],
) -> float:
    """Prorate the budget based on the date range."""

    days_in_range = calculate_days_in_range(
        from_date, to_date, first_expense_date, last_expense_date
    )
    return (budget / 30) * days_in_range


@router.get("/budget/actual-vs-budget", response_class=Response)
async def budget_vs_actual(
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
    token: str = Header(None),
):
    """
    Endpoint to generate a bar chart comparing budgeted vs actual expenses within a date range.
    Returns a PNG image file directly.
    """
    user_id = await verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    expenses, _, user = await fetch_data(user_id, from_date, to_date)

    if not expenses:
        raise HTTPException(
            status_code=404, detail="No expenses found for the specified period"
        )

    buf = create_budget_vs_actual(
        expenses, user["categories"] if user else {}, from_date, to_date
    )

    return Response(content=buf.getvalue(), media_type="image/png")
