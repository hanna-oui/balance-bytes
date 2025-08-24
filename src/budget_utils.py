import json
import os
import re
from datetime import datetime, timedelta
import calendar

# -------------------------
# Config
# -------------------------
# point paths to project root (go up one directory from src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGET_FILE = os.path.join(BASE_DIR, "budget-log.json")
EMAIL_FILE = os.path.join(BASE_DIR, "email-dump.json")

MONTHLY_BUDGET = 500.00   # reinitialize this each month

# -------------------------
# Helpers
# -------------------------
def extract_amount(subject):
    """Extract $amount from subject line like 'You made a $15.89 transaction...'"""
    match = re.search(r"\$\s*([\d,]+\.\d{2})", subject)
    if match:
        return float(match.group(1).replace(",", ""))
    return None

def get_week_start(dt):
    """Return Monday of the week containing dt"""
    return dt - timedelta(days=dt.weekday())

def init_budget_log(today):
    """Initialize new budget log for the month"""
    year, month = today.year, today.month
    days_in_month = calendar.monthrange(year, month)[1]

    return {
        "today_date": today.strftime("%Y-%m-%d"),
        "month": month,
        "days_remaining_in_month": days_in_month - today.day,
        "grocery_budget": {
            "monthly_budget": MONTHLY_BUDGET,
            "weekly_budget": round(MONTHLY_BUDGET / 4, 2),
            "daily_budget": round(MONTHLY_BUDGET / days_in_month, 2),
            "amount_spent_today": 0.0,
            "amount_spent_week": 0.0,
            "amount_spent_month": 0.0,
            "allotted_budget_remaining": MONTHLY_BUDGET
        },
        "processed_ids": []  # track email IDs already counted
    }

# -------------------------
# Main function
# -------------------------
def update_budget_log():
    """
    Update the grocery budget log based on transactions in email-dump.json.
    Looks for 'GIANT-EAGLE' purchases in subjects.
    """
    today = datetime.today()  # use real today
    # today = datetime(2025, 8, 23)  # <-- uncomment for testing

    # Load or reset budget log
    if os.path.exists(BUDGET_FILE):
        with open(BUDGET_FILE, "r") as f:
            budget_log = json.load(f)
        if budget_log["month"] != today.month:
            budget_log = init_budget_log(today)
    else:
        budget_log = init_budget_log(today)

    # Load emails
    if not os.path.exists(EMAIL_FILE):
        print("email-dump.json not found, run build_email_dump first.")
        return
    with open(EMAIL_FILE, "r") as f:
        emails = json.load(f)

    # Process GIANT-EAGLE transactions
    for email in emails:
        subj = email.get("subject", "")
        eid = email.get("id")
        date_str = email.get("date")
        if not subj or not date_str:
            continue

        if "GIANT-EAGLE" in subj.upper():
            if eid in budget_log["processed_ids"]:
                continue  # already counted

            amount = extract_amount(subj)
            if not amount:
                continue

            tx_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
            today_date = today.date()

            # monthly total
            budget_log["grocery_budget"]["amount_spent_month"] += amount

            # weekly total
            if get_week_start(tx_date) == get_week_start(today_date):
                budget_log["grocery_budget"]["amount_spent_week"] += amount

            # daily total
            if tx_date == today_date:
                budget_log["grocery_budget"]["amount_spent_today"] += amount

            budget_log["processed_ids"].append(eid)

    # Update remaining budget
    budget_log["grocery_budget"]["allotted_budget_remaining"] = round(
        budget_log["grocery_budget"]["monthly_budget"] - budget_log["grocery_budget"]["amount_spent_month"], 2
    )

    budget_log["today_date"] = today.strftime("%Y-%m-%d")
    budget_log["days_remaining_in_month"] = (
        calendar.monthrange(today.year, today.month)[1] - today.day
    )

    # Save back
    with open(BUDGET_FILE, "w") as f:
        json.dump(budget_log, f, indent=2)

    print(f"Budget updated for {today.strftime('%Y-%m-%d')}")
