/**
 * API client service for Financial Goals (FRD-041).
 * Communicates with backend endpoints (/api/v1/goals).
 */
import { API_BASE_URL } from "../config/api.js";

function getAuthHeader() {
  const token = localStorage.getItem("access_token") || localStorage.getItem("token");
  return (token && token !== "demo_token") ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse(res, fallbackErrorMsg) {
  if (res.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("token");
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    let err = {};
    if (ct.includes("application/json")) {
      err = await res.json().catch(() => ({}));
    } else {
      const txt = await res.text().catch(() => "");
      try {
        err = txt ? JSON.parse(txt) : {};
      } catch {
        err = { detail: txt };
      }
    }
    throw new Error(err.detail || err.error?.message || fallbackErrorMsg);
  }

  if (res.status === 204) return null;
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  if (!ct.includes("application/json")) return null;

  const text = await res.text().catch(() => "");
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export async function fetchGoals() {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  };
  const res = await fetch(`${API_BASE_URL}/api/v1/goals`, { headers });
  return handleResponse(res, "Failed to fetch goals.");
}

export async function createGoalApi(goalData) {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  };
  const res = await fetch(`${API_BASE_URL}/api/v1/goals`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      goal_name: goalData.name,
      target_quantity: Number(goalData.target),
      unit: goalData.unit || "INR",
      start_date: goalData.startDate || null,
      end_date: goalData.endDate,
      notes: goalData.note || null,
      investment_name: goalData.assetType || "Savings",
    }),
  });
  return handleResponse(res, "Failed to create goal.");
}

export async function updateGoalApi(goalId, fields) {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  };
  const payload = {};
  if (fields.name !== undefined) payload.goal_name = fields.name;
  if (fields.target !== undefined) payload.target_quantity = Number(fields.target);
  if (fields.note !== undefined) payload.notes = fields.note;
  if (fields.endDate !== undefined) payload.end_date = fields.endDate;
  if (fields.unit !== undefined) payload.unit = fields.unit;

  const res = await fetch(`${API_BASE_URL}/api/v1/goals/${goalId}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(payload),
  });
  return handleResponse(res, "Failed to update goal.");
}

export async function deleteGoalApi(goalId) {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  };
  const res = await fetch(`${API_BASE_URL}/api/v1/goals/${goalId}`, {
    method: "DELETE",
    headers,
  });
  await handleResponse(res, "Failed to delete goal.");
  return true;
}

export async function addGoalProgressApi(goalId, { amount, assetType, date, remarks }) {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  };
  const res = await fetch(`${API_BASE_URL}/api/v1/goals/${goalId}/progress`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      quantity_added: Number(amount),
      progress_date: date || null,
      remarks: remarks || `Added ${assetType || "deposit"}`,
      asset_type: assetType || "Gold",
    }),
  });
  return handleResponse(res, "Failed to record goal progress.");
}
