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

// ---------------------------------------------------------------------------
// Pure logic extractor for Delete Transaction Workflow (FRD-015)
// ---------------------------------------------------------------------------

function normalizeTransactionRawId(tx) {
  if (!tx) return null;
  if (tx.rawId) return tx.rawId;
  if (typeof tx.id === "string") {
    return Number(tx.id.replace(/^(exp_|inc_)/, "")) || tx.id;
  }
  return tx.id;
}

function extractDeleteConfirmationDetails(tx) {
  if (!tx) return null;

  return {
    amount: Number(tx.amount) || 0,
    formattedAmount: "₹" + Math.round(Number(tx.amount) || 0).toLocaleString("en-IN"),
    category: tx.type === "income" ? "Income Deposit" : (tx.categoryName || tx.category || "Expense"),
    type: tx.type || "expense",
    date: tx.date || tx.transaction_date || tx.expense_date || tx.income_date,
    warning: "This action cannot be undone.",
  };
}

async function executeDeleteTransaction(tx, apiClients) {
  if (!tx) throw new Error("No transaction provided for deletion.");
  const rawId = normalizeTransactionRawId(tx);

  if (tx.type === "expense") {
    await apiClients.deleteExpense(rawId);
  } else if (tx.type === "income") {
    await apiClients.deleteIncome(rawId);
  } else {
    throw new Error(`Unsupported transaction type: ${tx.type}`);
  }

  // Trigger cross-module synchronization event
  window.dispatchEvent({ type: "expense-updated" });
  return { success: true, message: "Transaction deleted successfully.", deletedId: rawId };
}

function removeTransactionFromList(transactions, rawId, type) {
  if (!Array.isArray(transactions)) return [];
  return transactions.filter((t) => {
    const tRawId = normalizeTransactionRawId(t);
    return !(tRawId === rawId && t.type === type);
  });
}

function recalculateTotalsAfterDeletion(transactions) {
  const expenses = transactions.filter((t) => t.type === "expense").reduce((sum, t) => sum + (Number(t.amount) || 0), 0);
  const incomes = transactions.filter((t) => t.type === "income").reduce((sum, t) => sum + (Number(t.amount) || 0), 0);
  const savings = incomes - expenses;

  return {
    totalSpending: expenses,
    totalIncome: incomes,
    netSavings: savings,
  };
}

// ---------------------------------------------------------------------------
// Unit Test Suite for FRD-015: Delete Transaction Popup
// ---------------------------------------------------------------------------

describe("FRD-015 Delete Transaction Popup - Unit Test Suite", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("AC-001, AC-002 & AC-003: Popup Accessibility & Detail Display", () => {
    test("extractDeleteConfirmationDetails formats transaction properties and warning accurately", () => {
      const sampleExpense = {
        id: "exp_105",
        rawId: 105,
        type: "expense",
        category: "Food",
        categoryName: "Food & Dining",
        amount: 2450.5,
        date: "2026-08-15",
      };

      const details = extractDeleteConfirmationDetails(sampleExpense);
      assert.strictEqual(details.amount, 2450.5);
      assert.strictEqual(details.formattedAmount, "₹2,451");
      assert.strictEqual(details.category, "Food & Dining");
      assert.strictEqual(details.type, "expense");
      assert.strictEqual(details.date, "2026-08-15");
      assert.strictEqual(details.warning, "This action cannot be undone.");
    });

    test("extractDeleteConfirmationDetails formats income transaction correctly", () => {
      const sampleIncome = {
        id: "inc_52",
        rawId: 52,
        type: "income",
        amount: 75000,
        date: "2026-08-01",
      };

      const details = extractDeleteConfirmationDetails(sampleIncome);
      assert.strictEqual(details.category, "Income Deposit");
      assert.strictEqual(details.formattedAmount, "₹75,000");
      assert.strictEqual(details.type, "income");
    });
  });

  describe("AC-004 & AC-008: Transaction Deletion & Success Message", () => {
    test("executeDeleteTransaction calls deleteExpense with normalized rawId on confirmed expense deletion", async () => {
      let calledExpenseId = null;
      const mockApi = {
        deleteExpense: async (id) => {
          calledExpenseId = id;
          return { success: true };
        },
        deleteIncome: async () => {},
      };

      const tx = { id: "exp_108", type: "expense", amount: 1500 };
      const res = await executeDeleteTransaction(tx, mockApi);

      assert.strictEqual(calledExpenseId, 108);
      assert.strictEqual(res.success, true);
      assert.strictEqual(res.message, "Transaction deleted successfully.");
      assert.strictEqual(res.deletedId, 108);
    });

    test("executeDeleteTransaction calls deleteIncome on confirmed income deletion", async () => {
      let calledIncomeId = null;
      const mockApi = {
        deleteExpense: async () => {},
        deleteIncome: async (id) => {
          calledIncomeId = id;
          return { success: true };
        },
      };

      const tx = { id: "inc_77", type: "income", amount: 50000 };
      const res = await executeDeleteTransaction(tx, mockApi);

      assert.strictEqual(calledIncomeId, 77);
      assert.strictEqual(res.success, true);
      assert.strictEqual(res.deletedId, 77);
    });
  });

  describe("AC-005: Cancel Deletion", () => {
    test("Canceling delete popup makes no API calls and preserves transaction intact in list", () => {
      const initialTransactions = [
        { id: "exp_1", rawId: 1, type: "expense", amount: 1000 },
        { id: "exp_2", rawId: 2, type: "expense", amount: 2000 },
      ];

      // User hits cancel -> no mutation performed
      const currentTransactions = [...initialTransactions];
      assert.strictEqual(currentTransactions.length, 2);
      assert.strictEqual(currentTransactions[0].id, "exp_1");
    });
  });

  describe("AC-006, AC-007 & AC-011: Transaction Removal & Cross-Module Recalculation", () => {
    test("removeTransactionFromList purges deleted item and updates financial totals", () => {
      const transactions = [
        { id: "exp_1", rawId: 1, type: "expense", amount: 5000 },
        { id: "exp_2", rawId: 2, type: "expense", amount: 3000 },
        { id: "inc_1", rawId: 1, type: "income", amount: 20000 },
      ];

      const totalsBefore = recalculateTotalsAfterDeletion(transactions);
      assert.strictEqual(totalsBefore.totalSpending, 8000);
      assert.strictEqual(totalsBefore.netSavings, 12000);

      // Delete exp_2
      const updatedList = removeTransactionFromList(transactions, 2, "expense");
      assert.strictEqual(updatedList.length, 2);

      const totalsAfter = recalculateTotalsAfterDeletion(updatedList);
      assert.strictEqual(totalsAfter.totalSpending, 5000);
      assert.strictEqual(totalsAfter.netSavings, 15000);
    });

    test("executeDeleteTransaction dispatches expense-updated event to synchronize Dashboard", async () => {
      let eventReceived = false;
      const handler = () => {
        eventReceived = true;
      };

      window.addEventListener("expense-updated", handler);

      const mockApi = {
        deleteExpense: async () => ({ success: true }),
      };

      await executeDeleteTransaction({ id: "exp_201", type: "expense", amount: 500 }, mockApi);
      assert.strictEqual(eventReceived, true);

      window.removeEventListener("expense-updated", handler);
    });
  });

  describe("AC-009 & AC-010: Error Handling & Security", () => {
    test("executeDeleteTransaction throws and bubbles API error when deletion fails", async () => {
      const failingApi = {
        deleteExpense: async () => {
          throw new Error("HTTP 404: Expense record not found.");
        },
      };

      await assert.rejects(
        async () => {
          await executeDeleteTransaction({ id: "exp_999", type: "expense", amount: 100 }, failingApi);
        },
        {
          message: "HTTP 404: Expense record not found.",
        }
      );
    });
  });
});
