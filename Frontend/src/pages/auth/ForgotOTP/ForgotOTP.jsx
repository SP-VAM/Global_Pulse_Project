import "./ForgotOTP.css";
import { useNavigate, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";

import background from "../../../assets/images/space-background.png";

function ForgotOTP() {
  const navigate = useNavigate();
  const location = useLocation();

  const identifier = location.state?.identifier || "";

  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendTimer, setResendTimer] = useState(30);
  const [toastMessage, setToastMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let timer;
    if (resendTimer > 0) {
      timer = setInterval(() => {
        setResendTimer((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [resendTimer]);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(""), 4000);
  };

  const handleChange = (value, index) => {
    if (!/^\d?$/.test(value)) return;
    setErrorMessage("");

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    if (value && index < 5) {
      const nextInput = document.getElementById(`otp-${index + 1}`);
      if (nextInput) nextInput.focus();
    }

    if (value && index === 5 && newOtp.join("").length === 6) {
      triggerVerification(newOtp.join(""));
    }
  };

  const handleKeyDown = (e, index) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      const prevInput = document.getElementById(`otp-${index - 1}`);
      if (prevInput) {
        prevInput.focus();
        const newOtp = [...otp];
        newOtp[index - 1] = "";
        setOtp(newOtp);
      }
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").trim();
    if (!/^\d{6}$/.test(pastedData)) return;

    const digits = pastedData.split("");
    setOtp(digits);
    const lastInput = document.getElementById("otp-5");
    if (lastInput) lastInput.focus();

    triggerVerification(pastedData);
  };

  const triggerVerification = async (codeToVerify) => {
    if (codeToVerify.length !== 6) {
      setErrorMessage("Please enter a valid 6-digit OTP code.");
      return;
    }

    try {
      setLoading(true);
      setErrorMessage("");

      const response = await fetch(
        "http://127.0.0.1:8000/api/auth/verify-forgot-otp",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            identifier,
            otp_code: codeToVerify,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setErrorMessage(data.detail || "Invalid verification code.");
        return;
      }

      showToast("OTP verified successfully!");
      setTimeout(() => {
        navigate("/reset-password", {
          state: { identifier },
        });
      }, 500);

    } catch (err) {
      console.error(err);
      setErrorMessage("Unable to connect to server. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendTimer > 0 || resending) return;

    try {
      setResending(true);
      setErrorMessage("");

      const response = await fetch(
        "http://127.0.0.1:8000/api/auth/forgot-password",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ identifier }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setErrorMessage(data.detail || "Unable to resend OTP code.");
        return;
      }

      showToast("A new verification code has been sent!");
      setOtp(["", "", "", "", "", ""]);
      setResendTimer(30);
      const firstInput = document.getElementById("otp-0");
      if (firstInput) firstInput.focus();

    } catch (err) {
      console.error(err);
      setErrorMessage("Server error during OTP resend.");
    } finally {
      setResending(false);
    }
  };

  return (
    <div
      className="forgot-otp-page"
      style={{
        backgroundImage: `url(${background})`,
      }}
    >
      <div className="forgot-otp-card">
        {/* Header Slot */}
        <div className="forgot-otp-header">
          <button
            type="button"
            className="back-btn"
            onClick={() => navigate("/forgot-password")}
            aria-label="Back to Forgot Password"
          >
            ← Back
          </button>
        </div>

        {/* Title */}
        <h1 className="forgot-otp-title">
          Verify Your
          <br />
          Account
        </h1>

        {/* Subtitle */}
        <p className="forgot-otp-subtitle">
          Enter the 6-digit verification code sent to{" "}
          <strong style={{ color: "#ffffff" }}>{identifier || "+91 1234567890"}</strong>
        </p>

        {toastMessage && (
          <div
            style={{
              background: "rgba(16, 185, 129, 0.15)",
              border: "1px solid rgba(16, 185, 129, 0.4)",
              color: "#34d399",
              borderRadius: "8px",
              padding: "10px 14px",
              fontSize: "13px",
              fontWeight: "600",
              margin: "12px 0",
              textAlign: "center",
            }}
          >
            {toastMessage}
          </div>
        )}

        {errorMessage && (
          <div
            style={{
              background: "rgba(239, 68, 68, 0.15)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              color: "#f87171",
              borderRadius: "8px",
              padding: "10px 14px",
              fontSize: "13px",
              fontWeight: "600",
              margin: "12px 0",
              textAlign: "center",
            }}
          >
            {errorMessage}
          </div>
        )}

        <div className="otp-container" onPaste={handlePaste}>
          {otp.map((digit, index) => (
            <input
              key={index}
              id={`otp-${index}`}
              name={`otp-${index}`}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              className="otp-input"
              onChange={(e) => handleChange(e.target.value, index)}
              onKeyDown={(e) => handleKeyDown(e, index)}
              aria-label={`OTP Digit ${index + 1}`}
            />
          ))}
        </div>

        <button
          className="verify-btn"
          disabled={otp.join("").length !== 6 || loading}
          onClick={() => triggerVerification(otp.join(""))}
        >
          {loading ? "Verifying..." : "Verify"}
        </button>

        <p className="resend-text">
          Didn't receive the code?{" "}
          <button
            type="button"
            className="resend-btn"
            disabled={resendTimer > 0 || resending}
            onClick={handleResend}
            style={{
              background: "none",
              border: "none",
              color: resendTimer > 0 ? "#6b7280" : "#3b82f6",
              cursor: resendTimer > 0 ? "not-allowed" : "pointer",
              fontWeight: "600",
              marginLeft: "4px",
            }}
          >
            {resending
              ? "Sending..."
              : resendTimer > 0
              ? `Resend in ${resendTimer}s`
              : "Resend OTP"}
          </button>
        </p>
      </div>
    </div>
  );
}

export default ForgotOTP;
