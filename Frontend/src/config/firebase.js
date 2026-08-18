import { initializeApp } from "firebase/app";
import { getAuth, RecaptchaVerifier, signInWithPhoneNumber } from "firebase/auth";
import { API_BASE_URL } from "./api.js";

const firebaseConfig = {
  apiKey: "AIzaSyAl_ADzvszn-x0t0ZaxO89brx1Oo5IWRA0",
  authDomain: "globalpulse-c4870.firebaseapp.com",
  projectId: "globalpulse-c4870",
  storageBucket: "globalpulse-c4870.firebasestorage.app",
  messagingSenderId: "438768082415",
  appId: "1:438768082415:web:fb65572341c1d2f9adea1a",
  measurementId: "G-YVVXSLGSFF"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

/**
 * Cleanly clear and reset any active reCAPTCHA verifier instance.
 * Safe for component unmounts, navigation, and error retries.
 */
export const cleanupRecaptcha = () => {
  if (window.recaptchaVerifier) {
    try {
      window.recaptchaVerifier.clear();
    } catch (e) {
      console.warn("[Firebase Auth] Recaptcha clear warning:", e);
    }
    window.recaptchaVerifier = null;
  }
};

/**
 * Setup or reuse existing RecaptchaVerifier instance.
 * Prevents "reCAPTCHA has already been rendered in this element" errors by reusing active verifiers.
 */
export const setupRecaptcha = (containerId = "recaptcha-container") => {
  if (window.recaptchaVerifier) {
    return window.recaptchaVerifier;
  }

  const container = document.getElementById(containerId);
  if (!container) {
    throw new Error(`reCAPTCHA container with id '${containerId}' not found in DOM.`);
  }

  window.recaptchaVerifier = new RecaptchaVerifier(
    auth,
    containerId,
    {
      size: "invisible",
      callback: () => {
        console.log("[Firebase Auth] reCAPTCHA solved successfully.");
      },
      "expired-callback": () => {
        console.warn("[Firebase Auth] reCAPTCHA expired, resetting...");
        cleanupRecaptcha();
      },
    }
  );

  return window.recaptchaVerifier;
};

/**
 * Dispatch real Firebase SMS code using reusable RecaptchaVerifier.
 */
export const sendFirebasePhoneOTP = async (phoneNumber, containerId = "recaptcha-container") => {
  const recaptcha = setupRecaptcha(containerId);
  const formattedNumber = phoneNumber.startsWith("+") ? phoneNumber : `+91${phoneNumber.trim()}`;
  console.log(`[Firebase Phone Auth] Sending real SMS to ${formattedNumber}...`);
  try {
    const confirmationResult = await signInWithPhoneNumber(auth, formattedNumber, recaptcha);
    window.confirmationResult = confirmationResult;
    console.log(`[Firebase Phone Auth] Real SMS dispatched successfully to ${formattedNumber}`);
    return confirmationResult;
  } catch (error) {
    console.error(`[Firebase Phone Auth] Error sending SMS to ${formattedNumber}:`, error);
    cleanupRecaptcha();
    throw error;
  }
};

export const verifyFirebasePhoneOTP = async (otpCode) => {
  if (!window.confirmationResult) {
    throw new Error("No active OTP session found. Please request OTP again.");
  }
  const result = await window.confirmationResult.confirm(otpCode);
  const idToken = await result.user.getIdToken();
  return {
    user: result.user,
    idToken: idToken,
    verificationId: window.confirmationResult.verificationId || null,
  };
};

export const authenticateWithBackend = async (idToken, username = null) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/firebase-login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      id_token: idToken,
      username: username,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Backend Firebase authentication failed.");
  }

  return response.json();
};
