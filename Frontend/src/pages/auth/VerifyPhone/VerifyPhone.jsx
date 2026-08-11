import "./VerifyPhone.css";
import { useLocation, useNavigate } from "react-router-dom";
import { useState, useRef, useEffect } from "react";

import background from "../../../assets/images/space-background.png";
import { sendFirebasePhoneOTP, cleanupRecaptcha } from "../../../config/firebase.js";
import { API_BASE_URL } from "../../../config/api.js";

const COUNTRY_CONFIGS = {
  "+91": {
    name: "India (+91)",
    flag: "IN",
    code: "+91",
    maxLength: 10,
    placeholder: "9876543210",
    regex: /^[6-9]\d{9}$/,
    errorMsg: "Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.",
  },
  "+1": {
    name: "USA / Canada (+1)",
    flag: "US",
    code: "+1",
    maxLength: 10,
    placeholder: "2025550143",
    regex: /^[2-9]\d{2}[2-9]\d{6}$/,
    errorMsg: "Please enter a valid 10-digit US/Canada mobile number.",
  },
  "+44": {
    name: "UK (+44)",
    flag: "GB",
    code: "+44",
    maxLength: 10,
    placeholder: "7911123456",
    regex: /^7\d{9}$/,
    errorMsg: "Please enter a valid 10-digit UK mobile number starting with 7.",
  },
  "+61": {
    name: "Australia (+61)",
    flag: "AU",
    code: "+61",
    maxLength: 9,
    placeholder: "412345678",
    regex: /^4\d{8}$/,
    errorMsg: "Please enter a valid 9-digit Australian mobile number starting with 4.",
  },
  "+971": {
    name: "UAE (+971)",
    flag: "AE",
    code: "+971",
    maxLength: 9,
    placeholder: "501234567",
    regex: /^5\d{8}$/,
    errorMsg: "Please enter a valid 9-digit UAE mobile number starting with 5.",
  },
  "+62": {
    name: "Indonesia (+62)",
    flag: "ID",
    code: "+62",
    maxLength: 11,
    placeholder: "81313782626",
    regex: /^8\d{9,10}$/,
    errorMsg: "Please enter a valid Indonesian mobile number starting with 8.",
  },
};

function VerifyPhone() {
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from || "signup";

  const [countryCode, setCountryCode] = useState("+91");
  const [mobileNumber, setMobileNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Cleanup reCAPTCHA verifier instance on unmount/navigation
  useEffect(() => {
    return () => {
      cleanupRecaptcha();
    };
  }, []);

  // Automatic real-time validation and error clearing
  useEffect(() => {
    if (!mobileNumber) {
      if (countryCode !== "+91") {
        setErrorMessage(`International SMS (${countryCode}) requires upgrading Firebase to the Blaze plan. Please select India (+91) for free testing.`);
      } else {
        setErrorMessage("");
      }
      return;
    }

    if (countryCode !== "+91") {
      if (/^[6-9]/.test(mobileNumber)) {
        setErrorMessage("Indian mobile numbers (starting with 6, 7, 8, or 9) require India (+91) country code. Please switch to India (+91).");
      } else {
        setErrorMessage(`International SMS (${countryCode}) requires upgrading Firebase to the Blaze plan. Please select India (+91) for free testing.`);
      }
    } else {
      if (/^[1-5]/.test(mobileNumber)) {
        setErrorMessage("Indian mobile numbers must start with 6, 7, 8, or 9.");
      } else {
        setErrorMessage("");
      }
    }
  }, [countryCode, mobileNumber]);

  const currentCountry = COUNTRY_CONFIGS[countryCode] || COUNTRY_CONFIGS["+91"];

  const handleCountryChange = (e) => {
    const selectedCode = e.target.value;
    setCountryCode(selectedCode);
    const newConfig = COUNTRY_CONFIGS[selectedCode] || COUNTRY_CONFIGS["+91"];
    if (mobileNumber.length > newConfig.maxLength) {
      setMobileNumber(mobileNumber.slice(0, newConfig.maxLength));
    }
  };

  const handlePhoneInput = (e) => {
    let val = e.target.value.replace(/\D/g, "");
    if (val.startsWith("0")) {
      val = val.replace(/^0+/, "");
    }
    const trimmedVal = val.slice(0, currentCountry.maxLength);
    setMobileNumber(trimmedVal);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanedNumber = mobileNumber.trim();

    if (countryCode !== "+91") {
      if (/^[6-9]/.test(cleanedNumber)) {
        setErrorMessage("Indian mobile numbers (starting with 6, 7, 8, or 9) require India (+91) country code. Please switch to India (+91).");
        return;
      }
      setErrorMessage(`International SMS (${countryCode}) requires upgrading Firebase to the Blaze plan. Please select India (+91) for free testing.`);
      return;
    }

    if (/^[1-5]/.test(cleanedNumber)) {
      setErrorMessage("Indian mobile numbers must start with 6, 7, 8, or 9.");
      return;
    }

    if (!currentCountry.regex.test(cleanedNumber)) {
      setErrorMessage(currentCountry.errorMsg);
      return;
    }

    const fullFormattedNumber = `${countryCode}${cleanedNumber}`;

    try {
      setLoading(true);
      setErrorMessage("");

      const apiUrl =
        from === "signup"
          ? `${API_BASE_URL}/api/auth/send-signup-otp`
          : `${API_BASE_URL}/api/auth/send-login-otp`;

      let backendSuccess = false;
      try {
        const backendResp = await fetch(apiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            mobile_number: fullFormattedNumber,
          }),
        });
        if (backendResp.ok) {
          backendSuccess = true;
          const resData = await backendResp.json().catch(() => ({}));
          console.log("Backend OTP response:", resData);
        } else {
          const errData = await backendResp.json().catch(() => ({}));
          if (errData.detail) {
            let msg = errData.detail;
            if (msg.toLowerCase().includes("already registered") || msg.toLowerCase().includes("already exist")) {
              msg = "Mobile number already exists. Please log in.";
            }
            setErrorMessage(msg);
            setLoading(false);
            return;
          }
          console.warn("Backend OTP response error:", errData);
        }
      } catch (backendErr) {
        console.warn("Backend API offline, trying Firebase Phone Auth:", backendErr);
      }

      // Dispatch Firebase Real SMS as fallback if backend was not used
      let firebaseSent = false;
      if (!backendSuccess) {
        try {
          await sendFirebasePhoneOTP(fullFormattedNumber, "recaptcha-container");
          firebaseSent = true;
        } catch (fbErr) {
          console.error("Firebase Real SMS Error:", fbErr);
          let userFacingErr = fbErr.message || "Failed to send SMS code.";
          if (fbErr.code === "auth/invalid-phone-number") {
            userFacingErr = "Invalid phone number format for selected country code.";
          } else if (fbErr.code === "auth/billing-not-enabled" || fbErr.message?.includes("billing-not-enabled")) {
            userFacingErr = "Firebase SMS requires the Blaze plan for real phone numbers. For development, register this number as a test phone number in Firebase Console → Authentication → Phone Numbers for Testing.";
          } else if (fbErr.code === "auth/operation-not-allowed") {
            userFacingErr = "Phone authentication disabled in Firebase Console. Please enable Phone provider under Sign-in method, or select India (+91) for free testing.";
          } else if (fbErr.code === "auth/invalid-app-credential") {
            userFacingErr = "Domain error: Please add 'localhost' to Authorized Domains in Firebase Console Settings.";
          } else if (fbErr.code === "auth/quota-exceeded") {
            userFacingErr = "Firebase SMS daily limit exceeded.";
          } else if (fbErr.code === "auth/captcha-check-failed") {
            userFacingErr = "reCAPTCHA verification failed. Please try again.";
          }
          setErrorMessage(userFacingErr);
          return;
        }
      }

      navigate("/otp", {
        state: {
          from,
          mobileNumber: cleanedNumber,
          countryCode,
          fullPhoneNumber: fullFormattedNumber,
          firebaseSent,
        },
      });

    } catch (error) {
      console.error(error);
      setErrorMessage("An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const isButtonEnabled = mobileNumber.trim().length === currentCountry.maxLength && !loading;

  const handleContinue = handleSubmit;

  return (
    <div
      className="verify-page"
      style={{
        backgroundImage: `url(${background})`,
      }}
    >
      <div className="verify-card">
        {/* Header matching SignUp logo header slot */}
        <div className="verify-header">
          <button
            className="back-btn"
            type="button"
            onClick={() => navigate(from === "login" ? "/login" : "/signup")}
            aria-label="Back to Sign Up"
          >
            ← Back
          </button>
        </div>

        {/* Title */}
        <h1 className="verify-title">
          Verify your Mobile Number
        </h1>

        {/* Subtitle */}
        <p className="verify-subtitle">
          We'll send you a verification code to confirm your number.
        </p>

        {/* TC-11: Label & phone input row */}
        <label className="phone-label">
          Phone number
        </label>

        <div className="phone-row">
          {/* Custom Country code dropdown */}
          <div className="country-code-wrapper" ref={dropdownRef}>
            <button
              type="button"
              className="country-code-btn"
              onClick={() => setIsDropdownOpen((prev) => !prev)}
              aria-label="Select Country Code"
            >
              <span>{countryCode}</span>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="white">
                <path d="M7 10l5 5 5-5z" />
              </svg>
            </button>

            {isDropdownOpen && (
              <div className="country-dropdown-menu">
                {Object.entries(COUNTRY_CONFIGS).map(([code, config]) => (
                  <div
                    key={code}
                    className={`country-dropdown-item ${countryCode === code ? "selected" : ""}`}
                    onClick={() => {
                      setCountryCode(code);
                      setIsDropdownOpen(false);
                    }}
                  >
                    <span className="country-flag">{config.flag}</span>
                    <span className="country-name">{config.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <input
            id="mobileNumber"
            name="mobileNumber"
            type="tel"
            placeholder={currentCountry.placeholder}
            className="phone-input"
            value={mobileNumber}
            onChange={handlePhoneInput}
            maxLength={currentCountry.maxLength}
            aria-label="Phone Number Input"
          />
        </div>

        {errorMessage && (
          <div style={{ color: "#f87171", fontSize: "13px", margin: "10px 0", textAlign: "center", fontWeight: "500" }}>
            {errorMessage}
          </div>
        )}

        {/* Invisible reCAPTCHA container for Firebase Phone SMS */}
        <div id="recaptcha-container"></div>

        {/* Continue button */}

        <button
          type="button"
          className="continue-btn"
          onClick={handleContinue}
          disabled={!isButtonEnabled}
        >
          {loading ? "Sending..." : "Continue"}
        </button>
      </div>
    </div>
  );
}

export default VerifyPhone;
