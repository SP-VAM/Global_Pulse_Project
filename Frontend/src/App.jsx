import { createContext, useContext, useMemo, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { UserProvider } from "./context/UserContext.jsx";

// Landing Page
import Landing from "./pages/Landing/Landing";

// Auth Pages (Clean Modular Barrel Export)
import {
  Login,
  SignUp,
  VerifyPhone,
  OTPVerification,
  ForgotPassword,
  ForgotOTP,
  ResetPassword,
  PasswordResetSuccess,
  GoogleLogin,
  LoginSuccess,
  CompleteProfile,
} from "./pages/auth";

// Dashboard Pages (Clean Modular Barrel Export)
import {
  DashboardLayout,
  Dashboard,
  Goals,
  Constituents,
  MarketAnalysis,
  LearningHub,
  ExpenseTracker,
  Investments,
  Upgrade,
  Settings,
  Profile,
} from "./pages/Dashboard";

const FlowContext = createContext(null);

export function useFlow() {
  return useContext(FlowContext);
}

export default function App() {
  const [flow, setFlow] = useState({
    country: "+91",
    phone: "",
    email: "john.abc@gmail.com",
    username: "john",
  });

  const value = useMemo(
    () => ({
      flow,
      updateFlow: (next) =>
        setFlow((current) => ({
          ...current,
          ...next,
        })),
    }),
    [flow]
  );

  return (
    <UserProvider>
      <FlowContext.Provider value={value}>
        <Routes>
          {/* Landing Page */}
          <Route path="/" element={<Landing />} />

          {/* Authentication Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/verify-phone" element={<VerifyPhone />} />
          <Route path="/otp" element={<OTPVerification />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/forgot-otp" element={<ForgotOTP />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/password-reset-success" element={<PasswordResetSuccess />} />
          <Route path="/google-login" element={<GoogleLogin />} />
          <Route path="/login-success" element={<LoginSuccess />} />
          <Route path="/complete-profile" element={<CompleteProfile />} />
          <Route path="/complete-account" element={<CompleteProfile google />} />

          {/* Protected Dashboard Routes */}
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="goals" element={<Goals />} />
            <Route path="constituents" element={<Constituents />} />
            <Route path="market-analysis" element={<MarketAnalysis />} />
            <Route path="learning-hub" element={<LearningHub />} />
            <Route path="expense-tracker" element={<ExpenseTracker />} />
            <Route path="expenses" element={<ExpenseTracker />} />
            <Route path="expense" element={<ExpenseTracker />} />
            <Route path="upgrade" element={<Upgrade />} />
            <Route path="settings" element={<Settings />} />
            <Route path="profile" element={<Profile />} />
            {/* Safety catch-all: unknown /dashboard/* stays inside dashboard */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>

          {/* Catch-all Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </FlowContext.Provider>
    </UserProvider>
  );
}
