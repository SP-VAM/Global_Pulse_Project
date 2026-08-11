/**
 * Expense Tracker API Client
 */

function getAuthHeader() {
  const token = localStorage.getItem("access_token")
  return token ? { Authorization: `Bearer ${token}` } : {}
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

export async function getExpenseSummary(year, month) {
  const query = new URLSearchParams()
  if (year) query.append("year", year)
  if (month) query.append("month", month)

  const res = await fetch(`/api/v1/expenses/summary?${query.toString()}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  })
  return handleResponse(res, "Failed to fetch expense summary.")
}

export async function createExpense(payload) {
  const res = await fetch("/api/v1/expenses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse(res, "Failed to create expense.")
}

export async function updateExpense(expenseId, payload) {
  const res = await fetch(`/api/v1/expenses/${expenseId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse(res, "Failed to update expense.")
}

export async function deleteExpense(expenseId) {
  const res = await fetch(`/api/v1/expenses/${expenseId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeader(),
    },
  })
  return handleResponse(res, "Failed to delete expense.")
}

export async function createIncome(payload) {
  const res = await fetch("/api/v1/expenses/income", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse(res, "Failed to create income.")
}

export async function updateIncome(incomeId, payload) {
  const res = await fetch(`/api/v1/expenses/income/${incomeId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse(res, "Failed to update income.")
}

export async function deleteIncome(incomeId) {
  const res = await fetch(`/api/v1/expenses/income/${incomeId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeader(),
    },
  })
  return handleResponse(res, "Failed to delete income.")
}

export async function saveBudget(payload) {
  const res = await fetch("/api/v1/expenses/budgets", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse(res, "Failed to save budget.")
}

export async function deleteBudget(budgetId) {
  const res = await fetch(`/api/v1/expenses/budgets/${budgetId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeader(),
    },
  })
  return handleResponse(res, "Failed to delete budget.")
}
