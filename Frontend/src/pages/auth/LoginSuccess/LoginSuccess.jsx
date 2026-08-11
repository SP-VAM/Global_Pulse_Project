import "./LoginSuccess.css";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { CheckCircle2 } from "lucide-react";

import background from "../../../assets/images/space-background.png";
import successIcon from "../../../assets/images/success.png";

function LoginSuccess() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("user") || "{}");
  const usernameDisplay = user?.username || user?.full_name || "john";

  // TC-55: Handle browser back button post-signup to prevent duplicate creation
  useEffect(() => {
    const handlePopState = (e) => {
      e.preventDefault();
      navigate("/dashboard", { replace: true });
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [navigate]);

  return (
    <div
      className="success-page"
      style={{
        backgroundImage: `url(${background})`,
      }}
    >
      <div className="success-card">
        {/* TC-44: Success checkmark icon */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px" }}>
          {successIcon ? (
            <img src={successIcon} alt="Success Icon" className="success-icon" />
          ) : (
            <CheckCircle2 size={64} color="#10b981" />
          )}
        </div>

        {/* TC-45: Dynamic welcome message "Welcome aboard, [username]!" */}
        <h1 className="success-title">
          Welcome aboard,
          <br />
          {usernameDisplay}! 🎉
        </h1>

        {/* TC-46: Confirmation description text */}
        <p className="success-subtitle">
          Your account has been created successfully! Everything is ready for you.
        </p>

        {/* TC-47, TC-48: 'Go to Dashboard' button */}
        <button
          className="dashboard-btn"
          type="button"
          onClick={() => navigate("/dashboard", { replace: true })}
        >
          Go to Dashboard →
        </button>
      </div>
    </div>
  );
}

export default LoginSuccess;
