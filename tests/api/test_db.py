import pytest
import datetime
from unittest.mock import AsyncMock, patch
from api.utils.db import fetch_data, calculate_days_in_range
from bson import ObjectId

class TestFetchData:
    """Test suite for the fetch_data function."""
    
    @pytest.mark.anyio
    @patch("api.utils.db.expenses_collection")
    @patch("api.utils.db.accounts_collection")
    @patch("api.utils.db.users_collection")
    async def test_fetch_data_from_date_only(self, mock_users, mock_accounts, mock_expenses):
        """Test fetch_data with only from_date specified."""
        mock_expenses.find.return_value.to_list = AsyncMock(return_value=[])
        mock_accounts.find.return_value.to_list = AsyncMock(return_value=[])
        mock_users.find_one = AsyncMock(return_value={})
        
        user_id = "60d5ec9877c9e9c8c7a8b4e6"
        from_date = datetime.date(2023, 1, 1)
        to_date = None
        
        await fetch_data(user_id, from_date, to_date)
        
        from_dt = datetime.datetime.combine(from_date, datetime.time.min)
        expected_query = {"user_id": user_id, "date": {"$gte": from_dt}}
        mock_expenses.find.assert_called_once_with(expected_query)

    @pytest.mark.anyio
    @patch("api.utils.db.expenses_collection")
    @patch("api.utils.db.accounts_collection")
    @patch("api.utils.db.users_collection")
    async def test_fetch_data_to_date_only(self, mock_users, mock_accounts, mock_expenses):
        """Test fetch_data with only to_date specified."""
        mock_expenses.find.return_value.to_list = AsyncMock(return_value=[])
        mock_accounts.find.return_value.to_list = AsyncMock(return_value=[])
        mock_users.find_one = AsyncMock(return_value={})
        
        user_id = "60d5ec9877c9e9c8c7a8b4e6"
        from_date = None
        to_date = datetime.date(2023, 12, 31)
        
        await fetch_data(user_id, from_date, to_date)
        
        to_dt = datetime.datetime.combine(to_date, datetime.time.max)
        expected_query = {"user_id": user_id, "date": {"$lte": to_dt}}
        mock_expenses.find.assert_called_once_with(expected_query)

class TestCalculateDaysInRange:
    """Test suite for the calculate_days_in_range function."""
    
    def test_from_date_only_with_last_expense_date(self):
        """Test days calculation with only from_date and last_expense_date."""
        from_date = datetime.date(2023, 1, 1)
        last_expense_date = datetime.date(2023, 1, 31)
        
        days = calculate_days_in_range(
            from_date=from_date,
            to_date=None,
            first_expense_date=None,
            last_expense_date=last_expense_date
        )
        
        expected_days = 31
        assert days == expected_days

    def test_from_date_only_without_last_expense_date(self):
        """Test days calculation with only from_date and no last_expense_date."""
        from_date = datetime.date(2023, 1, 1)
        today = datetime.date.today()
        
        days = calculate_days_in_range(
            from_date=from_date,
            to_date=None,
            first_expense_date=None,
            last_expense_date=None
        )
        
        expected_days = (today - from_date).days + 1
        assert days == expected_days

    def test_to_date_only_with_first_expense_date(self):
        """Test days calculation with only to_date and first_expense_date."""
        to_date = datetime.date(2023, 12, 31)
        first_expense_date = datetime.date(2023, 12, 1)
        
        days = calculate_days_in_range(
            from_date=None,
            to_date=to_date,
            first_expense_date=first_expense_date,
            last_expense_date=None
        )
        
        expected_days = 31
        assert days == expected_days

    def test_to_date_only_without_first_expense_date(self):
        """Test days calculation with only to_date and no first_expense_date."""
        to_date = datetime.date(2023, 12, 31)
        
        days = calculate_days_in_range(
            from_date=None,
            to_date=to_date,
            first_expense_date=None,
            last_expense_date=None
        )
        
        epoch_date = datetime.date(1970, 1, 1)
        expected_days = (to_date - epoch_date).days + 1
        assert days == expected_days