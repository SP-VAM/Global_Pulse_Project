"""
GlobalPulse Email Service
Handles sending HTML email verification OTPs and notification emails via SMTP (e.g. Gmail / SendGrid).
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service layer for sending verification and system emails over SMTP."""

    def __init__(self):
        self.settings = get_settings()

    def send_otp_email(self, recipient_email: str, otp_code: str) -> bool:
        """
        Send a 6-digit OTP verification code to recipient_email via SMTP.
        If SMTP_USER and SMTP_PASSWORD are not configured, logs the OTP in dev mode.
        """
        smtp_user = self.settings.SMTP_USER.strip()
        smtp_pass = self.settings.SMTP_PASSWORD.strip()

        if smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"{otp_code} is your GlobalPulse Verification Code"
                sender_email = self.settings.EMAILS_FROM_EMAIL.strip() or smtp_user
                msg["From"] = f"{self.settings.EMAILS_FROM_NAME} <{sender_email}>"
                msg["To"] = recipient_email

                html_content = f"""
                <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 24px; background-color: #0b0f19; color: #ffffff; border-radius: 12px; border: 1px solid #1e293b;">
                    <h2 style="color: #3b82f6; text-align: center; margin-top: 0;">GlobalPulse Account Verification</h2>
                    <p style="color: #cbd5e1; font-size: 15px;">Hello,</p>
                    <p style="color: #cbd5e1; font-size: 15px;">Thank you for signing up with GlobalPulse. Please use the following 6-digit verification code to complete your registration:</p>
                    <div style="background-color: #1e293b; padding: 18px; text-align: center; font-size: 34px; font-weight: bold; letter-spacing: 8px; color: #60a5fa; border-radius: 8px; margin: 24px 0;">
                        {otp_code}
                    </div>
                    <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">This code will expire in 10 minutes. If you did not request this verification code, please ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #1e293b; margin: 20px 0;" />
                    <p style="font-size: 12px; color: #64748b; text-align: center; margin-bottom: 0;">GlobalPulse &copy; 2026. All rights reserved.</p>
                </div>
                """
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(sender_email, recipient_email, msg.as_string())

                logger.info("Successfully dispatched OTP email via SMTP to %s", recipient_email)
                return True
            except Exception as e:
                logger.error("Failed to send OTP email via SMTP to %s: %s", recipient_email, e)
                return False
        else:
            logger.info("[DEV MODE EMAIL SENDER] OTP for %s: %s (Configure SMTP_USER & SMTP_PASSWORD in .env for real inbox delivery)", recipient_email, otp_code)
            return True


_email_service_instance = None


def get_email_service() -> EmailService:
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance
