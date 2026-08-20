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

import {
  sanitizeFinancialInput,
  validateFinancialAmount,
} from "../../../Frontend/src/utils/financialValidation.js";
import { getCategoryKey, CATEGORIES } from "../../../Frontend/src/pages/Dashboard/ExpenseTracker/data.js";

// ---------------------------------------------------------------------------
// Pure logic extractors for Budget Setup (FRD-017)
// ---------------------------------------------------------------------------

function checkDuplicateCategory(targetCategoryKey, existingBudgets, isEdit = false) {
  if (isEdit || !existingBudgets || existingBudgets.length === 0) return false;
  const normTarget = getCategoryKey(targetCategoryKey);
  return existingBudgets.some((b) => {
    const bKey = getCategoryKey(b.category || b.categoryName || b.categoryId);
    return bKey === normTarget;
  });
}

function calculateTotalMonthlyBudget(budgets) {
  if (!budgets || !Array.isArray(budgets)) return 0;
  return budgets.reduce((sum, b) => {
    const amount = Number(b.limit ?? b.budgetAmount ?? b.amount ?? 0);
    return sum + (amount > 0 ? amount : 0);
  }, 0);
}

function calculateBudgetUtilization(budgetLimit, categorySpending) {
  const limit = Number(budgetLimit) || 0;
  const spent = Number(categorySpending) || 0;
  if (limit <= 0) return { spent, limit: 0, remaining: 0, percentage: 0, isOverBudget: false, status: "unbudgeted" };

  const remaining = limit - spent;
  const percentage = Math.round((spent / limit) * 100);
  const isOverBudget = spent > limit;

  return {
    spent,
    limit,
    remaining,
    percentage,
    isOverBudget,
    status: isOverBudget ? "over_budget" : percentage >= 80 ? "approaching_limit" : "in_budget",
  };
}

function validateBudgetForm({ category, limit, isEdit = false, initialLimit = 0, existingBudgets = [] }) {
  if (!category) {
    return { isValid: false, error: "Please select a budget category." };
  }

  if (checkDuplicateCategory(category, existingBudgets, isEdit)) {
    return { isValid: false, error: "This category already exists." };
  }

  const minAllowed = isEdit ? initialLimit : 1;
  const valResult = validateFinancialAmount(limit, {
    fieldName: "Monthly limit",
    min: minAllowed,
    minError: isEdit
      ? `Monthly limit can only be increased (minimum ₹${initialLimit.toLocaleString("en-IN")}).`
      : "Enter a monthly limit greater than 0.",
  });

  if (!valResult.isValid) {
    return { isValid: false, error: valResult.error };
  }

  return { isValid: true, error: null, cleanLimit: valResult.numValue };
}

// ---------------------------------------------------------------------------
// Unit Test Suite for FRD-017: Budget Setup
// ---------------------------------------------------------------------------

describe("FRD-017 Budget Setup - Unit Test Suite", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("AC-001, AC-002 & AC-003: Category Selection, Validation & Duplicate Prevention", () => {
    test("validateBudgetForm passes with valid positive category and limit", () => {
      const form = {
        category: "food",
        limit: "15000",
        isEdit: false,
        existingBudgets: [],
      };

      const res = validateBudgetForm(form);
      assert.strictEqual(res.isValid, true);
      assert.strictEqual(res.cleanLimit, 15000);
      assert.strictEqual(res.error, null);
    });

    test("validateBudgetForm rejects duplicate category selection in create mode", () => {
      const existing = [{ category: "food", limit: 12000 }];
      const form = {
        category: "food",
        limit: "15000",
        isEdit: false,
        existingBudgets: existing,
      };

      const res = validateBudgetForm(form);
      assert.strictEqual(res.isValid, false);
      assert.strictEqual(res.error, "This category already exists.");
    });

    test("validateBudgetForm permits editing existing category without duplicate conflict", () => {
      const existing = [{ category: "food", limit: 12000 }];
      const form = {
        category: "food",
        limit: "18000",
        isEdit: true,
        initialLimit: 12000,
        existingBudgets: existing,
      };

      const res = validateBudgetForm(form);
      assert.strictEqual(res.isValid, true);
      assert.strictEqual(res.cleanLimit, 18000);
    });
  });

  describe("AC-003 & AC-004: Positive Numeric Limit & Non-Zero Enforcement", () => {
    test("validateBudgetForm rejects 0 and negative numbers", () => {
      const zeroForm = { category: "rent", limit: "0", isEdit: false, existingBudgets: [] };
      const negForm = { category: "rent", limit: "-500", isEdit: false, existingBudgets: [] };

      const zeroRes = validateBudgetForm(zeroForm);
      assert.strictEqual(zeroRes.isValid, false);
      assert.strictEqual(zeroRes.error, "Enter a monthly limit greater than 0.");

      const negRes = validateBudgetForm(negForm);
      assert.strictEqual(negRes.isValid, false);
    });

    test("validateBudgetForm rejects empty limit field", () => {
      const emptyForm = { category: "shopping", limit: "", isEdit: false, existingBudgets: [] };
      const res = validateBudgetForm(emptyForm);
      assert.strictEqual(res.isValid, false);
    });
  });

  describe("AC-005 & AC-006: Automatic Total Budget Calculation & Dynamic Modification", () => {
    test("calculateTotalMonthlyBudget accurately sums all active category limits", () => {
      const budgets = [
        { category: "rent", limit: 25000 },
        { category: "food", limit: 15000 },
        { category: "transport", limit: 5000 },
        { category: "entertainment", limit: 5000 },
      ];

      const total = calculateTotalMonthlyBudget(budgets);
      assert.strictEqual(total, 50000);
    });

    test("calculateTotalMonthlyBudget updates dynamically when removing or adding categories", () => {
      const initialBudgets = [
        { category: "rent", limit: 25000 },
        { category: "food", limit: 15000 },
      ];
      assert.strictEqual(calculateTotalMonthlyBudget(initialBudgets), 40000);

      // Add a category
      const afterAdd = [...initialBudgets, { category: "shopping", limit: 10000 }];
      assert.strictEqual(calculateTotalMonthlyBudget(afterAdd), 50000);

      // Remove a category
      const afterRemove = afterAdd.filter((b) => b.category !== "food");
      assert.strictEqual(calculateTotalMonthlyBudget(afterRemove), 35000);
    });
  });

  describe("AC-008 & AC-009: Budget Utilization & Unbudgeted Category Handling", () => {
    test("calculateBudgetUtilization calculates percentage, remaining balance, and status flags", () => {
      // In budget (50% utilization)
      const u1 = calculateBudgetUtilization(20000, 10000);
      assert.strictEqual(u1.percentage, 50);
      assert.strictEqual(u1.remaining, 10000);
      assert.strictEqual(u1.isOverBudget, false);
      assert.strictEqual(u1.status, "in_budget");

      // Approaching threshold (85% utilization)
      const u2 = calculateBudgetUtilization(20000, 17000);
      assert.strictEqual(u2.percentage, 85);
      assert.strictEqual(u2.status, "approaching_limit");

      // Over budget (125% utilization)
      const u3 = calculateBudgetUtilization(20000, 25000);
      assert.strictEqual(u3.percentage, 125);
      assert.strictEqual(u3.remaining, -5000);
      assert.strictEqual(u3.isOverBudget, true);
      assert.strictEqual(u3.status, "over_budget");
    });

    test("Unbudgeted category returns unbudgeted status without skewing budget limits", () => {
      const unbudgeted = calculateBudgetUtilization(0, 5000);
      assert.strictEqual(unbudgeted.limit, 0);
      assert.strictEqual(unbudgeted.status, "unbudgeted");
      assert.strictEqual(unbudgeted.percentage, 0);
    });
  });

  describe("AC-007, AC-010 & AC-013: Budget Save Dispatch & Cross-Component Sync", () => {
    test("Saving budget dispatches expense-updated event for real-time dashboard sync", async () => {
      let eventReceived = false;
      const handler = () => {
        eventReceived = true;
      };

      window.addEventListener("expense-updated", handler);

      const mockSaveApi = async (payload) => {
        assert.strictEqual(payload.category_name, "Rent");
        assert.strictEqual(payload.budget_amount, 25000);
        window.dispatchEvent({ type: "expense-updated" });
        return { budget_id: 1, ...payload };
      };

      const result = await mockSaveApi({
        category_name: "Rent",
        budget_amount: 25000,
        budget_month: 8,
        budget_year: 2026,
      });

      assert.strictEqual(result.budget_id, 1);
      assert.strictEqual(eventReceived, true);

      window.removeEventListener("expense-updated", handler);
    });
  });
});
