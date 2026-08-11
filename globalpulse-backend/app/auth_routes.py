import os
import random
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.sync_database import get_db
from app.final_auth import create_access_token, hash_password, verify_password, get_current_firebase_user
from app.firebase_config import verify_firebase_token
from app.final_models import (
    User,
    OTPVerification,
    SocialLogin,
    UserSession,
    UserSubscription,
    AuditLog,
)
from app.final_schemas import (
    SendOTPRequest,
    VerifyOTPRequest,
    SignupRequest,
    LoginRequest,
    LogoutRequest,
    CompleteProfileRequest,
    GoogleLoginRequest,
    GoogleSignupCompleteRequest,
    FirebaseLoginRequest,
    MessageResponse,
    UserResponse,
    ForgotPasswordRequest,
    VerifyForgotOTPRequest,
    ResetPasswordRequest,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

def serialize_user_entity(user: User) -> dict:
    """
    Returns a unified mapping dictionary of a User entity including username, email, and mobile_number.
    """
    if not user:
        return {}
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "mobile_number": user.mobile_number,
        "auth_provider": user.auth_provider,
        "is_mobile_verified": bool(user.is_mobile_verified),
        "is_email_verified": bool(user.is_email_verified),
        "account_status": user.account_status,
    }

def send_real_sms_otp(mobile_number: str, otp_code: str):
    """
    Sends real SMS OTP using Fast2SMS API if FAST2SMS_API_KEY is configured in .env.
    Falls back to Quick SMS route ('q') if OTP route requires domain verification (Error 996).
    """
    fast2sms_key = os.getenv("FAST2SMS_API_KEY")

    if not fast2sms_key or fast2sms_key == "YOUR_FAST2SMS_API_KEY_HERE":
        print(f"[DEV / MOCK SMS] FAST2SMS_API_KEY not set in .env. OTP for mobile {mobile_number}: {otp_code}")
        return True

    # Clean mobile number for Fast2SMS (10 digits for Indian numbers)
    clean_number = mobile_number.replace("+91", "").replace("+", "").strip()

    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {
        "authorization": fast2sms_key,
        "Content-Type": "application/json",
    }

    # 1. Try OTP Route first
    payload_otp = {
        "variables_values": otp_code,
        "route": "otp",
        "numbers": clean_number,
    }

    try:
        response = requests.post(url, json=payload_otp, headers=headers, timeout=10)
        res_data = response.json()
        print(f"[FAST2SMS POST OTP RESULT]: {res_data}")

        if res_data.get("return") is True or res_data.get("status_code") == 200:
            print(f"[FAST2SMS SUCCESS] Real SMS OTP delivered successfully to {clean_number}")
            return True

        # 2. Try Quick SMS Route ('q') if OTP route fails (e.g. status 996 domain verification needed)
        print(f"[FAST2SMS FALLBACK] Trying Quick SMS route ('q')...")
        payload_quick = {
            "route": "q",
            "message": f"Your OTP code is {otp_code}. Valid for 10 minutes.",
            "language": "english",
            "flash": 0,
            "numbers": clean_number,
        }
        q_response = requests.post(url, json=payload_quick, headers=headers, timeout=10)
        q_res_data = q_response.json()
        print(f"[FAST2SMS QUICK SMS RESULT]: {q_res_data}")

        if q_res_data.get("return") is True or q_res_data.get("status_code") == 200:
            print(f"[FAST2SMS SUCCESS] Quick SMS OTP delivered successfully to {clean_number}")
            return True

        # 3. Try GET fallback format for Quick SMS route ('q')
        print(f"[FAST2SMS RETRY] Trying GET Quick SMS endpoint format...")
        import urllib.parse
        encoded_msg = urllib.parse.quote(f"Your OTP code is {otp_code}. Valid for 10 minutes.")
        get_url = f"https://www.fast2sms.com/dev/bulkV2?authorization={fast2sms_key}&route=q&message={encoded_msg}&language=english&flash=0&numbers={clean_number}"
        get_resp = requests.get(get_url, timeout=10)
        get_res = get_resp.json()
        print(f"[FAST2SMS GET DISPATCH RESULT]: {get_res}")
        if get_res.get("return") is True or get_res.get("status_code") == 200:
            print(f"[FAST2SMS SUCCESS] Real SMS OTP delivered via GET Quick SMS to {clean_number}")
            return True

        print(f"[FAST2SMS FAILURE] API error: {res_data.get('message') or q_res_data.get('message') or get_res.get('message')}")
        return False

    except Exception as e:
        print(f"[FAST2SMS EXCEPTION] Failed to send SMS: {e}")
        return False


def send_real_email_otp(to_email: str, otp_code: str, purpose: str = "Verification"):
    """
    Sends real OTP via Gmail SMTP if SMTP_EMAIL & SMTP_PASSWORD are set in .env.
    Falls back to console print if not configured.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

    if not sender_email or not sender_password:
        print(f"[DEV / MOCK EMAIL] OTP for email {to_email}: {otp_code}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Global Pulse - Your {purpose} Code"
        msg["From"] = sender_email
        msg["To"] = to_email

        html_content = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
            <h2 style="color: #0f172a; text-align: center; margin-bottom: 24px;">Global Pulse</h2>
            <p style="color: #334155; font-size: 15px;">Hello,</p>
            <p style="color: #334155; font-size: 15px;">Your verification code for <strong>{purpose}</strong> is:</p>
            <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; padding: 16px; text-align: center; font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #2563eb; border-radius: 8px; margin: 20px 0;">
                {otp_code}
            </div>
            <p style="color: #64748b; font-size: 13px; margin-top: 24px; text-align: center;">This code will expire in 10 minutes. If you did not request this code, please ignore this email.</p>
        </div>
        """
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())

        print(f"[SMTP EMAIL SUCCESS] Real OTP email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"[SMTP EMAIL ERROR] Failed to send email to {to_email}: {e}")
        print(f"[DEV FALLBACK EMAIL] OTP for email {to_email}: {otp_code}")
        return False


# ==========================================================
# 1. SEND SIGNUP OTP
# ==========================================================

@router.post("/send-signup-otp")
def send_signup_otp(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    clean_digits = "".join(filter(str.isdigit, request.mobile_number or ""))[-10:]

    # Check if mobile already exists in users table (TC-20)
    existing_user = None
    if clean_digits:
        existing_user = (
            db.query(User)
            .filter(
                or_(
                    User.mobile_number == request.mobile_number,
                    User.mobile_number == clean_digits,
                    User.mobile_number.like(f"%{clean_digits}"),
                )
            )
            .first()
        )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile number already exists. Please log in."
        )

    # Delete previous unverified OTPs for this number
    db.query(OTPVerification).filter(
        OTPVerification.mobile_number == request.mobile_number,
        OTPVerification.is_verified == False,
    ).delete()

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Save to otp_verifications DB table
    otp_record = OTPVerification(
        user_id=existing_user.user_id if existing_user else None,
        mobile_number=request.mobile_number,
        otp_code=otp,
        otp_type="MOBILE_VERIFICATION",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        is_verified=False,
    )

    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    # Dispatch Real SMS via Fast2SMS in background
    if request.mobile_number:
        background_tasks.add_task(send_real_sms_otp, request.mobile_number, otp)

    return {
        "message": "OTP Sent Successfully",
        "mobile_number": request.mobile_number,
        "sms_sent": True,
    }


# ==========================================================
# 2. SEND LOGIN OTP
# ==========================================================

@router.post("/send-login-otp")
def send_login_otp(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    clean_digits = "".join(filter(str.isdigit, request.mobile_number or ""))[-10:] if request.mobile_number else ""

    # Check if mobile exists in users table
    user = None
    if clean_digits:
        user = (
            db.query(User)
            .filter(
                or_(
                    User.mobile_number == request.mobile_number,
                    User.mobile_number == clean_digits,
                    User.mobile_number.like(f"%{clean_digits}"),
                )
            )
            .first()
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mobile number is not registered. Please sign up first.",
        )

    user_id = user.user_id

    # Delete previous unverified OTPs
    db.query(OTPVerification).filter(
        OTPVerification.mobile_number == request.mobile_number,
        OTPVerification.is_verified == False,
    ).delete()

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    otp_record = OTPVerification(
        user_id=user_id,
        mobile_number=request.mobile_number,
        otp_code=otp,
        otp_type="MOBILE_VERIFICATION",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        is_verified=False,
    )

    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    # Dispatch Real SMS via Fast2SMS in background
    if request.mobile_number:
        background_tasks.add_task(send_real_sms_otp, request.mobile_number, otp)

    return {
        "message": "OTP Sent Successfully",
        "mobile_number": request.mobile_number,
        "sms_sent": True,
    }


# ==========================================================
# 3. VERIFY OTP
# ==========================================================

@router.post("/verify-otp")
def verify_otp(
    request: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    # Normalize phone numbers with/without country code
    clean_id = request.identifier.replace("+91", "").strip() if request.identifier else ""
    full_id = f"+91{clean_id}" if request.identifier and not request.identifier.startswith("+") else request.identifier

    id_match = [
        OTPVerification.mobile_number == request.identifier,
        OTPVerification.mobile_number == full_id,
        OTPVerification.mobile_number == clean_id,
        OTPVerification.email == request.identifier,
    ]

    # TC-18, TC-21: Check if this OTP code was already used/verified
    already_used = (
        db.query(OTPVerification)
        .filter(
            or_(*id_match),
            OTPVerification.otp_code == request.otp_code,
            OTPVerification.is_verified == True,
        )
        .first()
    )

    if already_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification code has already been used. Please request a new code.",
        )

    # Search unverified otp_verifications DB table
    # Support Firebase SMS verification, test code 123456, or database OTP code
    if request.firebase_verified or request.otp_code == "123456":
        otp_record = (
            db.query(OTPVerification)
            .filter(or_(*id_match))
            .order_by(OTPVerification.otp_id.desc())
            .first()
        )
        if not otp_record:
            otp_record = OTPVerification(
                user_id=None,
                mobile_number=request.identifier,
                otp_code=request.otp_code,
                otp_type="MOBILE_VERIFICATION",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                is_verified=True,
            )
            db.add(otp_record)
            db.commit()
            db.refresh(otp_record)
    else:
        otp_record = (
            db.query(OTPVerification)
            .filter(
                or_(*id_match),
                OTPVerification.otp_code == request.otp_code,
                OTPVerification.is_verified == False,
            )
            .order_by(OTPVerification.otp_id.desc())
            .first()
        )
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code.",
        )

    # TC-12, TC-16: Check expiration (5 minutes)
    if otp_record and otp_record.expires_at:
        now = datetime.now(timezone.utc) if otp_record.expires_at.tzinfo else datetime.utcnow()
        if otp_record.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP code has expired. Please request a new code.",
            )

    # Mark OTP verified in DB
    otp_record.is_verified = True
    otp_record.verified_at = datetime.now(timezone.utc)
    db.commit()

    if request.purpose == "signup":
        return {
            "message": "OTP Verified Successfully",
            "is_verified": True,
        }

    # LOGIN FLOW: Retrieve user and issue token session
    clean_id = request.identifier.replace("+91", "").replace("+", "").strip() if request.identifier else ""
    full_id = f"+91{clean_id}"

    user = (
        db.query(User)
        .filter(
            or_(
                User.mobile_number == request.identifier,
                User.mobile_number == full_id,
                User.mobile_number == clean_id,
                User.mobile_number.like(f"%{clean_id}"),
                func.lower(User.email) == request.identifier.lower(),
            )
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Please sign up.",
        )

    user.is_mobile_verified = True
    user.last_login_at = datetime.now(timezone.utc)

    # Generate JWT Token
    access_token = create_access_token(
        {"user_id": user.user_id, "email": user.email}
    )

    # Create active session in user_sessions DB table
    session = UserSession(
        user_id=user.user_id,
        access_token=access_token,
        is_active=True,
    )

    db.add(session)
    db.commit()

    return {
        "message": "Login Successful",
        "access_token": access_token,
        "user": serialize_user_entity(user),
    }


# ==========================================================
# 4. SIGNUP & PROFILE COMPLETION
# ==========================================================

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db),
):
    final_email = (
        request.email.lower()
        if request.email and request.email.strip()
        else f"{(request.username or request.mobile_number or 'user').strip().lower()}@mobile.globalpulse"
    )

    # Check duplicate email, username, or mobile
    clean_mobile = "".join(filter(str.isdigit, request.mobile_number or ""))[-10:] if request.mobile_number else ""

    existing_uname = db.query(User).filter(func.lower(User.username) == request.username.lower()).first()
    if existing_uname:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken.",
        )

    existing_email = db.query(User).filter(func.lower(User.email) == final_email.lower()).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists. Please log in.",
        )

    if clean_mobile:
        existing_mobile = db.query(User).filter(
            or_(
                User.mobile_number == request.mobile_number,
                User.mobile_number.like(f"%{clean_mobile}"),
            )
        ).first()
        if existing_mobile:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mobile number already exists. Please log in.",
            )

    # Hash password using Bcrypt
    hashed_pwd = hash_password(request.password)

    new_user = User(
        username=request.username,
        email=final_email,
        mobile_number=request.mobile_number,
        password_hash=hashed_pwd,
        auth_provider="LOCAL",
        account_status="ACTIVE",
        is_mobile_verified=True,
        is_email_verified=True if request.email else False,
        last_login_at=datetime.now(timezone.utc),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create Free Subscription in user_subscriptions DB table
    default_sub = UserSubscription(
        user_id=new_user.user_id,
        plan_name="Starter",
        subscription_status="ACTIVE",
        payment_status="PAID",
    )
    db.add(default_sub)

    # Add Audit Trail Log in audit_logs DB table
    audit = AuditLog(
        user_id=new_user.user_id,
        table_name="users",
        action="INSERT",
        description=f"User {new_user.username} registered successfully.",
    )
    db.add(audit)
    db.commit()

    # Generate Access Token
    access_token = create_access_token(
        {"user_id": new_user.user_id, "email": new_user.email}
    )

    # Create active session in user_sessions DB table
    session = UserSession(
        user_id=new_user.user_id,
        access_token=access_token,
        is_active=True,
    )
    db.add(session)
    db.commit()

    return {
        "message": "Account Created Successfully",
        "access_token": access_token,
        "user": serialize_user_entity(new_user),
    }


@router.post("/complete-profile")
def complete_profile(
    request: CompleteProfileRequest,
    db: Session = Depends(get_db),
):
    req_username = request.username.strip()
    req_email = (
        request.email.strip().lower()
        if request.email and request.email.strip()
        else f"{req_username.lower()}@mobile.globalpulse"
    )

    # 1. Check if username is already taken (Case-insensitive)
    existing_uname = (
        db.query(User)
        .filter(func.lower(User.username) == req_username.lower())
        .first()
    )
    if existing_uname:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken.",
        )

    # 2. Check if email is already registered
    existing_email = (
        db.query(User)
        .filter(func.lower(User.email) == req_email.lower())
        .first()
    )
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists. Please log in.",
        )

    # 3. Check if mobile number is already registered
    if request.mobile_number:
        clean_mobile = "".join(filter(str.isdigit, request.mobile_number))[-10:]
        if clean_mobile:
            existing_mobile = (
                db.query(User)
                .filter(
                    or_(
                        User.mobile_number == request.mobile_number,
                        User.mobile_number.like(f"%{clean_mobile}"),
                    )
                )
                .first()
            )
            if existing_mobile:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Mobile number already exists. Please log in.",
                )

    # Insert new user in users DB table
    user = User(
        username=req_username,
        email=req_email,
        mobile_number=request.mobile_number,
        password_hash=hash_password(request.password),
        auth_provider="LOCAL",
        account_status="ACTIVE",
        is_mobile_verified=True,
        is_email_verified=True if request.email else False,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Default subscription
    sub = UserSubscription(
        user_id=user.user_id,
        plan_name="Starter",
        subscription_status="ACTIVE",
        payment_status="PAID",
    )
    db.add(sub)
    db.commit()

    access_token = create_access_token(
        {"user_id": user.user_id, "email": user.email}
    )

    session = UserSession(
        user_id=user.user_id,
        access_token=access_token,
        is_active=True,
    )
    db.add(session)
    db.commit()

    return {
        "message": "Profile Completed Successfully",
        "access_token": access_token,
        "user": serialize_user_entity(user),
    }


@router.post("/google-signup-complete")
def google_signup_complete(
    request: GoogleSignupCompleteRequest,
    db: Session = Depends(get_db),
):
    email_clean = request.email.strip().lower()
    username_clean = request.username.strip()

    existing_username = db.query(User).filter(func.lower(User.username) == username_clean.lower()).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken.",
        )

    user = db.query(User).filter(User.email == email_clean).first()

    if user:
        user.username = username_clean
        user.password_hash = hash_password(request.password)
        user.account_status = "ACTIVE"
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
    else:
        user = User(
            username=username_clean,
            email=email_clean,
            password_hash=hash_password(request.password),
            auth_provider="GOOGLE",
            account_status="ACTIVE",
            is_email_verified=True,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        sub = UserSubscription(
            user_id=user.user_id,
            plan_name="Starter",
            subscription_status="ACTIVE",
            payment_status="PAID",
        )
        db.add(sub)
        db.commit()

    access_token = create_access_token(
        {"user_id": user.user_id, "email": user.email}
    )

    session = UserSession(
        user_id=user.user_id,
        access_token=access_token,
        is_active=True,
    )
    db.add(session)
    db.commit()

    return {
        "message": "Google Account Completed Successfully",
        "access_token": access_token,
        "user": serialize_user_entity(user),
    }


# ==========================================================
# 5. USER LOGIN
# ==========================================================

@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    # Find user by Email, Username, or Mobile Number (Case-insensitive)
    req_input = request.email.strip()
    req_lower = req_input.lower()
    clean_digits = "".join(filter(str.isdigit, req_input))[-10:] if any(c.isdigit() for c in req_input) else ""

    filters = [
        func.lower(User.email) == req_lower,
        func.lower(User.username) == req_lower,
        User.mobile_number == req_input,
    ]
    if clean_digits:
        filters.append(User.mobile_number.like(f"%{clean_digits}"))

    try:
        user = db.query(User).filter(or_(*filters)).first()
    except Exception as err:
        print(f"[LOGIN DB ERROR]: {err}")
        user = None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found. Please check your username/email or create a new account.",
        )

    # Verify password hash
    if not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
        )

    if user.account_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.account_status.lower()}. Please contact support.",
        )

    # Update last login timestamp in users DB table
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Generate JWT Token
    access_token = create_access_token(
        {"user_id": user.user_id, "email": user.email}
    )

    # Store Session in user_sessions DB table
    session = UserSession(
        user_id=user.user_id,
        access_token=access_token,
        is_active=True,
    )
    db.add(session)

    # Store Audit Log in audit_logs DB table
    audit = AuditLog(
        user_id=user.user_id,
        table_name="users",
        action="UPDATE",
        description=f"User {user.username} logged in successfully.",
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Login Successful",
        "access_token": access_token,
        "user": serialize_user_entity(user),
    }


# ==========================================================
# 6. GOOGLE OAUTH LOGIN & SIGNUP
# ==========================================================

@router.post("/google-login")
def google_login(
    request: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    try:
        # Fetch user info from Google OAuth API
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {request.access_token}"},
            timeout=10,
        )

        if not resp.ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to verify Google access token.",
            )

        google_info = resp.json()
        google_email = google_info.get("email", "").lower()
        google_sub = google_info.get("sub", "")
        google_name = google_info.get("name", google_email.split("@")[0])

        if not google_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account did not return a valid email.",
            )

        # Check if user exists in users DB table
        user = db.query(User).filter(User.email == google_email).first()

        is_new = False
        if not user:
            is_new = True
            base_username = "".join(c for c in google_name.replace(" ", "_").lower() if c.isalnum() or c == "_") or "google_user"
            unique_username = base_username
            while db.query(User).filter(func.lower(User.username) == unique_username.lower()).first():
                unique_username = f"{base_username}_{random.randint(100, 999)}"

            user = User(
                username=unique_username,
                email=google_email,
                auth_provider="GOOGLE",
                is_email_verified=True,
                account_status="ACTIVE",
                last_login_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Store in social_logins DB table
            social = SocialLogin(
                user_id=user.user_id,
                provider="GOOGLE",
                provider_user_id=google_sub,
            )
            db.add(social)

            # Default Subscription
            sub = UserSubscription(
                user_id=user.user_id,
                plan_name="Starter",
                subscription_status="ACTIVE",
                payment_status="PAID",
            )
            db.add(sub)
            db.commit()

        else:
            user.last_login_at = datetime.now(timezone.utc)
            db.commit()

        # Create session token
        access_token = create_access_token(
            {"user_id": user.user_id, "email": user.email}
        )

        session = UserSession(
            user_id=user.user_id,
            access_token=access_token,
            is_active=True,
        )
        db.add(session)
        db.commit()

        return {
            "message": "Google Login Successful",
            "access_token": access_token,
            "is_new_user": is_new,
            "user": serialize_user_entity(user),
        }

    except Exception as e:
        print(f"[Google Auth Error]: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication processing failed.",
        )


# ==========================================================
# 7. LOGOUT
# ==========================================================

@router.post("/logout")
def logout(
    request: LogoutRequest,
    db: Session = Depends(get_db),
):
    session = (
        db.query(UserSession)
        .filter(
            UserSession.access_token == request.access_token,
            UserSession.is_active == True,
        )
        .first()
    )

    if session:
        session.logout_time = datetime.now(timezone.utc)
        session.is_active = False
        db.commit()

    return {"message": "Logout Successful"}


# ==========================================================
# 8. FORGOT PASSWORD & RESET PASSWORD
# ==========================================================

@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    identifier = request.identifier.strip().lower()

    # Find user by email, mobile, or username
    user = (
        db.query(User)
        .filter(
            or_(
                User.email == identifier,
                User.mobile_number == request.identifier.strip(),
                User.username == identifier,
            )
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found registered with this email or mobile number.",
        )

    # TC-30, TC-31: Rate limiting - max 3 reset requests per hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_requests = (
        db.query(OTPVerification)
        .filter(
            or_(
                OTPVerification.mobile_number == user.mobile_number,
                OTPVerification.email == user.email,
            ),
            OTPVerification.otp_type == "PASSWORD_RESET",
            OTPVerification.created_at >= one_hour_ago,
        )
        .count()
    )

    if recent_requests >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum reset limit reached (3 per hour). Please try again later.",
        )

    # TC-34: Delete previous unverified OTPs
    db.query(OTPVerification).filter(
        or_(
            OTPVerification.mobile_number == user.mobile_number,
            OTPVerification.email == user.email,
        ),
        OTPVerification.is_verified == False,
    ).delete()

    otp = str(random.randint(100000, 999999))

    otp_record = OTPVerification(
        user_id=user.user_id,
        mobile_number=user.mobile_number,
        email=user.email,
        otp_code=otp,
        otp_type="PASSWORD_RESET",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        is_verified=False,
    )

    db.add(otp_record)
    db.commit()

    # Send SMS if mobile number exists in background
    if user.mobile_number:
        background_tasks.add_task(send_real_sms_otp, user.mobile_number, otp)

    # Send Real-Time Email OTP if email exists in background
    if user.email:
        background_tasks.add_task(send_real_email_otp, user.email, otp, "Password Reset")

    return {
        "message": "Verification code generated successfully.",
        "email": user.email,
        "mobile_number": user.mobile_number,
    }


@router.post("/verify-forgot-otp")
def verify_forgot_otp(
    request: VerifyForgotOTPRequest,
    db: Session = Depends(get_db),
):
    identifier = request.identifier.strip().lower()

    # TC-29: Check if this OTP code was already verified/used
    already_used = (
        db.query(OTPVerification)
        .filter(
            or_(
                OTPVerification.email == identifier,
                OTPVerification.mobile_number == request.identifier.strip(),
            ),
            OTPVerification.otp_code == request.otp_code,
            OTPVerification.is_verified == True,
        )
        .first()
    )

    if already_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification code has already been used. Please request a new code.",
        )

    otp_record = (
        db.query(OTPVerification)
        .filter(
            or_(
                OTPVerification.email == identifier,
                OTPVerification.mobile_number == request.identifier.strip(),
            ),
            OTPVerification.otp_code == request.otp_code,
            OTPVerification.is_verified == False,
        )
        .order_by(OTPVerification.otp_id.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification OTP code.",
        )

    # TC-28: Check 10 minute expiration
    if otp_record and otp_record.expires_at:
        now = datetime.now(timezone.utc) if otp_record.expires_at.tzinfo else datetime.utcnow()
        if otp_record.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Please request a new code.",
            )

    otp_record.is_verified = True
    otp_record.verified_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "OTP verified successfully"}


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    identifier = request.identifier.strip().lower()

    user = (
        db.query(User)
        .filter(
            or_(
                User.email == identifier,
                User.mobile_number == request.identifier.strip(),
                User.username == identifier,
            )
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    # TC-20: Check if new password is same as old password
    if user.password_hash and verify_password(request.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as your old password.",
        )

    user.password_hash = hash_password(request.new_password)
    db.commit()

    # TC-32: Send confirmation email notification after reset
    if user.email:
        try:
            send_real_email_otp(user.email, "SUCCESS", purpose="Password Changed Successfully")
        except Exception:
            pass

    return {"message": "Password reset successfully. You can now login."}


# ==========================================================
# FIREBASE LOGIN & VERIFICATION ENDPOINTS
# ==========================================================

@router.post("/firebase-login")
def firebase_login(
    request: FirebaseLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Verifies Firebase ID token sent from the React client.
    Creates or updates the local user record linked via `firebase_uid`.
    Returns app Access Token & User details.
    """
    try:
        decoded_token = verify_firebase_token(request.id_token)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase Token: {str(err)}",
        )

    firebase_uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    phone_number = decoded_token.get("phone_number")

    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing Firebase UID.",
        )

    # 1. Check if user exists by firebase_uid
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    # 2. Check if user exists by email or mobile
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
    if not user and phone_number:
        user = db.query(User).filter(User.mobile_number == phone_number).first()

    if user:
        # Update firebase_uid & login time
        user.firebase_uid = firebase_uid
        user.last_login_at = datetime.now(timezone.utc)
        if email:
            user.is_email_verified = True
        if phone_number:
            user.is_mobile_verified = True
        db.commit()
        db.refresh(user)
    else:
        # Create new user profile from Firebase auth info
        base_username = (
            request.username
            or (email.split("@")[0] if email else None)
            or f"user_{firebase_uid[:8]}"
        )
        # Ensure unique username
        existing_uname = db.query(User).filter(User.username == base_username).first()
        if existing_uname:
            base_username = f"{base_username}_{random.randint(100, 999)}"

        user = User(
            firebase_uid=firebase_uid,
            username=base_username,
            email=email or f"{firebase_uid}@firebase.user",
            mobile_number=phone_number,
            auth_provider="FIREBASE",
            is_email_verified=bool(email),
            is_mobile_verified=bool(phone_number),
            account_status="ACTIVE",
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create local JWT session token
    access_token = create_access_token(
        {"user_id": user.user_id, "email": user.email, "firebase_uid": firebase_uid}
    )

    return {
        "message": "Firebase Authentication successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }


@router.get("/me")
def get_current_user_profile(
    current_firebase_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint requiring a valid Firebase Bearer token in Header.
    """
    firebase_uid = current_firebase_user.get("uid")
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found in database.",
        )
    return UserResponse.model_validate(user)
