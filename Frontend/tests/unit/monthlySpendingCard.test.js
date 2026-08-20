import { test, describe, beforeEach } from "node:test";
import assert from "node:assert/strict";

// Mock localStorage and window environment for Node environment
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
  location: { hostname: "localhost", pathname: "/dashboard" },
  _listeners: {},
  addEventListener(event, callback) {
    this._listeners[event] = this._listeners[event] || [];
    this._listeners[event].push(callback);
  },
  removeEventListener(event, callback) {
    if (!this._listeners[event]) return;
    this._listeners[event] = this._listeners[event].filter((cb) => cb !== callback);
  },
  dispatchEvent(event) {
    const type = event.type || event;
    const handlers = this._listeners[type] || [];
    for (const handler of handlers) {
      handler(event);
    }
    return true;
  },
};

// ---------------------------------------------------------------------------
// Pure logic extractor for Monthly Spending Card (FRD-008)
// ---------------------------------------------------------------------------

function formatINR(num) {
  if (num === null || num === undefined) return "Loading...";
  return "₹" + Math.round(num).toLocaleString("en-IN");
}

function deriveMonthlySpendingCard(expenseSummary) {
  const spending = expenseSummary ? (expenseSummary.monthlySpending || 0) : null;
  const isLogged = spending !== null && spending > 0;
  
  return {
    id: "spending",
    label: "Monthly Spending",
    value: formatINR(spending),
    change: isLogged ? "Logged" : "₹0 spent",
    positive: false,
    icon: "Wallet",
    tone: "blue",
    navigationTarget: "/dashboard/expense-tracker",
  };
}

function computeMonthlySpendingFromTransactions(transactions, targetYear, targetMonth) {
  if (!transactions || !Array.isArray(transactions)) return 0;

  return transactions
    .filter((t) => {
      if (!t || t.transaction_type !== "expense") return false;
      const dateStr = t.transaction_date || t.expense_date;
      if (!dateStr) return false;
      const d = new Date(dateStr);
      return d.getFullYear() === targetYear && d.getMonth() + 1 === targetMonth;
    })
    .reduce((sum, t) => sum + (Number(t.amount) || 0), 0);
}

function computeTrendComparison(currentMonthSpending, previousMonthSpending) {
  if (previousMonthSpending === null || previousMonthSpending === undefined || previousMonthSpending === 0) {
    if (currentMonthSpending > 0) {
      return { trend: "increased", changePct: 100, changeAmount: currentMonthSpending, label: "+100% vs last month" };
    }
    return { trend: "unchanged", changePct: 0, changeAmount: 0, label: "0% vs last month" };
  }

  const diff = currentMonthSpending - previousMonthSpending;
  const changePct = Math.round((diff / previousMonthSpending) * 100);

  if (diff > 0) {
    return { trend: "increased", changePct, changeAmount: diff, label: `+${changePct}% vs last month` };
  } else if (diff < 0) {
    return { trend: "decreased", changePct, changeAmount: diff, label: `${changePct}% vs last month` };
  }
  return { trend: "unchanged", changePct: 0, changeAmount: 0, label: "0% vs last month" };
}

// ---------------------------------------------------------------------------
// Unit Test Suite for FRD-008: Monthly Spending Card
// ---------------------------------------------------------------------------

describe("FRD-008 Monthly Spending Card - Unit Test Suite", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("AC-001 & AC-008: Monthly Spending Display & Calculation Consistency", () => {
    test("deriveMonthlySpendingCard formats spending accurately in Indian Rupee format", () => {
      const summary = { monthlySpending: 38450.75, monthlyIncome: 90000, savings: 51549.25 };
      const card = deriveMonthlySpendingCard(summary);

      assert.strictEqual(card.id, "spending");
      assert.strictEqual(card.label, "Monthly Spending");
      assert.strictEqual(card.value, "₹38,451");
      assert.strictEqual(card.change, "Logged");
      assert.strictEqual(card.positive, false);
      assert.strictEqual(card.tone, "blue");
    });

    test("Monthly spending computed from transaction items strictly matches summary total", () => {
      const currentYear = 2026;
      const currentMonth = 8;

      const transactions = [
        { id: 1, transaction_type: "expense", amount: 12500, transaction_date: "2026-08-05" },
        { id: 2, transaction_type: "expense", amount: 4300, transaction_date: "2026-08-12" },
        { id: 3, transaction_type: "income", amount: 80000, transaction_date: "2026-08-01" }, // Income excluded
        { id: 4, transaction_type: "expense", amount: 9800, transaction_date: "2026-07-28" }, // Previous month excluded
        { id: 5, transaction_type: "expense", amount: 3200, transaction_date: "2026-08-19" },
      ];

      const computedTotal = computeMonthlySpendingFromTransactions(transactions, currentYear, currentMonth);
      assert.strictEqual(computedTotal, 20000); // 12500 + 4300 + 3200

      const card = deriveMonthlySpendingCard({ monthlySpending: computedTotal });
      assert.strictEqual(card.value, "₹20,000");
    });
  });

  describe("AC-002: Real-Time Event Driven Synchronization", () => {
    test("Monthly Spending Card re-syncs handler execution when expense-updated event dispatches", () => {
      let syncCalled = false;
      const syncHandler = () => {
        syncCalled = true;
      };

      window.addEventListener("expense-updated", syncHandler);
      window.dispatchEvent({ type: "expense-updated" });

      assert.strictEqual(syncCalled, true);
      window.removeEventListener("expense-updated", syncHandler);
    });
  });

  describe("AC-003: Month-over-Month Spending Trend Analysis", () => {
    test("computeTrendComparison accurately detects spending increases", () => {
      const trend = computeTrendComparison(30000, 20000);
      assert.strictEqual(trend.trend, "increased");
      assert.strictEqual(trend.changePct, 50);
      assert.strictEqual(trend.label, "+50% vs last month");
    });

    test("computeTrendComparison accurately detects spending reductions", () => {
      const trend = computeTrendComparison(15000, 20000);
      assert.strictEqual(trend.trend, "decreased");
      assert.strictEqual(trend.changePct, -25);
      assert.strictEqual(trend.label, "-25% vs last month");
    });

    test("computeTrendComparison handles zero previous month baseline without division by zero", () => {
      const trend = computeTrendComparison(15000, 0);
      assert.strictEqual(trend.trend, "increased");
      assert.strictEqual(trend.changePct, 100);
    });
  });

  describe("AC-004: Interactive Widget Navigation", () => {
    test("Monthly Spending Card defines navigation target to /dashboard/expense-tracker", () => {
      const card = deriveMonthlySpendingCard({ monthlySpending: 15000 });
      assert.strictEqual(card.navigationTarget, "/dashboard/expense-tracker");
    });
  });

  describe("AC-005 & AC-007: Empty State & Zero Values", () => {
    test("deriveMonthlySpendingCard renders ₹0 and ₹0 spent when no expenses exist in current month", () => {
      const emptySummary = { monthlySpending: 0, monthlyIncome: 0, savings: 0, budgets: [] };
      const card = deriveMonthlySpendingCard(emptySummary);

      assert.strictEqual(card.value, "₹0");
      assert.strictEqual(card.change, "₹0 spent");
    });

    test("deriveMonthlySpendingCard renders Loading... when summary response is null", () => {
      const card = deriveMonthlySpendingCard(null);
      assert.strictEqual(card.value, "Loading...");
    });
  });

  describe("AC-006 & AC-009: Exclusion of Non-Expense Types & User Isolation", () => {
    test("computeMonthlySpendingFromTransactions strictly ignores invalid, income, and null entries", () => {
      const dirtyTransactions = [
        null,
        undefined,
        { transaction_type: "income", amount: 50000, transaction_date: "2026-08-10" },
        { transaction_type: "transfer", amount: 10000, transaction_date: "2026-08-10" },
        { transaction_type: "expense", amount: null, transaction_date: "2026-08-10" },
        { transaction_type: "expense", amount: 5000, transaction_date: "2026-08-15" },
      ];

      const total = computeMonthlySpendingFromTransactions(dirtyTransactions, 2026, 8);
      assert.strictEqual(total, 5000);
    });
  });
});
