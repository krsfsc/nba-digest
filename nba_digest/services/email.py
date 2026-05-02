"""Email sending service via Gmail SMTP."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from nba_digest.models import Digest

log = logging.getLogger(__name__)


class EmailService:
    """Sends digest emails via Gmail SMTP."""

    GMAIL_SMTP_SERVER = "smtp.gmail.com"
    GMAIL_SMTP_PORT = 465  # SSL

    def __init__(self, sender_email: str, app_password: str):
        """
        Initialize email service.

        Args:
            sender_email: Gmail address to send from
            app_password: Gmail app-specific password (not regular password)
        """
        self.sender_email = sender_email
        self.app_password = app_password

    def send(
        self, recipient: str, subject: str, html_body: str, text_body: Optional[str] = None
    ) -> bool:
        """
        Send email via Gmail.

        Args:
            recipient: Email address to send to
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plaintext fallback body

        Returns:
            True if sent successfully

        Raises:
            RuntimeError: If email sending fails
        """
        try:
            log.info("Connecting to Gmail SMTP...")

            # Create message with both plaintext and HTML versions
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = recipient

            # Plaintext fallback
            if text_body:
                msg.attach(MIMEText(text_body, "plain"))

            # HTML version (preferred)
            msg.attach(MIMEText(html_body, "html"))

            # Send via Gmail
            with smtplib.SMTP_SSL(self.GMAIL_SMTP_SERVER, self.GMAIL_SMTP_PORT) as server:
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, recipient, msg.as_string())

            log.info("Email sent to %s", recipient)
            return True

        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(f"Gmail authentication failed: {e}")
        except smtplib.SMTPException as e:
            raise RuntimeError(f"SMTP error: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to send email: {e}")

    def send_digest(
        self, recipient: str, digest: Digest, html_body: str, text_body: Optional[str] = None
    ) -> bool:
        """
        Send digest email.

        Args:
            recipient: Email address to send to
            digest: Digest model (for subject line)
            html_body: Email HTML body
            text_body: Optional plaintext fallback

        Returns:
            True if sent successfully
        """
        subject = f"🏀 NBA Playoff Digest — {digest.date}"
        return self.send(recipient, subject, html_body, text_body)
