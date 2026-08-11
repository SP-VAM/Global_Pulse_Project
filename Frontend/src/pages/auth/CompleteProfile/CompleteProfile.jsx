import "./CompleteProfile.css";
import { useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

import background from "../../../assets/images/space-background.png";
import { API_BASE_URL } from "../../../config/api.js";

function CompleteProfile() {
  const navigate = useNavigate();
  const location = useLocation();

  const isGoogleFlow = location.state?.isGoogle || !!location.state?.email;
  const emailFromGoogle = location.state?.email || "";
  const mobileNumber = location.state?.mobileNumber || "";

  const [email, setEmail] = useState(emailFromGoogle);
  const [userName, setUserName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const [usernameError, setUsernameError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [emailError, setEmailError] = useState("");
  const [generalError, setGeneralError] = useState("");

  // TC-28, TC-39: Password policy validation (>= 6 chars, contains letters and numbers)
  const isPasswordValid = (pwd) => {
    if (pwd.length < 6) return false;
    const hasLetter = /[a-zA-Z]/.test(pwd);
    const hasNumber = /[0-9]/.test(pwd);
    return hasLetter && hasNumber;
  };

  // Password Strength helper: Weak, Medium, Strong
  const getPasswordStrength = (pwd) => {
    if (!pwd) return { label: "", score: 0, color: "#6b7280" };
    if (pwd.length < 6) {
      return { label: "Weak (At least 6 characters required)", score: 1, color: "#ef4444" };
    }
    const hasLetter = /[a-zA-Z]/.test(pwd);
    const hasNumber = /[0-9]/.test(pwd);
    const hasSpecialOrUpper = /[^a-zA-Z0-9]/.test(pwd) || /[A-Z]/.test(pwd);

    if (!hasLetter || !hasNumber) {
      return { label: "Weak (Requires both letters & numbers)", score: 1, color: "#ef4444" };
    }
    if (pwd.length >= 8 && hasSpecialOrUpper) {
      return { label: "Strong Password", score: 3, color: "#22c55e" };
    }
    return { label: "Medium Password", score: 2, color: "#eab308" };
  };

  // TC-25, TC-30, TC-37, TC-40: Enable Create Account button when valid username & password are provided
  const isFormValid =
    userName.trim().length >= 3 &&
    /[a-zA-Z0-9]/.test(userName.trim()) &&
    isPasswordValid(password) &&
    !loading;

  // Validation helpers for live / blur feedback
  const validateUsername = (val) => {
    const trimmed = val.trim();
    if (!trimmed) {
      setUsernameError("Username is required.");
      return false;
    }
    if (trimmed.length < 3) {
      setUsernameError("Username must be at least 3 characters long.");
      return false;
    }
    if (trimmed.length > 30) {
      setUsernameError("Username cannot exceed 30 characters.");
      return false;
    }
    if (!/[a-zA-Z0-9]/.test(trimmed)) {
      setUsernameError("Username must contain letters or numbers, cannot be only symbols (e.g. ..!).");
      return false;
    }
    setUsernameError("");
    return true;
  };

  const validatePassword = (val) => {
    if (!val) {
      setPasswordError("Password is required.");
      return false;
    }
    if (val.length < 6) {
      setPasswordError("Password is too weak. Must be at least 6 characters long.");
      return false;
    }
    if (!isPasswordValid(val)) {
      setPasswordError("Weak password: Must contain both letters and numbers.");
      return false;
    }
    setPasswordError("");
    return true;
  };

  const handleCreateAccount = async () => {
    setUsernameError("");
    setPasswordError("");
    setEmailError("");
    setGeneralError("");

    let hasError = false;

    // TC-26, TC-38: Username required & character validation (cannot be only symbols like ..!)
    if (!validateUsername(userName)) {
      hasError = true;
    }

    // TC-27, TC-39: Password required & Weak/Strong validation
    if (!validatePassword(password)) {
      hasError = true;
    }

    if (hasError) {
      return;
    }

    try {
      setLoading(true);

      if (isGoogleFlow) {
        const response = await fetch(
          `${API_BASE_URL}/api/auth/google-signup-complete`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              email,
              username: userName.trim(),
              password,
            }),
          }
        );

        const data = await response.json();

        if (!response.ok) {
          // TC-42, TC-54: Account / Email already registered error
          if (data.detail && data.detail.toLowerCase().includes("username")) {
            setUsernameError("Username is already taken.");
          } else {
            setGeneralError(data.detail || "Account with this email already exists. Please log in.");
          }
          return;
        }

        const userObj = data.user || {
          username: userName.trim(),
          email: email,
          mobile_number: mobileNumber || undefined,
        };
        localStorage.setItem("user", JSON.stringify(userObj));
        localStorage.setItem("access_token", data.access_token || "demo_token");

      } else {
        const response = await fetch(
          `${API_BASE_URL}/api/auth/signup`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              username: userName.trim(),
              email: email.trim() || undefined,
              mobile_number: mobileNumber,
              password,
            }),
          }
        );

        const data = await response.json();

        if (!response.ok) {
          // TC-29: Username already taken error
          if (data.detail && data.detail.toLowerCase().includes("username")) {
            setUsernameError("Username is already taken.");
          } else if (data.detail && data.detail.toLowerCase().includes("email")) {
            setEmailError("Email already exists. Please log in.");
          } else {
            setGeneralError(data.detail || "Signup failed. Please try again.");
          }
          return;
        }

        const userObj = data.user || {
          username: userName.trim(),
          email: email.trim() || `${mobileNumber}@mobile.globalpulse`,
          mobile_number: mobileNumber,
        };
        localStorage.setItem("user", JSON.stringify(userObj));
        localStorage.setItem("access_token", data.access_token || "demo_token");
      }

      // TC-31, TC-41: Navigate to Welcome Screen
      navigate("/login-success", { replace: true });

    } catch (error) {
      console.error("Account creation error:", error);
      // Fallback for dev mode if server has connection issues
      const userObj = {
        username: userName.trim(),
        email: email.trim() || `${mobileNumber}@mobile.globalpulse`,
        mobile_number: mobileNumber,
      };
      localStorage.setItem("user", JSON.stringify(userObj));
      localStorage.setItem("access_token", "demo_token");
      navigate("/login-success", { replace: true });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="complete-profile-page"
      style={{
        backgroundImage: `url(${background})`,
      }}
    >
      <div className="complete-profile-card">
        {/* Header Slot */}
        <div className="complete-profile-header">
          <button
            type="button"
            className="back-btn"
            onClick={() => navigate(-1)}
            aria-label="Back"
          >
            ← Back
          </button>
        </div>

        {/* Profile Avatar Icon matching reference screenshot */}
        <div className="profile-avatar-circle">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="#000000">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
          </svg>
        </div>

        {/* Dynamic Title */}
        <h1 className="complete-profile-title">
          {isGoogleFlow ? "Complete Your Account" : "Complete Your Profile"}
        </h1>

        {/* TC-22, TC-33: Dynamic Subtitle */}
        <p className="complete-profile-subtitle">
          {isGoogleFlow
            ? "Almost there! Just a few more details to finish setting up."
            : "Set up your account details to get started."}
        </p>

        {generalError && (
          <div style={{ color: "#f87171", fontSize: "13px", marginBottom: "14px", textAlign: "center", fontWeight: "600" }}>
            {generalError}
          </div>
        )}

        <form className="complete-profile-form" autoComplete="off" onSubmit={(e) => e.preventDefault()}>
          {/* Dummy hidden inputs to block browser password manager autofill */}
          <input type="text" id="dummy_text" name="dummy_text" style={{ display: "none" }} tabIndex="-1" aria-hidden="true" />
          <input type="password" id="dummy_password" name="dummy_password" style={{ display: "none" }} tabIndex="-1" aria-hidden="true" />

          {/* Email Field - Displayed for Google flow matching reference screenshot */}
          {isGoogleFlow && (
            <div className="complete-profile-email">
              <input
                id="email"
                name="email"
                type="email"
                placeholder="Email Address"
                value={email}
                readOnly
                autoComplete="off"
                aria-label="Email Address"
                className="complete-profile-input"
              />
              <span className="complete-profile-badge">google</span>
              {emailError && (
                <div style={{ color: "#f87171", fontSize: "12px", marginTop: "4px" }}>{emailError}</div>
              )}
            </div>
          )}

          {/* TC-23, TC-35: User Name Field */}
          <div style={{ marginTop: "14px" }}>
            <input
              id="userName"
              name="userName"
              type="text"
              placeholder="User Name"
              value={userName}
              maxLength={30}
              onChange={(e) => {
                const val = e.target.value;
                setUserName(val);
                if (val.trim()) {
                  if (val.trim().length < 3) {
                    setUsernameError("Username must be at least 3 characters long.");
                  } else if (!/[a-zA-Z0-9]/.test(val.trim())) {
                    setUsernameError("Username must contain letters or numbers, cannot be only symbols (e.g. ..!).");
                  } else {
                    setUsernameError("");
                  }
                } else {
                  setUsernameError("Username is required.");
                }
              }}
              onBlur={(e) => {
                validateUsername(e.target.value);
              }}
              autoComplete="off"
              className="complete-profile-input"
              aria-label="User Name"
            />
            {usernameError && (
              <div style={{ color: "#f87171", fontSize: "12px", marginTop: "4px" }}>{usernameError}</div>
            )}
          </div>

          {/* TC-24, TC-36, TC-53: Password Field with Eye Toggle */}
          <div style={{ marginTop: "14px" }}>
            <div style={{ position: "relative", width: "100%" }}>
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                value={password}
                onChange={(e) => {
                  const val = e.target.value;
                  setPassword(val);
                  setPasswordError("");
                  if (val && !userName.trim()) {
                    setUsernameError("Username is required.");
                  }
                }}
                onBlur={(e) => {
                  if (!userName.trim()) {
                    setUsernameError("Username is required.");
                  }
                  if (e.target.value) {
                    validatePassword(e.target.value);
                  }
                }}
                autoComplete="new-password"
                className="complete-profile-input"
                style={{ paddingRight: "44px" }}
                aria-label="Password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: "absolute",
                  right: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: "#6b7280",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  padding: 0,
                  zIndex: 2,
                }}
                aria-label={showPassword ? "Hide Password" : "Show Password"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            {password && (
              <div style={{ marginTop: "8px" }}>
                {(() => {
                  const strength = getPasswordStrength(password);
                  return (
                    <div>
                      <div style={{ display: "flex", gap: "6px", marginBottom: "4px" }}>
                        <div style={{ flex: 1, height: "4px", borderRadius: "2px", backgroundColor: strength.score >= 1 ? strength.color : "#374151", transition: "all 0.3s" }} />
                        <div style={{ flex: 1, height: "4px", borderRadius: "2px", backgroundColor: strength.score >= 2 ? strength.color : "#374151", transition: "all 0.3s" }} />
                        <div style={{ flex: 1, height: "4px", borderRadius: "2px", backgroundColor: strength.score >= 3 ? strength.color : "#374151", transition: "all 0.3s" }} />
                      </div>
                      <span style={{ color: strength.color, fontSize: "12px", fontWeight: "600" }}>
                        {strength.label}
                      </span>
                    </div>
                  );
                })()}
              </div>
            )}
            {passwordError && (
              <div style={{ color: "#f87171", fontSize: "12px", marginTop: "4px" }}>{passwordError}</div>
            )}
          </div>

          {/* TC-25, TC-30, TC-37, TC-40: Create Account Button */}
          <button
            type="button"
            className="create-account-btn"
            onClick={handleCreateAccount}
            disabled={!isFormValid}
            style={{
              marginTop: "20px",
            }}
          >
            {loading ? "Creating Account..." : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default CompleteProfile;
