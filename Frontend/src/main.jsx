import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { GoogleOAuthProvider } from "@react-oauth/google";
// import { GoogleOAuthProvider } from "@react-oauth/google";

import App from "./App.jsx";
import "./styles/global.css";

// import "./styles/global.css";
import "./styles/auth_legacy.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID || "515335749994-cfdtgpa99tu6rni2hjggc7ktud1olp8b.apps.googleusercontent.com"}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </GoogleOAuthProvider>
  </React.StrictMode>
);