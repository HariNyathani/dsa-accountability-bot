"""
Email service — send reminders via Gmail SMTP.

Multi-user: accepts a target email per call. Falls back to no-op if
credentials are not configured.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

logger = logging.getLogger("dsa_bot.email")


def send_email(subject: str, body: str, to_email: str = "") -> bool:
    """
    Send an email via Gmail SMTP.
    Returns True on success, False on failure.
    Retries once on failure.
    """
    to = to_email
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD or not to:
        logger.warning("Email not configured — skipping send.")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = to
    msg["Subject"] = subject

    # Plain-text body
    msg.attach(MIMEText(body, "plain"))

    # HTML body (richer formatting)
    html_body = _build_html(subject, body)
    msg.attach(MIMEText(html_body, "html"))

    for attempt in range(2):  # retry once
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
                server.sendmail(config.GMAIL_ADDRESS, to, msg.as_string())
            logger.info(f"Email sent to {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Email send attempt {attempt + 1} failed: {e}")

    return False


def _build_html(subject: str, body: str) -> str:
    """Build a simple HTML email body."""
    escaped = body.replace("\n", "<br>")
    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 30px;">
        <div style="max-width: 500px; margin: auto; background: #16213e; border-radius: 12px; padding: 24px; border: 1px solid #0f3460;">
            <h2 style="color: #e94560; margin-top: 0;">🚨 {subject}</h2>
            <p style="line-height: 1.7; font-size: 15px;">{escaped}</p>
            <hr style="border: none; border-top: 1px solid #0f3460; margin: 20px 0;">
            <p style="font-size: 12px; color: #888;">DSA Accountability Bot • Stay disciplined 💪</p>
        </div>
    </body>
    </html>
    """


def send_reminder_email_to(day_str: str, to_email: str) -> bool:
    """Send the escalation reminder email to a specific user."""
    subject = f"⚠️ DSA Progress Missing — {day_str}"
    body = (
        f"Hey! You haven't posted your DSA progress today ({day_str}).\n\n"
        "This is the final escalation reminder. The deadline has passed.\n\n"
        "Please post your progress in the DSA channel ASAP, "
        "or your streak will be broken.\n\n"
        "— Your DSA Accountability Bot 🤖"
    )
    return send_email(subject, body, to_email)


# Legacy compat
def send_reminder_email(day_str: str) -> bool:
    """Legacy wrapper — no longer used (no global email target)."""
    logger.warning("send_reminder_email() called without target email — skipping.")
    return False
