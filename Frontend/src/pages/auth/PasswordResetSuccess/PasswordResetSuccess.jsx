import "./PasswordResetSuccess.css";
import { useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";

import background from "../../../assets/images/space-background.png";
import success from "../../../assets/images/success.png";

function PasswordResetSuccess() {
  const navigate = useNavigate();

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
          Password Reset Successful!
        </h1>

        {/* TC-24: Subtitle confirmation text */}
        <p className="password-success-subtitle">
          Your password has been updated successfully. You can now log in using your new password.
        </p>

        {/* TC-25: Back to Login button */}
        <button
          type="button"
          className="password-success-btn"
          onClick={() => navigate("/login")}
        >
          Back to Login
        </button>
      </div>
    </div>
  );
}

export default PasswordResetSuccess;
