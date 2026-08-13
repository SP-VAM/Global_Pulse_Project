import "./PasswordResetSuccess.css";
import { useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";

import background from "../../../assets/images/space-background.png";
import success from "../../../assets/images/success.png";

function PasswordResetSuccess() {
  const navigate = useNavigate();
  const token = localStorage.getItem("access_token");
  const isAuthenticated = token && token !== "null" && token !== "undefined" && token !== "demo_token";

  return (
    <div
      className="password-success-page"
      style={{
        backgroundImage: `url(${background})`,
      }}
    >
      <div className="password-success-card">
        {/* TC-24: Success icon */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px" }}>
          {success ? (
            <img src={success} alt="Success" className="password-success-image" />
          ) : (
            <CheckCircle2 size={64} color="#10b981" />
          )}
        </div>

        {/* TC-24: Heading */}
        <h1 className="password-success-title">
          Password Changed Successfully!
        </h1>

        {/* TC-24: Subtitle confirmation text */}
        <p className="password-success-subtitle">
          Your password has been updated in Railway PostgreSQL. You can now use your new password for all future logins.
        </p>

        {isAuthenticated ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", width: "100%" }}>
            <button
              type="button"
              className="password-success-btn"
              onClick={() => navigate("/dashboard")}
            >
              Return to Dashboard
            </button>
            <button
              type="button"
              className="password-success-btn"
              style={{ background: "rgba(255, 255, 255, 0.08)", color: "#cbd5e1" }}
              onClick={() => {
                localStorage.clear();
                navigate("/login");
              }}
            >
              Log Out & Test New Password
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="password-success-btn"
            onClick={() => navigate("/login")}
          >
            Continue to Login
          </button>
        )}
      </div>
    </div>
  );
}

export default PasswordResetSuccess;
