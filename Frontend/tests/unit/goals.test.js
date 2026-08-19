import { test, describe, beforeEach, mock } from "node:test";
import assert from "node:assert/strict";

// Mock localStorage and window before importing
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
  location: { hostname: "localhost", pathname: "/dashboard/goals" },
};

import {
  fetchGoals,
  createGoalApi,
  updateGoalApi,
  deleteGoalApi,
  addGoalProgressApi,
} from "../../src/api/goalsApi.js";

import {
  formatINR,
  calculateDaysLeft,
  getMilestones,
  getMotivationalMessage,
  getAssetAllocation,
} from "../../src/pages/Dashboard/Goals/goalHelpers.js";

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

describe("Frontend Financial Goals - Unit Test Suite", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  /* -------------------------------------------------------------
   * 1. Helper & Calculation Functions
   * ------------------------------------------------------------- */
  describe("Goals Calculations & Logic", () => {
    test("formatINR formats Indian Rupee currency values properly", () => {
      assert.strictEqual(formatINR(0), "₹0");
      assert.strictEqual(formatINR(50000), "₹50,000");
      assert.strictEqual(formatINR(1500000), "₹15,00,000");
    });

    test("calculateDaysLeft computes correct remaining day count", () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 10);
      const isoStr = futureDate.toISOString().slice(0, 10);

      const days = calculateDaysLeft(isoStr);
      assert.strictEqual(days >= 9 && days <= 11, true);

      // Past date returns 0
      assert.strictEqual(calculateDaysLeft("2020-01-01"), 0);
    });

    test("getMilestones generates 10% step milestones correctly", () => {
      const goal = { target: 100000, progress: 35000 };
      const milestones = getMilestones(goal);

      assert.strictEqual(milestones.length, 10);
      assert.strictEqual(milestones[0].isCompleted, true); // 10%
      assert.strictEqual(milestones[2].isCompleted, true); // 30%
      assert.strictEqual(milestones[3].isCurrent, true);   // 40% (next milestone)
      assert.strictEqual(milestones[4].isFuture, true);    // 50%
    });

    test("getMotivationalMessage reflects completion percentage", () => {
      const msg0 = getMotivationalMessage({ target: 100000, progress: 0 });
      assert.match(msg0, /Take the first step/);

      const msg50 = getMotivationalMessage({ target: 100000, progress: 50000 });
      assert.match(msg50, /50%/);

      const msg100 = getMotivationalMessage({ target: 100000, progress: 100000 });
      assert.match(msg100, /Incredible milestone achieved/);
    });

    test("getAssetAllocation segments progress by asset type", () => {
      const goal = {
        history: [
          { amount: 20000, assetType: "Gold" },
          { amount: 30000, assetType: "Stocks" },
        ],
      };
      const alloc = getAssetAllocation(goal);
      const gold = alloc.find((a) => a.name === "Gold");
      const stocks = alloc.find((a) => a.name === "Stocks");

      assert.strictEqual(gold.percentage, 40);
      assert.strictEqual(stocks.percentage, 60);
    });
  });

  /* -------------------------------------------------------------
   * 2. Goals API Client Integration Tests
   * ------------------------------------------------------------- */
  describe("Goals API Client & CRUD Operations", () => {
    test("fetchGoals attaches JWT and returns user goals list", async () => {
      localStorage.setItem("access_token", "test_jwt_goals_123");

      const mockGoals = [
        {
          goal_id: 1,
          goal_name: "Emergency Fund",
          target_quantity: 500000,
          current_quantity: 150000,
          unit: "INR",
          history: [],
        },
      ];

      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /\/api\/v1\/goals$/);
        assert.strictEqual(options.headers.Authorization, "Bearer test_jwt_goals_123");
        return createMockResponse(mockGoals, 200);
      });

      const res = await fetchGoals();
      assert.deepStrictEqual(res, mockGoals);
      assert.strictEqual(globalThis.fetch.mock.callCount(), 1);
    });

    test("createGoalApi executes POST /api/v1/goals with normalized payload", async () => {
      localStorage.setItem("access_token", "test_jwt_goals_123");

      const goalInput = {
        name: "Car Down Payment",
        target: 200000,
        unit: "INR",
        startDate: "2026-08-01",
        endDate: "2027-08-01",
        note: "EV Purchase",
      };

      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /\/api\/v1\/goals$/);
        assert.strictEqual(options.method, "POST");
        assert.strictEqual(options.headers.Authorization, "Bearer test_jwt_goals_123");

        const body = JSON.parse(options.body);
        assert.strictEqual(body.goal_name, "Car Down Payment");
        assert.strictEqual(body.target_quantity, 200000);

        return createMockResponse({ goal_id: 10, ...body }, 201);
      });

      const res = await createGoalApi(goalInput);
      assert.strictEqual(res.goal_id, 10);
      assert.strictEqual(res.goal_name, "Car Down Payment");
    });

    test("updateGoalApi executes PUT /api/v1/goals/{id}", async () => {
      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /\/api\/v1\/goals\/10$/);
        assert.strictEqual(options.method, "PUT");
        const body = JSON.parse(options.body);
        assert.strictEqual(body.target_quantity, 250000);
        return createMockResponse({ goal_id: 10, target_quantity: 250000 }, 200);
      });

      const res = await updateGoalApi(10, { target: 250000 });
      assert.strictEqual(res.target_quantity, 250000);
    });

    test("addGoalProgressApi executes POST /api/v1/goals/{id}/progress", async () => {
      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /\/api\/v1\/goals\/10\/progress$/);
        assert.strictEqual(options.method, "POST");
        const body = JSON.parse(options.body);
        assert.strictEqual(body.quantity_added, 15000);
        assert.strictEqual(body.asset_type, "Gold");
        return createMockResponse({ goal_id: 10, current_quantity: 15000 }, 200);
      });

      const res = await addGoalProgressApi(10, { amount: 15000, assetType: "Gold", date: "2026-08-19" });
      assert.strictEqual(res.current_quantity, 15000);
    });

    test("deleteGoalApi executes DELETE /api/v1/goals/{id}", async () => {
      globalThis.fetch = mock.fn(async (url, options) => {
        assert.match(url, /\/api\/v1\/goals\/10$/);
        assert.strictEqual(options.method, "DELETE");
        return createMockResponse(null, 204);
      });

      const res = await deleteGoalApi(10);
      assert.strictEqual(res, true);
    });
  });
});
