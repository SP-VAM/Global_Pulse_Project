"""
GlobalPulse Email Service
Handles sending HTML email verification OTPs and notification emails via SMTP (e.g. Gmail).
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError, ValidationError

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    """Mask email address for safe logging: sa****@gmail.com."""
    if not email or "@" not in email:
        return "****"
    user, domain = email.split("@", 1)
    if len(user) <= 2:
        masked_user = user[0] + "****"
    else:
        masked_user = user[:2] + "****"
    return f"{masked_user}@{domain}"


class EmailService:
    """Service layer for sending verification and system emails over SMTP."""

    def __init__(self):
        self.settings = get_settings()

    def validate_configuration(self) -> None:
        """Verify SMTP configuration is present without performing network operations."""
        smtp_user = (self.settings.SMTP_USER or "").strip()
        smtp_pass = (self.settings.SMTP_PASSWORD or "").strip()

        if not smtp_user or not smtp_pass or smtp_user == "YOUR_GMAIL_USER@gmail.com":
            logger.error("SMTP credentials (SMTP_USER/SMTP_PASSWORD) are not configured in environment.")
            raise ServiceUnavailableError("Email delivery service is unconfigured. SMTP credentials missing.", status_code=503)

    def send_otp_email(self, recipient_email: str, otp_code: str) -> bool:
        """
        Send a 6-digit OTP verification code to recipient_email via SMTP.
        Raises ServiceUnavailableError if SMTP credentials are missing or connection fails.
        """
        self.validate_configuration()
        smtp_user = self.settings.SMTP_USER.strip()
        smtp_pass = self.settings.SMTP_PASSWORD.strip()
        masked = mask_email(recipient_email)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Your GlobalPulse Verification Code"
            sender_email = self.settings.EMAILS_FROM_EMAIL.strip() or smtp_user
            msg["From"] = f"{self.settings.EMAILS_FROM_NAME} <{sender_email}>"
            msg["To"] = recipient_email

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 24px; background-color: #0b0f19; color: #ffffff; border-radius: 12px; border: 1px solid #1e293b;">
                <h2 style="color: #3b82f6; text-align: center; margin-top: 0;">GlobalPulse Account Verification</h2>
                <p style="color: #cbd5e1; font-size: 15px;">Hello,</p>
                <p style="color: #cbd5e1; font-size: 15px;">Thank you for using GlobalPulse. Please use the following 6-digit verification code:</p>
                <div style="background-color: #1e293b; padding: 18px; text-align: center; font-size: 34px; font-weight: bold; letter-spacing: 8px; color: #60a5fa; border-radius: 8px; margin: 24px 0;">
                    {otp_code}
                </div>
                <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">This code will expire in 5 minutes. If you did not request this verification code, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #1e293b; margin: 20px 0;" />
                <p style="font-size: 12px; color: #64748b; text-align: center; margin-bottom: 0;">GlobalPulse &copy; 2026. All rights reserved.</p>
            </div>
            """
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(sender_email, recipient_email, msg.as_string())

            logger.info("Successfully dispatched real OTP email via SMTP to %s", masked)
            return True
        except smtplib.SMTPAuthenticationError as auth_err:
            logger.error("SMTP authentication failed for %s: %s", masked, type(auth_err).__name__)
            raise ServiceUnavailableError("Email delivery authentication failed.", status_code=502)
        except Exception as e:
            logger.error("Failed to deliver OTP email via SMTP to %s: %s", masked, type(e).__name__)
            raise ServiceUnavailableError("Email delivery provider is unreachable or rejected connection.", status_code=503)


_email_service_instance = None


def get_email_service() -> EmailService:
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance
