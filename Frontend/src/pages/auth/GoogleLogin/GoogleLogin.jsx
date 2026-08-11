import "./GoogleLogin.css";
import { useLocation, useNavigate } from "react-router-dom";

import background from "../../../assets/images/space-background.png";

function GoogleLogin() {
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from || "login";

  return (
    <div
      className="google-login-page"
      style={{
        backgroundImage: `url(${background})`,
      }}
    >
      <div className="google-login-card">
        <button
          type="button"
          className="google-back-btn"
          onClick={() => navigate(-1)}
        >
          ← Back
        </button>

        <div className="google-profile-icon">
          <span>👤</span>
        </div>

        <h1 className="google-login-title">Google Log In</h1>

        <p className="google-login-subtitle">
          You have logged in with this Google Account
        </p>

        <div className="google-account-box">
          <input
            id="google_email"
            name="google_email"
            type="email"
            value="john.abc@gmail.com"
            readOnly
            aria-label="Google account email"
          />
          <span className="google-account-badge">google</span>
        </div>

        <button
          type="button"
          className="google-login-submit"
          onClick={() => {
            if (from === "signup") {
              navigate("/complete-profile");
            } else {
              navigate("/login-success");
            }
          }}
        >
          Log in
        </button>
      </div>
    </div>
  );
}

export default GoogleLogin;
