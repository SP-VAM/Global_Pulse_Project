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
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => true,
};

// ---------------------------------------------------------------------------
// Pure logic extractors matching Dashboard.jsx calculation rules
// ---------------------------------------------------------------------------

function formatVal(num) {
  if (num === null || num === undefined) return "Loading...";
  return "₹" + Math.round(num).toLocaleString("en-IN");
}

function deriveLiveSummaryCards(expenseSummary) {
  const spending = expenseSummary ? (expenseSummary.monthlySpending || 0) : null;
  const income = expenseSummary ? (expenseSummary.monthlyIncome || 0) : null;
  const savings = expenseSummary ? (expenseSummary.savings || 0) : null;
  const totalBudget = expenseSummary ? (expenseSummary.budgets || []).reduce((acc, b) => acc + (Number(b.budgetAmount) || 0), 0) : 0;
  const remainingBudget = totalBudget > 0 && spending !== null ? (totalBudget - spending) : 0;

  return [
    {
      id: "spending",
      label: "Monthly Spending",
      value: formatVal(spending),
      change: spending !== null && spending > 0 ? "Logged" : "₹0 spent",
      positive: false,
    },
    {
      id: "income",
      label: "Income",
      value: formatVal(income),
      change: income !== null && income > 0 ? "Logged" : "₹0 logged",
      positive: true,
    },
    {
      id: "budget",
      label: "Remaining Budget",
      value: expenseSummary ? formatVal(remainingBudget) : "Loading...",
      change: totalBudget === 0 ? "No budget set" : remainingBudget >= 0 ? "In budget" : "Over budget",
      positive: remainingBudget >= 0,
      tone: remainingBudget >= 0 ? "amber" : "red",
    },
    {
      id: "savings",
      label: "Savings",
      value: formatVal(savings),
      change: savings !== null && savings >= 0 ? "Net positive" : "Deficit",
      positive: savings !== null && savings >= 0,
      tone: "green",
    },
  ];
}

function deriveDisplayCompanies(liveMarketItems, defaultSparklines = {}) {
  if (!liveMarketItems || liveMarketItems.length === 0) return [];
  return liveMarketItems.map((item) => {
    const priceVal = item.current_price ?? item.previous_close ?? item.price ?? 0;
    const changePct = item.change_percent ?? item.change ?? 0;
    const positive = changePct >= 0;
    const sym = (item.symbol || item.ticker || "").replace(".NS", "").toUpperCase();
    const compName = item.company_name || item.name || sym;

    const rawHistory = item.price_history || [];
    const validHistory = Array.isArray(rawHistory)
      ? rawHistory.filter(
          (p) => p && typeof p.close === "number" && !isNaN(p.close) && isFinite(p.close) && p.close > 0
        )
      : [];

    const fallbackSpark = defaultSparklines[sym.toLowerCase()] || defaultSparklines[sym] || [10, 25, 40, 35, 60, 80];
    const series = validHistory.length > 0 ? validHistory.map((p) => p.close) : fallbackSpark;

    return {
      id: sym.toLowerCase(),
      name: compName,
      ticker: sym,
      price: typeof priceVal === "number" ? `₹${priceVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : priceVal,
      change: `${positive ? "+" : ""}${typeof changePct === "number" ? changePct.toFixed(2) : changePct}%`,
      positive,
      series,
      price_history: validHistory,
    };
  });
}

function deriveTopMovers(liveMarketItems) {
  if (!liveMarketItems || liveMarketItems.length === 0) return [];
  const sorted = [...liveMarketItems]
    .sort((a, b) => Math.abs(b.change_percent ?? 0) - Math.abs(a.change_percent ?? 0))
    .slice(0, 4);

  return sorted.map((item) => {
    const priceVal = item.current_price ?? item.previous_close ?? 0;
    const changePct = item.change_percent ?? 0;
    const positive = changePct >= 0;
    return {
      id: item.symbol.toLowerCase(),
      name: item.company_name ? item.company_name.split(" ")[0] : item.symbol,
      ticker: item.symbol,
      value: typeof priceVal === "number" ? priceVal.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : priceVal,
      change: `${positive ? "+" : ""}${typeof changePct === "number" ? changePct.toFixed(2) : changePct}%`,
      positive,
    };
  });
}

function filterCompanies(companies, query, pageIndex = 0, pageSize = 4) {
  const q = (query || "").trim().toLowerCase();
  if (q) {
    return companies.filter(
      (c) =>
        (c.name && c.name.toLowerCase().includes(q)) ||
        (c.ticker && c.ticker.toLowerCase().includes(q))
    );
  }
  const start = pageIndex * pageSize;
  return companies.slice(start, start + pageSize);
}

function checkAuthGuard(token) {
  if (!token || token === "demo_token" || token === "null" || token === "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("token");
    return { allowed: false, redirect: "/login" };
  }
  return { allowed: true, redirect: null };
}

// ---------------------------------------------------------------------------
// Unit Test Suites for FRD-007 Dashboard Overview
// ---------------------------------------------------------------------------

describe("FRD-007 Dashboard Overview - Unit Test Suite", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("AC-001 & AC-012: Authentication Guard & User Isolation", () => {
    test("checkAuthGuard denies access and redirects when token is missing", () => {
      const res = checkAuthGuard(null);
      assert.strictEqual(res.allowed, false);
      assert.strictEqual(res.redirect, "/login");
    });

    test("checkAuthGuard denies access and clears storage on demo_token", () => {
      localStorage.setItem("access_token", "demo_token");
      const res = checkAuthGuard("demo_token");
      assert.strictEqual(res.allowed, false);
      assert.strictEqual(res.redirect, "/login");
      assert.strictEqual(localStorage.getItem("access_token"), null);
    });

    test("checkAuthGuard permits valid JWT bearer token", () => {
      const validJwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-IDcSemACtGwtbJnR10oeCXaCGBcz6NevqZsstldNc";
      localStorage.setItem("access_token", validJwt);
      const res = checkAuthGuard(validJwt);
      assert.strictEqual(res.allowed, true);
      assert.strictEqual(res.redirect, null);
    });
  });

  describe("AC-003: Financial Summary Calculations & INR Formatting", () => {
    test("deriveLiveSummaryCards produces exact formatted currency strings for valid budget and spending", () => {
      const mockSummary = {
        monthlySpending: 24500,
        monthlyIncome: 75000,
        savings: 50500,
        budgets: [{ categoryId: 1, budgetAmount: 40000 }],
      };

      const cards = deriveLiveSummaryCards(mockSummary);
      assert.strictEqual(cards.length, 4);

      const spendingCard = cards.find((c) => c.id === "spending");
      assert.strictEqual(spendingCard.value, "₹24,500");
      assert.strictEqual(spendingCard.change, "Logged");
      assert.strictEqual(spendingCard.positive, false);

      const incomeCard = cards.find((c) => c.id === "income");
      assert.strictEqual(incomeCard.value, "₹75,000");
      assert.strictEqual(incomeCard.change, "Logged");
      assert.strictEqual(incomeCard.positive, true);

      const budgetCard = cards.find((c) => c.id === "budget");
      assert.strictEqual(budgetCard.value, "₹15,500");
      assert.strictEqual(budgetCard.change, "In budget");
      assert.strictEqual(budgetCard.positive, true);

      const savingsCard = cards.find((c) => c.id === "savings");
      assert.strictEqual(savingsCard.value, "₹50,500");
      assert.strictEqual(savingsCard.change, "Net positive");
      assert.strictEqual(savingsCard.positive, true);
    });

    test("deriveLiveSummaryCards handles over-budget state accurately", () => {
      const overBudgetSummary = {
        monthlySpending: 55000,
        monthlyIncome: 60000,
        savings: 5000,
        budgets: [{ categoryId: 1, budgetAmount: 40000 }],
      };

      const cards = deriveLiveSummaryCards(overBudgetSummary);
      const budgetCard = cards.find((c) => c.id === "budget");
      assert.strictEqual(budgetCard.value, "₹-15,000");
      assert.strictEqual(budgetCard.change, "Over budget");
      assert.strictEqual(budgetCard.positive, false);
      assert.strictEqual(budgetCard.tone, "red");
    });

    test("deriveLiveSummaryCards handles zero budgets and deficit savings gracefully", () => {
      const deficitSummary = {
        monthlySpending: 30000,
        monthlyIncome: 20000,
        savings: -10000,
        budgets: [],
      };

      const cards = deriveLiveSummaryCards(deficitSummary);
      const budgetCard = cards.find((c) => c.id === "budget");
      assert.strictEqual(budgetCard.value, "₹0");
      assert.strictEqual(budgetCard.change, "No budget set");

      const savingsCard = cards.find((c) => c.id === "savings");
      assert.strictEqual(savingsCard.value, "₹-10,000");
      assert.strictEqual(savingsCard.change, "Deficit");
      assert.strictEqual(savingsCard.positive, false);
    });

    test("deriveLiveSummaryCards handles null summary loading state with placeholders", () => {
      const cards = deriveLiveSummaryCards(null);
      for (const card of cards) {
        assert.strictEqual(card.value, "Loading...");
      }
    });
  });

  describe("AC-002 & AC-008: Market Constituent Intelligence & Sparklines", () => {
    test("deriveDisplayCompanies maps current price, change %, and valid sparkline series", () => {
      const liveItems = [
        {
          symbol: "RELIANCE.NS",
          company_name: "Reliance Industries Ltd",
          current_price: 2985.5,
          change_percent: 1.45,
          price_history: [
            { date: "2026-08-18", close: 2942.8 },
            { date: "2026-08-19", close: 2985.5 },
          ],
        },
        {
          symbol: "TCS.NS",
          company_name: "Tata Consultancy Services Ltd",
          current_price: 4120.0,
          change_percent: -0.85,
          price_history: [],
        },
      ];

      const res = deriveDisplayCompanies(liveItems, { tcs: [4000, 4050, 4120] });
      assert.strictEqual(res.length, 2);

      const rel = res[0];
      assert.strictEqual(rel.ticker, "RELIANCE");
      assert.strictEqual(rel.price, "₹2,985.50");
      assert.strictEqual(rel.change, "+1.45%");
      assert.strictEqual(rel.positive, true);
      assert.deepStrictEqual(rel.series, [2942.8, 2985.5]);

      const tcs = res[1];
      assert.strictEqual(tcs.ticker, "TCS");
      assert.strictEqual(tcs.price, "₹4,120.00");
      assert.strictEqual(tcs.change, "-0.85%");
      assert.strictEqual(tcs.positive, false);
      assert.deepStrictEqual(tcs.series, [4000, 4050, 4120]);
    });

    test("deriveDisplayCompanies sanitizes invalid/negative/NaN candle close values", () => {
      const itemsWithDirtyHistory = [
        {
          symbol: "INFY.NS",
          company_name: "Infosys Ltd",
          current_price: 1850.0,
          change_percent: 0.5,
          price_history: [
            { date: "2026-08-17", close: 1840.0 },
            { date: "2026-08-18", close: null },
            { date: "2026-08-19", close: NaN },
            { date: "2026-08-20", close: -50.0 },
            { date: "2026-08-21", close: 1850.0 },
          ],
        },
      ];

      const res = deriveDisplayCompanies(itemsWithDirtyHistory);
      assert.strictEqual(res[0].price_history.length, 2);
      assert.deepStrictEqual(res[0].series, [1840.0, 1850.0]);
    });
  });

  describe("AC-006: Top Movers Extraction", () => {
    test("deriveTopMovers sorts constituents by highest absolute change percent and takes top 4", () => {
      const liveItems = [
        { symbol: "STOCK_A", company_name: "Company A", current_price: 100, change_percent: 1.2 },
        { symbol: "STOCK_B", company_name: "Company B", current_price: 200, change_percent: -5.4 },
        { symbol: "STOCK_C", company_name: "Company C", current_price: 300, change_percent: 4.8 },
        { symbol: "STOCK_D", company_name: "Company D", current_price: 400, change_percent: 0.3 },
        { symbol: "STOCK_E", company_name: "Company E", current_price: 500, change_percent: -6.1 },
        { symbol: "STOCK_F", company_name: "Company F", current_price: 600, change_percent: 2.1 },
      ];

      const movers = deriveTopMovers(liveItems);
      assert.strictEqual(movers.length, 4);

      // Rank order: STOCK_E (-6.1%), STOCK_B (-5.4%), STOCK_C (+4.8%), STOCK_F (+2.1%)
      assert.strictEqual(movers[0].ticker, "STOCK_E");
      assert.strictEqual(movers[0].change, "-6.10%");
      assert.strictEqual(movers[1].ticker, "STOCK_B");
      assert.strictEqual(movers[1].change, "-5.40%");
      assert.strictEqual(movers[2].ticker, "STOCK_C");
      assert.strictEqual(movers[2].change, "+4.80%");
      assert.strictEqual(movers[3].ticker, "STOCK_F");
      assert.strictEqual(movers[3].change, "+2.10%");
    });
  });

  describe("AC-010: Carousel Slicing & Search Filtering", () => {
    const companies = Array.from({ length: 50 }, (_, i) => ({
      id: `stock_${i + 1}`,
      ticker: `SYM${i + 1}`,
      name: i === 0 ? "Reliance Industries" : i === 1 ? "Tata Motors" : `Company ${i + 1}`,
    }));

    test("filterCompanies without query slices page 0 with 4 items", () => {
      const page0 = filterCompanies(companies, "", 0, 4);
      assert.strictEqual(page0.length, 4);
      assert.strictEqual(page0[0].ticker, "SYM1");
      assert.strictEqual(page0[3].ticker, "SYM4");
    });

    test("filterCompanies with query filters across all items case-insensitively", () => {
      const searchByName = filterCompanies(companies, "reliance", 0, 4);
      assert.strictEqual(searchByName.length, 1);
      assert.strictEqual(searchByName[0].name, "Reliance Industries");

      const searchByTicker = filterCompanies(companies, "sym10", 0, 4);
      assert.strictEqual(searchByTicker.length, 1);
      assert.strictEqual(searchByTicker[0].ticker, "SYM10");
    });

    test("filterCompanies with non-matching query returns empty array", () => {
      const emptyRes = filterCompanies(companies, "NON_EXISTENT_CO", 0, 4);
      assert.strictEqual(emptyRes.length, 0);
    });
  });

  describe("AC-014: Decoupled Failure Resilience", () => {
    test("Financial summary cards compute accurately even when market intelligence dataset is empty/failed", () => {
      const validExpenseSummary = {
        monthlySpending: 12000,
        monthlyIncome: 45000,
        savings: 33000,
        budgets: [{ categoryId: 1, budgetAmount: 20000 }],
      };

      const emptyMarketItems = [];

      const cards = deriveLiveSummaryCards(validExpenseSummary);
      const companies = deriveDisplayCompanies(emptyMarketItems);

      assert.strictEqual(cards.find((c) => c.id === "spending").value, "₹12,000");
      assert.strictEqual(cards.find((c) => c.id === "savings").value, "₹33,000");
      assert.strictEqual(companies.length, 0);
    });
  });
});
