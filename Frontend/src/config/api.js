/**
 * Centralized API Base URL Configuration for GlobalPulse
 *
 * Supports Vite build-time environment variables (VITE_API_URL, VITE_API_BASE_URL)
 * with robust production fallback to Render backend and localhost fallback for dev.
 */

const getApiBaseUrl = () => {
  const envUrl = (typeof import.meta !== "undefined" && import.meta.env)
    ? (import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL)
    : (typeof process !== "undefined" && process.env ? (process.env.VITE_API_URL || process.env.VITE_API_BASE_URL) : "");

  if (envUrl && typeof envUrl === "string" && envUrl.trim() !== "") {
    return envUrl.trim().replace(/\/$/, "");
  }

  if (typeof window !== "undefined" && window.location.hostname.includes("onrender.com")) {
    return "https://globalpulse-backend-i6oa.onrender.com";
  }

  return "http://127.0.0.1:8000";
};

export const API_BASE_URL = getApiBaseUrl();
export const API_URL = API_BASE_URL;

export default API_BASE_URL;
