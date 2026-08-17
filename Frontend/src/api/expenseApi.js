/**
 * Expense Tracker API Client
 */

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

const summaryCache = new Map();

export function invalidateExpenseCache() {
  summaryCache.clear();
}

export async function getExpenseSummary(year, month) {
  const cacheKey = `${year}_${month}`;
  if (summaryCache.has(cacheKey)) {
    // Return cached summary instantly in 0ms
    return summaryCache.get(cacheKey);
  }

  const query = new URLSearchParams();
  if (year) query.append("year", year);
  if (month) query.append("month", month);

  const res = await fetch(`/api/v1/expenses/summary?${query.toString()}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  });
  const data = await handleResponse(res, "Failed to fetch expense summary.");
  summaryCache.set(cacheKey, data);
  return data;
}

export async function createExpense(payload) {
  invalidateExpenseCache();
  const res = await fetch("/api/v1/expenses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(res, "Failed to create expense.");
}

export async function updateExpense(expenseId, payload) {
  invalidateExpenseCache();
  const res = await fetch(`/api/v1/expenses/${expenseId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(res, "Failed to update expense.");
}

export async function deleteExpense(expenseId) {
  invalidateExpenseCache();
  const res = await fetch(`/api/v1/expenses/${expenseId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeader(),
    },
  });
  return handleResponse(res, "Failed to delete expense.");
}

export async function createIncome(payload) {
  invalidateExpenseCache();
  const res = await fetch("/api/v1/expenses/income", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(res, "Failed to create income.");
}

export async function updateIncome(incomeId, payload) {
  invalidateExpenseCache();
  const res = await fetch(`/api/v1/expenses/income/${incomeId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(res, "Failed to update income.");
}

export async function deleteIncome(incomeId) {
  invalidateExpenseCache();
  const res = await fetch(`/api/v1/expenses/income/${incomeId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeader(),
    },
  });
  return handleResponse(res, "Failed to delete income.");
}

export async function saveBudget(payload) {
  invalidateExpenseCache();
  const res = await fetch("/api/v1/expenses/budgets", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(res, "Failed to save budget.");
}

export async function deleteBudget(budgetId) {
  invalidateExpenseCache();
  const res = await fetch(`/api/v1/expenses/budgets/${budgetId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeader(),
    },
  });
  return handleResponse(res, "Failed to delete budget.");
}

export async function getFilteredTransactions(params = {}) {
  const query = new URLSearchParams()
  if (params.year) query.append("year", params.year)
  if (params.month) query.append("month", params.month)
  if (params.keyword) query.append("keyword", params.keyword)
  if (params.categoryId) query.append("category_id", params.categoryId)
  if (params.transactionType) query.append("transaction_type", params.transactionType)
  if (params.dateFrom) query.append("date_from", params.dateFrom)
  if (params.dateTo) query.append("date_to", params.dateTo)
  if (params.amountMin !== undefined && params.amountMin !== "" && params.amountMin !== null) {
    query.append("amount_min", params.amountMin)
  }
  if (params.amountMax !== undefined && params.amountMax !== "" && params.amountMax !== null) {
    query.append("amount_max", params.amountMax)
  }

  const res = await fetch(`/api/v1/expenses/transactions?${query.toString()}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  })
  return handleResponse(res, "Failed to fetch transactions.")
}

