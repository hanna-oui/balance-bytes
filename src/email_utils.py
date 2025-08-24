# -------------------------
# Gmail API Setup
# -------------------------
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import json 
import base64
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
from datetime import datetime


SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

# figure out project root (go up one directory from src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

creds = None
if os.path.exists(TOKEN_PATH):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

# If no valid creds or wrong scopes, go through OAuth flow
if not creds or not creds.valid or not set(SCOPES).issubset(set(creds.scopes)):
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials back to token.json in the project root
    with open(TOKEN_PATH, 'w') as token:
        token.write(creds.to_json())

service = build('gmail', 'v1', credentials=creds)


# -------------------------
# Helpers
# -------------------------
def get_header(headers, name):
    for h in headers:
        if h['name'].lower() == name.lower():
            return h['value']
    return None

def parse_parts(parts):
    text, html, attachments = "", "", []
    for part in parts:
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")
        if body_data:
            data = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
            if mime_type == "text/plain":
                text += data
            elif mime_type == "text/html":
                html += data
        if "parts" in part:
            t, h, a = parse_parts(part["parts"])
            text += t
            html += h
            attachments.extend(a)
        if part.get("filename"):
            attachments.append(part["filename"])
    return text.strip(), html.strip(), attachments

# -------------------------
# Main function
# -------------------------
def build_email_dump(start_date: str, output_file: str = "email-dump.json"):
    """
    Fetch all emails since start_date and save them to output_file.
    
    :param start_date: ISO string or YYYY-MM-DD (e.g., "2025-08-23")
    :param output_file: Path for JSON dump
    """
    # Ensure date is RFC 3339 for Gmail API
    if len(start_date) == 10:  # e.g. "2025-08-23"
        dt = datetime.fromisoformat(start_date)
    else:
        dt = datetime.fromisoformat(start_date)
    query = f"after:{dt.strftime('%Y/%m/%d')}"  

    # Fetch messages
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    emails_dump = []
    for m in messages:
        msg = service.users().messages().get(userId='me', id=m['id'], format='full').execute()
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])

        subject = get_header(headers, "Subject")
        sender = get_header(headers, "From")
        to = get_header(headers, "To")
        date_raw = get_header(headers, "Date")
        date = parsedate_to_datetime(date_raw).isoformat() if date_raw else None

        message_id = get_header(headers, "Message-ID")
        dkim = get_header(headers, "DKIM-Signature")
        auth_results = get_header(headers, "Authentication-Results")

        labels = msg.get("labelIds", [])
        thread_id = msg.get("threadId")
        internal_date = msg.get("internalDate")

        plain_body, html_body, attachments = "", "", []
        if "parts" in payload:
            plain_body, html_body, attachments = parse_parts(payload["parts"])
        else:
            body_data = payload.get("body", {}).get("data")
            if body_data:
                plain_body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore").strip()

        # fallback: strip HTML if no plain text
        if (not plain_body) and html_body:
            plain_body = BeautifulSoup(html_body, "html.parser").get_text(separator="\n").strip()

        email_entry = {
            "id": msg["id"],
            "thread_id": thread_id,
            "labels": labels,
            "internal_date": internal_date,
            "from": sender,
            "to": to,
            "subject": subject,
            "date": date,
            "message_id": message_id,
            "dkim": dkim,
            "auth_results": auth_results,
            "attachments": attachments,
            "attachments_count": len(attachments),
            "plain_body": plain_body,
            "body_preview": plain_body[:500] if plain_body else "(empty)"
        }

        emails_dump.append(email_entry)

    # Save all emails to JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(emails_dump, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(emails_dump)} emails since {start_date} to {output_file}")

