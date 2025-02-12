from datetime import datetime

import aiohttp

from config import config


class APIHelper:
    BASE_URL = config.TELEGRAM_BOT_API_BASE_URL

    @staticmethod
    async def save_expense(token: str, expense_data: dict) -> dict:
        """Save expense via API following the Telegram bot pattern"""
        async with aiohttp.ClientSession() as session:
            headers = {"Content-Type": "application/json", "token": token}

            # Ensure date is in correct ISO format
            try:
                if not expense_data["date"].endswith("Z"):
                    expense_data["date"] = f"{expense_data['date']}Z"
            except (KeyError, AttributeError):
                return {"success": False, "message": "Invalid date format"}

            # Use the expense data directly as it matches the API format
            payload = {
                "amount": expense_data["amount"],
                "description": expense_data["description"],
                "category": expense_data["category"],
                "currency": expense_data["currency"],
                "account": expense_data["account"],
                "date": expense_data["date"],
            }

            try:
                async with session.post(
                    f"{APIHelper.BASE_URL}/expenses/", json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        return {"success": True, "data": await response.json()}
                    else:
                        error_data = await response.json()
                        return {
                            "success": False,
                            "message": error_data.get(
                                "detail", "Failed to save expense"
                            ),
                        }
            except Exception as e:
                return {"success": False, "message": str(e)}
