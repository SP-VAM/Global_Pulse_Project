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
  location: { hostname: "localhost", pathname: "/dashboard/constituents" },
};

import {
  getSupportedCompanies,
  getMarketSnapshot,
  getStockAnalysis,
  getStockSentiment,
} from "../../src/api/marketApi.js";

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

describe("Frontend Market API Client - Unit Test Suite", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("getSupportedCompanies fetches list of Nifty 50 companies", async () => {
    const mockCompanies = {
      companies: [
        { symbol: "RELIANCE", name: "Reliance Industries" },
        { symbol: "TCS", name: "Tata Consultancy Services" },
      ],
    };

    globalThis.fetch = mock.fn(async (url) => {
      assert.match(url, /\/api\/v1\/stocks\/companies$/);
      return createMockResponse(mockCompanies, 200);
    });

    const res = await getSupportedCompanies();
    assert.deepStrictEqual(res, mockCompanies);
    assert.strictEqual(globalThis.fetch.mock.callCount(), 1);
  });

  test("getMarketSnapshot queries bulk market snapshot for top 50 shares", async () => {
    const mockSnapshot = {
      timestamp: "2026-08-19T12:00:00Z",
      items: [
        {
          symbol: "RELIANCE",
          company_name: "Reliance Industries",
          current_price: 2950.5,
          previous_close: 2920.0,
          change: 30.5,
          change_percent: 1.04,
          market_cap: 20000000000000,
        },
      ],
    };

    globalThis.fetch = mock.fn(async (url) => {
      assert.match(url, /\/api\/v1\/stocks\/market-snapshot/);
      return createMockResponse(mockSnapshot, 200);
    });

    const res = await getMarketSnapshot();
    assert.deepStrictEqual(res, mockSnapshot);
    assert.strictEqual(res.items[0].symbol, "RELIANCE");
    assert.strictEqual(globalThis.fetch.mock.callCount(), 1);
  });

  test("getStockAnalysis fetches detailed technical indicators and price history", async () => {
    const mockAnalysis = {
      symbol: "TCS",
      current_price: 4150.0,
      indicators: { rsi: 55.4, macd: 12.5 },
    };

    globalThis.fetch = mock.fn(async (url) => {
      assert.match(url, /\/api\/v1\/stocks\/TCS\/analysis/);
      return createMockResponse(mockAnalysis, 200);
    });

    const res = await getStockAnalysis("TCS");
    assert.deepStrictEqual(res, mockAnalysis);
  });

  test("getStockSentiment fetches live sentiment metrics", async () => {
    const mockSentiment = {
      symbol: "INFY",
      total_articles: 15,
      positive_count: 10,
      negative_count: 2,
      sentiment_score: 0.75,
    };

    globalThis.fetch = mock.fn(async (url) => {
      assert.match(url, /\/api\/v1\/stocks\/INFY\/sentiment/);
      return createMockResponse(mockSentiment, 200);
    });

    const res = await getStockSentiment("INFY");
    assert.deepStrictEqual(res, mockSentiment);
  });

  test("getMarketSnapshot automatically retries on transient Failed to fetch error", async () => {
    let callCount = 0;
    globalThis.fetch = mock.fn(async () => {
      callCount++;
      if (callCount === 1) {
        throw new TypeError("Failed to fetch");
      }
      return createMockResponse({ items: [{ symbol: "RELIANCE" }] }, 200);
    });

    const res = await getMarketSnapshot(undefined, 2);
    assert.strictEqual(res.items.length, 1);
    assert.strictEqual(callCount, 2); // Succeeded on retry attempt 2
  });
});
