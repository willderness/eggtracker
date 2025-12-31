"""Google Sheets integration for egg tracking."""

import json
import os
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME = "EggLog"


def get_client() -> gspread.Client:
    """Create and return an authenticated gspread client."""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set")

    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(credentials)


def get_worksheet() -> gspread.Worksheet:
    """Get the EggLog worksheet."""
    client = get_client()
    sheet_id = os.environ.get("GOOGLE_SHEETS_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID environment variable not set")

    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.worksheet(SHEET_NAME)


def add_eggs(count: int) -> tuple[int, int]:
    """
    Add eggs to today's count.

    Returns:
        Tuple of (today's total, weekly total)
    """
    worksheet = get_worksheet()
    today = datetime.now().strftime("%Y-%m-%d")

    # Get all records
    records = worksheet.get_all_records()

    # Find today's row
    today_row = None
    for i, record in enumerate(records):
        if record.get("Date") == today:
            today_row = i + 2  # +2 because of header row and 1-indexing
            break

    if today_row:
        # Update existing row
        current_count = int(worksheet.cell(today_row, 2).value or 0)
        new_count = current_count + count
        worksheet.update_cell(today_row, 2, new_count)
    else:
        # Add new row
        worksheet.append_row([today, count])

    # Calculate totals
    today_total = get_today_total()
    week_total = get_week_total()

    return today_total, week_total


def get_today_total() -> int:
    """Get today's egg count."""
    worksheet = get_worksheet()
    today = datetime.now().strftime("%Y-%m-%d")

    records = worksheet.get_all_records()
    for record in records:
        if record.get("Date") == today:
            return int(record.get("Count", 0))

    return 0


def get_week_total() -> int:
    """Get the rolling 7-day total."""
    worksheet = get_worksheet()

    # Calculate date range (last 7 days including today)
    today = datetime.now()
    week_ago = today - timedelta(days=6)

    records = worksheet.get_all_records()
    total = 0

    for record in records:
        date_str = record.get("Date", "")
        if date_str:
            try:
                record_date = datetime.strptime(date_str, "%Y-%m-%d")
                if week_ago <= record_date <= today:
                    total += int(record.get("Count", 0))
            except ValueError:
                continue

    return total


def get_week_breakdown() -> list[tuple[str, int]]:
    """
    Get daily breakdown for the last 7 days.

    Returns:
        List of (date_string, count) tuples, sorted by date descending
    """
    worksheet = get_worksheet()

    today = datetime.now()
    week_ago = today - timedelta(days=6)

    records = worksheet.get_all_records()
    breakdown = []

    # Create a dict for quick lookup
    date_counts = {}
    for record in records:
        date_str = record.get("Date", "")
        if date_str:
            try:
                record_date = datetime.strptime(date_str, "%Y-%m-%d")
                if week_ago <= record_date <= today:
                    date_counts[date_str] = int(record.get("Count", 0))
            except ValueError:
                continue

    # Fill in all 7 days (including days with 0 eggs)
    for i in range(7):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        count = date_counts.get(date_str, 0)
        # Format as shorter date for display
        display_date = date.strftime("%a %m/%d")
        breakdown.append((display_date, count))

    return breakdown
