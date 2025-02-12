"""Shared plotting utilities for analytics and exports."""

import datetime
import io
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def create_expense_bar(
    expenses: list,
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
) -> io.BytesIO:
    """Generate expense bar chart."""
    df = pd.DataFrame(expenses)
    df["date"] = pd.to_datetime(df["date"])
    daily_expenses = df.groupby(df["date"].dt.date)["amount"].sum()

    plt.figure(figsize=(10, 6))
    ax = daily_expenses.plot(kind="bar", color="skyblue")

    date_range_text = get_date_range_text(from_date, to_date)
    total_spend = daily_expenses.sum()
    plt.title(
        f"Total Expenses per Day\n{date_range_text}\nTotal Spend: ${total_spend:,.2f}"
    )

    plt.xlabel("Date")
    plt.ylabel("Total Expense Amount")
    plt.xticks(rotation=45)
    plt.tight_layout()

    for i, value in enumerate(daily_expenses):
        ax.text(i, value + 0.5, f"{value:.2f}", ha="center", va="bottom", fontsize=10)

    return save_plot_to_buffer()


def create_category_pie(
    expenses: list,
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
) -> io.BytesIO:
    """Generate category pie chart."""
    df = pd.DataFrame(expenses)
    df["date"] = pd.to_datetime(df["date"])

    category_expenses = df.groupby("category")["amount"].sum()

    plt.figure(figsize=(8, 8))

    date_range_text = get_date_range_text(from_date, to_date)
    total_spend = category_expenses.sum()
    plt.title(
        f"Expense Distribution by Category\n{date_range_text}\nTotal Spend: ${total_spend:,.2f}",
        pad=20,
    )

    colors = [
        "#2ecc71",  # emerald green
        "#3498db",  # bright blue
        "#9b59b6",  # amethyst purple
        "#e74c3c",  # alizarin red
        "#f1c40f",  # sunflower yellow
        "#1abc9c",  # turquoise
        "#e67e22",  # carrot orange
        "#34495e",  # wet asphalt
        "#7f8c8d",  # concrete gray
        "#16a085",  # green sea
    ]

    labels = [f"{cat}\n(${amount:,.2f})" for cat, amount in category_expenses.items()]

    plt.pie(
        category_expenses,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        colors=colors,
    )
    plt.axis("equal")

    return save_plot_to_buffer()


def create_monthly_line(
    expenses: list,
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
) -> io.BytesIO:
    """Generate monthly expense line chart."""
    df = pd.DataFrame(expenses)
    df["date"] = pd.to_datetime(df["date"])
    monthly_expenses = df.groupby(df["date"].dt.to_period("M"))["amount"].sum()

    plt.figure(figsize=(10, 6))

    date_range_text = get_date_range_text(from_date, to_date)
    total_spend = monthly_expenses.sum()
    plt.title(f"Monthly Expenses\n{date_range_text}\nTotal Spend: ${total_spend:,.2f}")

    plt.xlabel("Month")
    plt.ylabel("Total Expense Amount")
    plt.xticks(rotation=45)
    plt.tight_layout()

    return save_plot_to_buffer()


def create_category_bar(
    expenses: list,
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
) -> io.BytesIO:
    """Generate category bar chart."""
    df = pd.DataFrame(expenses)
    df["date"] = pd.to_datetime(df["date"])

    category_expenses = df.groupby("category")["amount"].sum()

    plt.figure(figsize=(10, 6))
    ax = category_expenses.plot(kind="bar", color="skyblue")

    date_range_text = get_date_range_text(from_date, to_date)
    total_spend = category_expenses.sum()
    plt.title(
        f"Expenses by Category\n{date_range_text}\nTotal Spend: ${total_spend:,.2f}"
    )

    plt.xlabel("Category")
    plt.ylabel("Total Expense Amount")
    plt.xticks(rotation=45)
    plt.tight_layout()

    for i, value in enumerate(category_expenses):
        ax.text(i, value + 0.5, f"{value:.2f}", ha="center", va="bottom", fontsize=10)

    return save_plot_to_buffer()


def create_budget_vs_actual(
    expenses: list,
    categories: dict,
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
) -> io.BytesIO:
    """Generate budget vs actual comparison chart."""
    df = pd.DataFrame(expenses)
    df["date"] = pd.to_datetime(df["date"])
    category_expenses = df.groupby("category")["amount"].sum()
    first_expense_date = df["date"].min().date() if not from_date else from_date
    last_expense_date = df["date"].max().date() if not to_date else to_date

    category_names = list(set(category_expenses.index).union(set(categories.keys())))
    actuals = [category_expenses.get(cat, 0) for cat in category_names]
    budgeted = [
        (
            prorate_budget(
                categories[cat]["monthly_budget"],
                from_date,
                to_date,
                first_expense_date,
                last_expense_date,
            )
            if cat in categories
            else 0
        )
        for cat in category_names
    ]

    plt.figure(figsize=(10, 6))
    x = range(len(category_names))
    plt.bar(x, budgeted, width=0.4, label="Budgeted", align="center")
    plt.bar(x, actuals, width=0.4, label="Actual", align="edge")
    plt.xticks(x, category_names, rotation=45)

    date_range_text = get_date_range_text(from_date, to_date)
    plt.title(f"Budget vs Actual Expenses\n{date_range_text}")
    plt.xlabel("Category")
    plt.ylabel("Amount")
    plt.legend()
    plt.tight_layout()

    return save_plot_to_buffer()


def get_date_range_text(
    from_date: Optional[datetime.date], to_date: Optional[datetime.date]
) -> str:
    """Generate standardized date range text."""
    if from_date and to_date:
        return (
            f"Date: {from_date}"
            if from_date == to_date
            else f"Date Range: {from_date} to {to_date}"
        )
    if from_date:
        return f"Date Range: From {from_date}"
    if to_date:
        return f"Date Range: To {to_date}"
    return "Date Range: All"


def save_plot_to_buffer() -> io.BytesIO:
    """Save current plot to BytesIO buffer."""
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf


def prorate_budget(
    budget: float,
    from_date: Optional[datetime.date],
    to_date: Optional[datetime.date],
    first_expense_date: Optional[datetime.date],
    last_expense_date: Optional[datetime.date],
) -> float:
    """Prorate the budget based on the date range."""
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

    return (budget / 30) * days_in_range
