/**
 * API client service for Financial Goals (FRD-041).
 * Communicates with backend endpoints (/api/v1/goals).
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (window.location.hostname === "localhost" ? "http://localhost:8000" : "");

function getAuthHeader() {
  const token = localStorage.getItem("token") || localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchGoals() {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  };
  const res = await fetch(`${API_BASE_URL}/api/v1/goals`, { headers });
  if (!res.ok) {
    throw new Error(`Failed to fetch goals: ${res.statusText}`);
  }
  return res.json();
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
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create goal: ${res.statusText}`);
  }
  return res.json();
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
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update goal: ${res.statusText}`);
  }
  return res.json();
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
  if (!res.ok && res.status !== 204) {
    throw new Error(`Failed to delete goal: ${res.statusText}`);
  }
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
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to record goal progress: ${res.statusText}`);
  }
  return res.json();
}
