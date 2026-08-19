/**
 * Portfolio Management API Client
 */

import { API_BASE_URL } from "../config/api.js";

function getAuthHeader() {
  const token = localStorage.getItem("access_token")
  return (token && token !== "demo_token") ? { Authorization: `Bearer ${token}` } : {}
}

async function handleResponse(res, fallbackErrorMsg) {
  if (res.status === 401) {
    localStorage.removeItem("access_token")
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login"
    }
    throw new Error("Session expired. Please log in again.")
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error?.message || err.detail || fallbackErrorMsg)
  }
  return await res.json()
}

export async function getPortfolioSummary() {
  const res = await fetch(`${API_BASE_URL}/api/v1/portfolio/summary`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  })
  return handleResponse(res, "Failed to fetch portfolio summary.")
}

export async function addInvestment(payload) {
  const res = await fetch(`${API_BASE_URL}/api/v1/portfolio`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse(res, "Failed to add investment.")
}

export async function updateInvestment(investmentId, payload) {
  const res = await fetch(`${API_BASE_URL}/api/v1/portfolio/${investmentId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse(res, "Failed to update investment.")
}

export async function deleteInvestment(investmentId) {
  const res = await fetch(`${API_BASE_URL}/api/v1/portfolio/${investmentId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeader(),
    },
  })
  return handleResponse(res, "Failed to delete investment.")
}

