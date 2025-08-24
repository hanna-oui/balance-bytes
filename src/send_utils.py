from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
import base64
import json
import os

# -------------------------
# Config
# -------------------------
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

# resolve paths relative to project root (go up one level from src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
BUDGET_FILE = os.path.join(BASE_DIR, "budget-log.json")

TO_EMAIL = "ozhannaoui@gmail.com"

# -------------------------
# Helpers
# -------------------------
def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}

def send_message(service, user_id, message):
    sent = service.users().messages().send(userId=user_id, body=message).execute()
    print(f"✅ Message sent with ID: {sent['id']}")
    return sent

# -------------------------
# Main function
# -------------------------
def send_budget_update():
    """Send grocery budget summary via Gmail API."""

    # --- Auth setup ---
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid or not set(SCOPES).issubset(set(creds.scopes)):
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    # --- Load budget data ---
    if not os.path.exists(BUDGET_FILE):
        print("No budget-log.json found. Run update_budget_log first.")
        return

    with open(BUDGET_FILE, "r") as f:
        budget_data = json.load(f)

    gb = budget_data["grocery_budget"]

    # --- Format message ---
    message_text = (
        f"Today's date is {budget_data['today_date']}.\n\n"
        f"You spent ${gb['amount_spent_today']:.2f} today on groceries.\n\n"
        f"So far, you have spent ${gb['amount_spent_week']:.2f} this week "
        f"and ${gb['amount_spent_month']:.2f} this month.\n\n"
        f"You now have ${gb['allotted_budget_remaining']:.2f} remaining for the month, "
        f"${gb['weekly_budget'] - gb['amount_spent_week']:.2f} remaining for the week.\n"
    )

    # --- Build + Send email ---
    msg = create_message(
        sender="me",
        to=TO_EMAIL,
        subject="Grocery Budget Update",
        message_text=message_text
    )
    send_message(service, "me", msg)
