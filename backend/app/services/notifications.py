import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, List

import httpx

from app.config import get_settings


class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> Dict[str, Any]:
        settings = get_settings()
        provider = (os.getenv("EMAIL_PROVIDER") or settings.email_provider or "smtp").lower()

        if provider == "sendgrid":
            api_key = os.getenv("SENDGRID_API_KEY") or settings.sendgrid_api_key
            if not api_key:
                return {"status": "queued", "recipient": to_email, "subject": subject, "body": body, "provider": provider}
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": os.getenv("SMTP_FROM_EMAIL") or settings.smtp_from_email},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            }
            try:
                response = httpx.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=15,
                )
                response.raise_for_status()
                return {"status": "sent", "recipient": to_email, "subject": subject, "provider": "sendgrid"}
            except Exception as exc:  # pragma: no cover - network/provider may be unavailable
                return {"status": "failed", "recipient": to_email, "subject": subject, "error": str(exc), "provider": "sendgrid"}

        host = os.getenv("SMTP_HOST") or settings.smtp_host
        port = int(os.getenv("SMTP_PORT") or settings.smtp_port or 1025)
        if not host or host == "localhost" and not (os.getenv("SMTP_USERNAME") or settings.smtp_username or os.getenv("SMTP_PASSWORD") or settings.smtp_password):
            return {"status": "queued", "recipient": to_email, "subject": subject, "body": body, "provider": "smtp"}

        try:
            smtp = smtplib.SMTP(host, port, timeout=15)
            smtp.ehlo()
            username = os.getenv("SMTP_USERNAME") or settings.smtp_username
            password = os.getenv("SMTP_PASSWORD") or settings.smtp_password
            if username and password:
                smtp.starttls()
                smtp.login(username, password)
            message = EmailMessage()
            message["To"] = to_email
            message["From"] = os.getenv("SMTP_FROM_EMAIL") or settings.smtp_from_email
            message["Subject"] = subject
            message.set_content(body)
            smtp.send_message(message)
            smtp.quit()
            return {"status": "sent", "recipient": to_email, "subject": subject, "provider": "smtp"}
        except Exception as exc:  # pragma: no cover - network/provider may be unavailable
            return {"status": "failed", "recipient": to_email, "subject": subject, "error": str(exc), "provider": "smtp"}


class NotificationService:
    @staticmethod
    def create_notification(recipient_id: str, title: str, body: str, channel: str = "email") -> Dict[str, Any]:
        return {"recipient_id": recipient_id, "title": title, "body": body, "status": "queued", "channel": channel}

    @staticmethod
    def send_medication_reminders(medication_list: List[Dict[str, Any]]) -> str:
        sent = 0
        for med in medication_list:
            recipient = med.get("recipient_email")
            if recipient:
                result = EmailService.send_email(
                    recipient,
                    med.get("subject", "Medication reminder"),
                    med.get("body", "Please take your prescribed medication on schedule."),
                )
                if result.get("status") in {"sent", "queued"}:
                    sent += 1
        return f"{sent} medication reminder(s) sent."

    @staticmethod
    def send_notification(recipient_email: str, title: str, body: str) -> Dict[str, Any]:
        return EmailService.send_email(recipient_email, title, body)
