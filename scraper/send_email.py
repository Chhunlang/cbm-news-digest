"""
send_email.py
-------------
Sends today's AI-generated daily summary to you by email, using a
free Gmail account + an "App Password" (no paid email service
needed). Runs as the last step of the daily GitHub Action.
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", GMAIL_ADDRESS)
ADMIN_DASHBOARD_URL = os.environ.get("ADMIN_DASHBOARD_URL", "")

if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD]):
    print("ERROR: missing one of SUPABASE_URL / SUPABASE_SERVICE_KEY / GMAIL_ADDRESS / GMAIL_APP_PASSWORD")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_today_summary():
    today = datetime.now(timezone.utc).date().isoformat()
    result = (
        supabase.table("summaries")
        .select("*")
        .eq("period_type", "daily")
        .eq("period_start", today)
        .execute()
    )
    return result.data[0] if result.data else None


def get_pending_count():
    result = (
        supabase.table("articles")
        .select("id", count="exact")
        .eq("status", "Pending Verification")
        .execute()
    )
    return result.count or 0


def build_email_body():
    summary = get_today_summary()
    pending_count = get_pending_count()

    lines = []
    lines.append(f"CBM News & Oil Price Digest — Daily Summary ({datetime.now(timezone.utc):%Y-%m-%d})")
    lines.append("=" * 60)
    lines.append("")
    if summary:
        lines.append(f"Articles collected today: {summary['article_count']}")
        lines.append("")
        lines.append(summary["summary_text"])
    else:
        lines.append("No new articles were collected today.")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"{pending_count} article(s) are waiting for your review/approval.")
    if ADMIN_DASHBOARD_URL:
        lines.append(f"Review them here: {ADMIN_DASHBOARD_URL}")
    lines.append("")
    lines.append("This is an automated message from your News Digest system.")
    return "\n".join(lines)


def main():
    body = build_email_body()
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"CBM News Digest — Daily Summary ({datetime.now(timezone.utc):%Y-%m-%d})"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [RECIPIENT_EMAIL], msg.as_string())

    print(f"Email sent to {RECIPIENT_EMAIL}")


if __name__ == "__main__":
    main()
