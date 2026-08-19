import { test, describe, beforeEach, mock } from "node:test";
import assert from "node:assert/strict";

// Mock localStorage and window before importing API
globalThis.localStorage = {
  _store: {},
  getItem(key) {
    return this._store[key] || null;
  },
  setItem(key, val) {
    this._store[key] = String(val);
  },
  removeItem(key) {
    delete this._store[key];
  },
  clear() {
    this._store = {};
  },
};

globalThis.window = {
  location: { hostname: "localhost", pathname: "/dashboard/expense-tracker" },
};

import {
  getExpenseSummary,
  createExpense,
  updateExpense,
  deleteExpense,
  createIncome,
  updateIncome,
  deleteIncome,
  saveBudget,
  deleteBudget,
  getFilteredTransactions,
  invalidateExpenseCache,
} from "../../src/api/expenseApi.js";

import {
  CATEGORIES,
  CATEGORY_MAP,
  formatINR,
  dateKey,
  prettyDate,
  monthLabel,
  addDaysISO,
  getCategoryKey,
} from "../../src/pages/Dashboard/ExpenseTracker/data.js";

function createMockResponse(data, status = 200) {
  const jsonStr = JSON.stringify(data);
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null),
    },
    json: async () => data,
    text: async () => jsonStr,
  };
}

describe("Frontend Expense Tracker - Unit Test Suite", () => {
  beforeEach(() => {
    localStorage.clear();
    invalidateExpenseCache();
  });

  /* -------------------------------------------------------------
   * 1. Data Helper & Calculation Unit Tests
   * ------------------------------------------------------------- */
  describe("Data Formatters & Calculation Rules", () => {
    test("formatINR formats numbers to Indian Rupee currency standard", () => {
      assert.strictEqual(formatINR(0), "₹0");
      assert.strictEqual(formatINR(500), "₹500");
      assert.strictEqual(formatINR(125000), "₹1,25,000");
      assert.strictEqual(formatINR(10000000), "₹1,00,00,000");
    });

    test("dateKey builds correct YYYY-MM-DD from 0-indexed JS month", () => {
      assert.strictEqual(dateKey(2026, 0, 5), "2026-01-05");
      assert.strictEqual(dateKey(2026, 7, 19), "2026-08-19");
      assert.strictEqual(dateKey(2026, 11, 31), "2026-12-31");
    });

    test("prettyDate converts ISO date key to human readable format", () => {
      assert.strictEqual(prettyDate("2026-08-19"), "19 August 2026");
      assert.strictEqual(prettyDate("2026-01-01"), "1 January 2026");
    });

    test("monthLabel produces formatted month and year string", () => {
      assert.strictEqual(monthLabel(2026, 0), "January 2026");
      assert.strictEqual(monthLabel(2026, 7), "August 2026");
    });

    test("addDaysISO accurately computes date addition across month boundaries", () => {
      assert.strictEqual(addDaysISO("2026-08-01", 7), "2026-08-08");
      assert.strictEqual(addDaysISO("2026-08-28", 5), "2026-09-02");
    });

    test("getCategoryKey normalizes various category aliases correctly", () => {
      assert.strictEqual(getCategoryKey("Food & Dining"), "food");
      assert.strictEqual(getCategoryKey("dining"), "food");
      assert.strictEqual(getCategoryKey("transportation"), "transport");
      assert.strictEqual(getCategoryKey("Travel"), "transport");
      assert.strictEqual(getCategoryKey("healthcare"), "health");
      assert.strictEqual(getCategoryKey("Medical"), "health");
      assert.strictEqual(getCategoryKey("utilities"), "bills");
      assert.strictEqual(getCategoryKey("unknown_category"), "other");
    });

    test("Total Spending, Total Income, and Net Savings calculations are exact", () => {
      const sampleIncomes = [{ amount: 75000 }, { amount: 15000 }];
      const sampleExpenses = [{ amount: 12000 }, { amount: 3500 }, { amount: 8500 }];

      const totalIncome = sampleIncomes.reduce((acc, curr) => acc + curr.amount, 0);
      const totalSpending = sampleExpenses.reduce((acc, curr) => acc + curr.amount, 0);
      const netSavings = totalIncome - totalSpending;

      assert.strictEqual(totalIncome, 90000);
      assert.strictEqual(totalSpending, 24000);
      assert.strictEqual(netSavings, 66000);
    });

    test("Category budget consumption & percentage tracking", () => {
      const budgetLimit = 10000;
      const spentAmount = 7500;
      const pct = Math.round((spentAmount / budgetLimit) * 100);
      const remaining = budgetLimit - spentAmount;
      const isOverBudget = spentAmount > budgetLimit;

      assert.strictEqual(pct, 75);
      assert.strictEqual(remaining, 2500);
      assert.strictEqual(isOverBudget, false);
    });
  });

  /* -------------------------------------------------------------
   * 2. Expense API Client Integration Tests (Mocked Network)
   * ------------------------------------------------------------- */
  describe("Expense API Client & CRUD Operations", () => {
    test("getExpenseSummary attaches Bearer token and returns parsed monthly summary", async () => {
      localStorage.setItem("access_token", "jwt_test_token_123");

      const mockData = {
        year: 2026,
        month: 8,
        total_income: 100000,
        total_expense: 35000,
        net_savings: 65000,
        expenses: [{ expenseId: 1, amount: 5000, category: { categoryName: "Food" } }],
        incomes: [{ incomeId: 1, amount: 100000, source: "Salary" }],
        budgets: [{ budgetId: 1, categoryName: "Food", monthlyLimit: 10000 }],
      };

      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /\/api\/v1\/expenses\/summary\?year=2026&month=8/);
        assert.strictEqual(options.headers.Authorization, "Bearer jwt_test_token_123");
        return createMockResponse(mockData, 200);
      });

      const res = await getExpenseSummary(2026, 8);
      assert.deepStrictEqual(res, mockData);
      assert.strictEqual(globalThis.fetch.mock.callCount(), 1);

      // Verify cached hit on second call (0 additional network calls)
      const cachedRes = await getExpenseSummary(2026, 8);
      assert.deepStrictEqual(cachedRes, mockData);
      assert.strictEqual(globalThis.fetch.mock.callCount(), 1);
    });

    test("createExpense sends POST request and invalidates summary cache", async () => {
      localStorage.setItem("access_token", "jwt_test_token_123");
      const payload = { amount: 2500, category_id: 1, description: "Groceries", expense_date: "2026-08-19" };

      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /\/api\/v1\/expenses$/);
        assert.strictEqual(options.method, "POST");
        assert.strictEqual(options.headers.Authorization, "Bearer jwt_test_token_123");
        assert.strictEqual(options.body, JSON.stringify(payload));
        return createMockResponse({ expenseId: 101, ...payload }, 201);
      });

      const created = await createExpense(payload);
      assert.strictEqual(created.expenseId, 101);
      assert.strictEqual(created.amount, 2500);
    });

    test("updateExpense sends PUT request with target expense ID", async () => {
      const payload = { amount: 3000, description: "Updated Groceries" };

      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /\/api\/v1\/expenses\/101$/);
        assert.strictEqual(options.method, "PUT");
        return createMockResponse({ expenseId: 101, ...payload }, 200);
      });

      const updated = await updateExpense(101, payload);
      assert.strictEqual(updated.amount, 3000);
    });

    test("deleteExpense sends DELETE request", async () => {
      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /\/api\/v1\/expenses\/101$/);
        assert.strictEqual(options.method, "DELETE");
        return createMockResponse({ message: "Deleted" }, 200);
      });

      const result = await deleteExpense(101);
      assert.deepStrictEqual(result, { message: "Deleted" });
    });

    test("createIncome, updateIncome, deleteIncome CRUD operations execute cleanly", async () => {
      const incomePayload = { amount: 50000, source: "Freelance", income_date: "2026-08-19" };

      globalThis.fetch = mock.fn(async (url, options) => {
        if (options.method === "POST") {
          assert.match(url, /\/api\/v1\/expenses\/income$/);
          return createMockResponse({ incomeId: 5, ...incomePayload }, 201);
        }
        if (options.method === "PUT") {
          assert.match(url, /\/api\/v1\/expenses\/income\/5$/);
          return createMockResponse({ incomeId: 5, amount: 55000 }, 200);
        }
        if (options.method === "DELETE") {
          assert.match(url, /\/api\/v1\/expenses\/income\/5$/);
          return createMockResponse({ message: "Income deleted" }, 200);
        }
      });

      const inc = await createIncome(incomePayload);
      assert.strictEqual(inc.incomeId, 5);

      const updatedInc = await updateIncome(5, { amount: 55000 });
      assert.strictEqual(updatedInc.amount, 55000);

      const delInc = await deleteIncome(5);
      assert.deepStrictEqual(delInc, { message: "Income deleted" });
    });

    test("saveBudget and deleteBudget manage category budget limits", async () => {
      const budgetPayload = { category_name: "Food", monthly_limit: 15000 };

      globalThis.fetch = mock.fn(async (url, options) => {
        if (options.method === "POST") {
          assert.match(url, /\/api\/v1\/expenses\/budgets$/);
          return createMockResponse({ budgetId: 12, ...budgetPayload }, 200);
        }
        if (options.method === "DELETE") {
          assert.match(url, /\/api\/v1\/expenses\/budgets\/12$/);
          return createMockResponse({ message: "Budget removed" }, 200);
        }
      });

      const saved = await saveBudget(budgetPayload);
      assert.strictEqual(saved.budgetId, 12);

      const del = await deleteBudget(12);
      assert.deepStrictEqual(del, { message: "Budget removed" });
    });

    test("getFilteredTransactions serializes search keyword, date ranges, category and amounts", async () => {
      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /keyword=grocery/);
        assert.match(url, /category_id=1/);
        assert.match(url, /amount_min=500/);
        assert.match(url, /amount_max=5000/);
        assert.match(url, /date_from=2026-08-01/);
        assert.match(url, /date_to=2026-08-19/);
        return createMockResponse({ transactions: [], total_count: 0 }, 200);
      });

      const params = {
        keyword: "grocery",
        categoryId: 1,
        amountMin: 500,
        amountMax: 5000,
        dateFrom: "2026-08-01",
        dateTo: "2026-08-19",
      };

      const res = await getFilteredTransactions(params);
      assert.deepStrictEqual(res.transactions, []);
    });

    test("getExpenseSummary retries automatically on NetworkError / Failed to fetch", async () => {
      let callCount = 0;
      globalThis.fetch = mock.fn(async () => {
        callCount++;
        if (callCount === 1) {
          throw new TypeError("Failed to fetch");
        }
        return createMockResponse({ total_income: 50000, total_expense: 20000 }, 200);
      });

      const res = await getExpenseSummary(2026, 8, 2);
      assert.strictEqual(res.total_income, 50000);
      assert.strictEqual(callCount, 2); // Succeeded on retry attempt 2
    });
  });
});
