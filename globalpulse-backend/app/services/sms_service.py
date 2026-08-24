"""
GlobalPulse SMS Service
Handles real SMS delivery to Indian mobile numbers via Fast2SMS API (/dev/bulkV2).
"""
import logging
import re
import httpx
from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError, ValidationError

logger = logging.getLogger(__name__)


def normalize_indian_mobile(mobile: str) -> str:
    """
    Normalize Indian mobile numbers consistently:
    +91XXXXXXXXXX, 91XXXXXXXXXX, or XXXXXXXXXX -> 10-digit Indian mobile number string.
    """
    if not mobile:
        raise ValidationError("Mobile number cannot be empty.")
    
    digits = re.sub(r"\D", "", str(mobile))
    
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[2:]
        
    if len(digits) != 10 or not digits[0] in "6789":
        raise ValidationError(f"Invalid 10-digit Indian mobile number: '{mobile}'.")
        
    return digits


def mask_mobile(mobile: str) -> str:
    """Mask mobile number for safe logging: 93****0976."""
    clean = re.sub(r"\D", "", str(mobile))
    if len(clean) >= 10:
        return f"{clean[:2]}****{clean[-4:]}"
    return "****"


class SMSService:
    """Service layer for sending OTP verification messages via Fast2SMS."""

    def __init__(self):
        self.settings = get_settings()

    def validate_configuration(self) -> None:
        """Verify SMS provider configuration is present without performing network operations."""
        api_key = getattr(self.settings, "FAST2SMS_API_KEY", "").strip()
        if not api_key or api_key == "YOUR_FAST2SMS_API_KEY_HERE":
            logger.error("Fast2SMS API key (FAST2SMS_API_KEY) is not configured in environment.")
            raise ServiceUnavailableError("SMS delivery service is unconfigured. FAST2SMS_API_KEY missing.", status_code=503)

    async def send_sms_otp(self, recipient_mobile: str, otp_code: str) -> bool:
        """
        Send a 6-digit OTP code to recipient_mobile via Fast2SMS API (/dev/bulkV2).
        Raises ServiceUnavailableError (HTTP 503 if unconfigured/unreachable, HTTP 502 if provider rejected).
        """
        self.validate_configuration()
        api_key = getattr(self.settings, "FAST2SMS_API_KEY", "").strip()

        clean_number = normalize_indian_mobile(recipient_mobile)
        masked = mask_mobile(clean_number)
        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {
            "authorization": api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Try DLT OTP route first
            payload_otp = {
                "variables_values": otp_code,
                "route": "otp",
                "numbers": clean_number,
            }

            try:
                resp = await client.post(url, json=payload_otp, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("return") is True or data.get("status_code") == 200:
                        logger.info("Successfully delivered real SMS OTP via Fast2SMS OTP route to %s", masked)
                        return True
                    logger.warning("Fast2SMS OTP route response rejected for %s: return=%s", masked, data.get("return"))
                else:
                    logger.warning("Fast2SMS OTP route returned HTTP status %s for %s", resp.status_code, masked)
            except Exception as e:
                logger.warning("Fast2SMS OTP route exception for %s: %s. Trying Quick SMS route...", masked, type(e).__name__)

            # 2. Fallback to Quick SMS route ('q')
            payload_quick = {
                "route": "q",
                "message": f"Your GlobalPulse verification code is {otp_code}. Valid for 5 minutes.",
                "language": "english",
                "flash": 0,
                "numbers": clean_number,
            }

            try:
                q_resp = await client.post(url, json=payload_quick, headers=headers)
                if q_resp.status_code == 200:
                    q_data = q_resp.json()
                    if q_data.get("return") is True or q_data.get("status_code") == 200:
                        logger.info("Successfully delivered real SMS OTP via Fast2SMS Quick SMS route to %s", masked)
                        return True
                    msg_list = q_data.get("message")
                    err_msg = str(msg_list[0]) if isinstance(msg_list, list) and msg_list else str(q_data.get("message") or "Fast2SMS rejected request.")
                    logger.error("Fast2SMS Quick SMS route rejected request for %s: %s", masked, err_msg)
                    raise ServiceUnavailableError(f"SMS delivery provider failed: {err_msg}", status_code=502)
                else:
                    logger.error("Fast2SMS HTTP status error for %s: %s", masked, q_resp.status_code)
                    raise ServiceUnavailableError(f"SMS provider HTTP {q_resp.status_code} error.", status_code=502)

            except ServiceUnavailableError:
                raise
            except httpx.TimeoutException:
                logger.error("Fast2SMS API timeout for %s", masked)
                raise ServiceUnavailableError("SMS delivery provider timed out.", status_code=503)
            except Exception as exc:
                logger.error("Failed to connect to Fast2SMS API for %s: %s", masked, type(exc).__name__)
                raise ServiceUnavailableError("SMS delivery provider is unreachable.", status_code=503)


_sms_service_instance = None

def get_sms_service() -> SMSService:
    global _sms_service_instance
    if _sms_service_instance is None:
        _sms_service_instance = SMSService()
    return _sms_service_instance
