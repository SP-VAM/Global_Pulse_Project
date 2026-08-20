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
  location: { hostname: "localhost", pathname: "/dashboard/expense-tracker" },
};

// ---------------------------------------------------------------------------
// Pure logic extractor for Filters & Search (FRD-022)
// ---------------------------------------------------------------------------

function filterTransactions(transactions, criteria = {}) {
  if (!transactions || !Array.isArray(transactions)) return [];

  const {
    keyword = "",
    category = "all",
    transactionType = "all",
    dateFrom = null,
    dateTo = null,
    amountMin = null,
    amountMax = null,
  } = criteria;

  const normalizedKeyword = keyword.trim().toLowerCase();

  return transactions.filter((t) => {
    if (!t) return false;

    // 1. Transaction Type filter (all | expense | income)
    if (transactionType !== "all" && t.transaction_type !== transactionType && t.type !== transactionType) {
      return false;
    }

    // 2. Category filter (only applicable to expenses)
    if (category !== "all") {
      const tCat = (t.category || t.category_name || t.categoryName || "").toLowerCase();
      if (tCat !== category.toLowerCase()) return false;
    }

    // 3. Keyword search (searches notes, payment method, category, and amount string)
    if (normalizedKeyword) {
      const notes = (t.notes || "").toLowerCase();
      const method = (t.payment_method || t.paymentMethod || t.method || "").toLowerCase();
      const cat = (t.category || t.category_name || t.categoryName || "").toLowerCase();
      const amtStr = String(t.amount || "");

      const matches =
        notes.includes(normalizedKeyword) ||
        method.includes(normalizedKeyword) ||
        cat.includes(normalizedKeyword) ||
        amtStr.includes(normalizedKeyword);

      if (!matches) return false;
    }

    // 4. Amount Range filter (amountMin <= amount <= amountMax)
    const amount = Number(t.amount) || 0;
    if (amountMin !== null && amountMin !== undefined && amount < Number(amountMin)) {
      return false;
    }
    if (amountMax !== null && amountMax !== undefined && amount > Number(amountMax)) {
      return false;
    }

    // 5. Date Range filter (dateFrom <= transaction_date <= dateTo)
    const dateStr = t.transaction_date || t.expense_date || t.income_date || t.date;
    if (dateFrom && dateStr < dateFrom) return false;
    if (dateTo && dateStr > dateTo) return false;

    return true;
  }).sort((a, b) => {
    // 6. Strict chronological ordering (newest first / DESC)
    const dateA = a.transaction_date || a.expense_date || a.income_date || a.date || "";
    const dateB = b.transaction_date || b.expense_date || b.income_date || b.date || "";
    return dateB.localeCompare(dateA);
  });
}

function buildFilterQueryParams(filters) {
  const params = new URLSearchParams();
  if (filters.keyword) params.append("keyword", filters.keyword.trim());
  if (filters.categoryId && filters.categoryId !== "all") params.append("category_id", filters.categoryId);
  if (filters.transactionType && filters.transactionType !== "all") params.append("transaction_type", filters.transactionType);
  if (filters.dateFrom) params.append("date_from", filters.dateFrom);
  if (filters.dateTo) params.append("date_to", filters.dateTo);
  if (filters.amountMin !== null && filters.amountMin !== undefined) params.append("amount_min", filters.amountMin);
  if (filters.amountMax !== null && filters.amountMax !== undefined) params.append("amount_max", filters.amountMax);
  return params.toString();
}

// ---------------------------------------------------------------------------
// Unit Test Suite for FRD-022: Filters & Search
// ---------------------------------------------------------------------------

describe("FRD-022 Filters & Search - Unit Test Suite", () => {
  const mockTransactions = [
    { id: "exp_1", transaction_type: "expense", amount: 450, category: "food", payment_method: "UPI", notes: "Swiggy dinner", transaction_date: "2026-08-18" },
    { id: "exp_2", transaction_type: "expense", amount: 2500, category: "shopping", payment_method: "Credit Card", notes: "Amazon shoes", transaction_date: "2026-08-15" },
    { id: "exp_3", transaction_type: "expense", amount: 22000, category: "rent", payment_method: "Net Banking", notes: "August flat rent", transaction_date: "2026-08-01" },
    { id: "inc_1", transaction_type: "income", amount: 85000, category: "income", payment_method: "Bank Transfer", notes: "Monthly salary", transaction_date: "2026-08-01" },
    { id: "exp_4", transaction_type: "expense", amount: 1200, category: "transport", payment_method: "UPI", notes: "Uber to airport", transaction_date: "2026-08-10" },
    { id: "inc_2", transaction_type: "income", amount: 15000, category: "income", payment_method: "UPI", notes: "Freelance UI design project", transaction_date: "2026-08-12" },
  ];

  describe("AC-001 & AC-002: Keyword & Category Filtering", () => {
    test("filterTransactions by keyword searches notes and payment methods case-insensitively", () => {
      const swiggyRes = filterTransactions(mockTransactions, { keyword: "swiggy" });
      assert.strictEqual(swiggyRes.length, 1);
      assert.strictEqual(swiggyRes[0].id, "exp_1");

      const upiRes = filterTransactions(mockTransactions, { keyword: "upi" });
      assert.strictEqual(upiRes.length, 3); // Swiggy, Uber, Freelance
    });

    test("filterTransactions by category isolates selected expense category", () => {
      const rentRes = filterTransactions(mockTransactions, { category: "rent" });
      assert.strictEqual(rentRes.length, 1);
      assert.strictEqual(rentRes[0].amount, 22000);
      assert.strictEqual(rentRes[0].category, "rent");
    });
  });

  describe("AC-001 & AC-003: Transaction Type & Multi-Filter Combination (AND Logic)", () => {
    test("filterTransactions isolates income transactions only", () => {
      const incomeOnly = filterTransactions(mockTransactions, { transactionType: "income" });
      assert.strictEqual(incomeOnly.length, 2);
      assert.strictEqual(incomeOnly[0].id, "inc_2"); // Newer date first (2026-08-12)
      assert.strictEqual(incomeOnly[1].id, "inc_1"); // (2026-08-01)
    });

    test("filterTransactions applies combined multi-filter criteria simultaneously", () => {
      // Type = expense, keyword = "upi", amount <= 1000
      const combined = filterTransactions(mockTransactions, {
        transactionType: "expense",
        keyword: "upi",
        amountMax: 1000,
      });

      assert.strictEqual(combined.length, 1);
      assert.strictEqual(combined[0].id, "exp_1");
      assert.strictEqual(combined[0].amount, 450);
    });
  });

  describe("AC-001 & AC-009: Amount Range & Date Range Boundaries", () => {
    test("filterTransactions by amount range bounds (min and max)", () => {
      const midRange = filterTransactions(mockTransactions, {
        amountMin: 1000,
        amountMax: 5000,
      });

      assert.strictEqual(midRange.length, 2); // exp_2 (2500), exp_4 (1200)
    });

    test("filterTransactions by date range correctly bounds transaction dates", () => {
      const dateBounded = filterTransactions(mockTransactions, {
        dateFrom: "2026-08-10",
        dateTo: "2026-08-16",
      });

      assert.strictEqual(dateBounded.length, 3); // exp_2 (08-15), inc_2 (08-12), exp_4 (08-10)
    });
  });

  describe("AC-005 & AC-006: Reset Filters & Empty State", () => {
    test("Resetting filters returns full unfiltered dataset", () => {
      const resetRes = filterTransactions(mockTransactions, {});
      assert.strictEqual(resetRes.length, mockTransactions.length);
    });

    test("Non-matching criteria returns clean empty array without error", () => {
      const noMatch = filterTransactions(mockTransactions, { keyword: "NON_EXISTENT_TEXT" });
      assert.strictEqual(noMatch.length, 0);
    });
  });

  describe("AC-007: Strict Chronological Ordering (Newest First)", () => {
    test("Filtered transactions are strictly ordered by date descending", () => {
      const allSorted = filterTransactions(mockTransactions, {});
      for (let i = 0; i < allSorted.length - 1; i++) {
        assert.ok(allSorted[i].transaction_date >= allSorted[i + 1].transaction_date);
      }
    });
  });

  describe("AC-008 & AC-011: Query Parameter Serialization", () => {
    test("buildFilterQueryParams serializes all active query parameters correctly", () => {
      const queryStr = buildFilterQueryParams({
        keyword: "lunch",
        categoryId: 3,
        transactionType: "expense",
        dateFrom: "2026-08-01",
        dateTo: "2026-08-20",
        amountMin: 100,
        amountMax: 5000,
      });

      assert.ok(queryStr.includes("keyword=lunch"));
      assert.ok(queryStr.includes("category_id=3"));
      assert.ok(queryStr.includes("transaction_type=expense"));
      assert.ok(queryStr.includes("date_from=2026-08-01"));
      assert.ok(queryStr.includes("date_to=2026-08-20"));
      assert.ok(queryStr.includes("amount_min=100"));
      assert.ok(queryStr.includes("amount_max=5000"));
    });
  });
});
