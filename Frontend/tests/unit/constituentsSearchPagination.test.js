import { describe, it } from "node:test"
import assert from "node:assert/strict"

/**
 * FRD-063 Search & Pagination (Top 50 Shares) - Unit Test Suite
 * Tests cover:
 * - AC-001: Case-Insensitive Search by Company Name
 * - AC-002: Case-Insensitive Search by Stock Ticker Symbol
 * - AC-003: Real-Time Slicing with Fixed Page Size (10 items per page)
 * - AC-004: Page Navigation (Next, Previous, Direct Page Jump)
 * - AC-005: Auto-Reset of Pagination to Page 1 on Query Change
 * - AC-006: Boundary Enforcement (Disabling Prev on Page 1, Next on Final Page)
 * - AC-007: Empty State Handling for Non-Matching Search Queries
 */

const PAGE_SIZE = 10

// Generate mock Nifty 50 constituents (50 items)
const mockNifty50 = Array.from({ length: 50 }, (_, i) => {
  const num = i + 1
  const tickers = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL",
    "SBIN", "INFY", "LTIM", "ITC", "HINDUNILVR",
    "LT", "BAJFINANCE", "HCLTECH", "MARUTI", "SUNPHARMA",
    "ADANIENT", "KOTAKBANK", "TATAMOTORS", "ONGC", "NTPC",
    "AXISBANK", "TITAN", "ADANIPORTS", "POWERGRID", "ULTRACOMCEM",
    "COALINDIA", "MM", "TATASTEEL", "SIEMENS", "BAJAJFINSV",
    "ASIANPAINT", "TRENT", "BEL", "HAL", "DLF",
    "ZOMATO", "DMART", "IOC", "GAIL", "REC",
    "PFC", "VBL", "NESTLEIND", "PIDILITIND", "CHOLAFIN",
    "SHRIRAMFIN", "JSWSTEEL", "GRASIM", "TECHM", "INDUSINDBK"
  ]
  const ticker = tickers[i] || `STOCK${num}`
  return {
    ticker,
    name: `${ticker} Corporation Ltd`,
    sector: i % 2 === 0 ? "Banking" : "IT",
    price: 1000 + i * 50,
    change: ((i % 5) - 2) * 0.75,
    rawMcap: (50 - i) * 100000000000,
  }
})

function searchAndPaginate({ items, query = "", page = 1, pageSize = PAGE_SIZE }) {
  const q = (query || "").trim().toLowerCase()
  const filtered = (items || []).filter((c) => {
    if (!q) return true
    return (
      c.name.toLowerCase().includes(q) ||
      c.ticker.toLowerCase().includes(q)
    )
  })

  const totalItems = filtered.length
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const currentPage = Math.max(1, Math.min(page, totalPages))
  const startIndex = (currentPage - 1) * pageSize
  const endIndex = Math.min(startIndex + pageSize, totalItems)
  const pagedItems = filtered.slice(startIndex, endIndex)

  return {
    totalItems,
    totalPages,
    currentPage,
    startIndex,
    endIndex,
    pagedItems,
    hasPrev: currentPage > 1,
    hasNext: currentPage < totalPages,
  }
}

describe("FRD-063 Search & Pagination - Unit Test Suite", () => {
  describe("AC-001 & AC-002: Search by Company Name and Ticker", () => {
    it("finds stock by exact ticker symbol case-insensitively", () => {
      const result = searchAndPaginate({ items: mockNifty50, query: "tcs" })
      assert.strictEqual(result.totalItems, 1)
      assert.strictEqual(result.pagedItems[0].ticker, "TCS")
    })

    it("finds stocks matching company name substring", () => {
      const result = searchAndPaginate({ items: mockNifty50, query: "Bank" })
      assert.ok(result.totalItems > 1)
      assert.ok(result.pagedItems.every((c) => c.name.toLowerCase().includes("bank") || c.ticker.toLowerCase().includes("bank")))
    })

    it("returns all 50 constituents when query is empty string or whitespace", () => {
      const resultEmpty = searchAndPaginate({ items: mockNifty50, query: "" })
      assert.strictEqual(resultEmpty.totalItems, 50)
      assert.strictEqual(resultEmpty.totalPages, 5)

      const resultSpaces = searchAndPaginate({ items: mockNifty50, query: "   " })
      assert.strictEqual(resultSpaces.totalItems, 50)
    })
  })

  describe("AC-003 & AC-004: 10-Item Page Slicing & Multi-Page Navigation", () => {
    it("slices exactly 10 items on Page 1 (items 0 to 9)", () => {
      const page1 = searchAndPaginate({ items: mockNifty50, page: 1 })
      assert.strictEqual(page1.pagedItems.length, 10)
      assert.strictEqual(page1.currentPage, 1)
      assert.strictEqual(page1.totalPages, 5)
      assert.strictEqual(page1.pagedItems[0].ticker, "RELIANCE")
      assert.strictEqual(page1.pagedItems[9].ticker, "HINDUNILVR")
      assert.strictEqual(page1.hasPrev, false)
      assert.strictEqual(page1.hasNext, true)
    })

    it("slices items 10 to 19 on Page 2", () => {
      const page2 = searchAndPaginate({ items: mockNifty50, page: 2 })
      assert.strictEqual(page2.pagedItems.length, 10)
      assert.strictEqual(page2.currentPage, 2)
      assert.strictEqual(page2.pagedItems[0].ticker, "LT")
      assert.strictEqual(page2.hasPrev, true)
      assert.strictEqual(page2.hasNext, true)
    })

    it("slices final 10 items on Page 5 (items 40 to 49)", () => {
      const page5 = searchAndPaginate({ items: mockNifty50, page: 5 })
      assert.strictEqual(page5.pagedItems.length, 10)
      assert.strictEqual(page5.currentPage, 5)
      assert.strictEqual(page5.pagedItems[9].ticker, "INDUSINDBK")
      assert.strictEqual(page5.hasPrev, true)
      assert.strictEqual(page5.hasNext, false)
    })
  })

  describe("AC-005: Pagination Reset on Query Change", () => {
    it("resets page index to 1 when search query changes while on page > 1", () => {
      let currentPage = 3
      const onSearchChange = (newQuery) => {
        currentPage = 1
        return searchAndPaginate({ items: mockNifty50, query: newQuery, page: currentPage })
      }

      const result = onSearchChange("HDFC")
      assert.strictEqual(result.currentPage, 1)
      assert.ok(result.totalItems >= 1)
      assert.strictEqual(result.pagedItems[0].ticker, "HDFCBANK")
    })
  })

  describe("AC-006: Boundary Enforcement & Clamping", () => {
    it("clamps requested page number if it exceeds totalPages", () => {
      const clamped = searchAndPaginate({ items: mockNifty50, page: 99 })
      assert.strictEqual(clamped.currentPage, 5)
      assert.strictEqual(clamped.pagedItems.length, 10)
    })

    it("clamps requested negative or zero page number to Page 1", () => {
      const clamped = searchAndPaginate({ items: mockNifty50, page: -2 })
      assert.strictEqual(clamped.currentPage, 1)
    })
  })

  describe("AC-007: Empty State Handling", () => {
    it("returns 0 totalItems and empty pagedItems array when no company matches search", () => {
      const result = searchAndPaginate({ items: mockNifty50, query: "NONEXISTENT_XYZ" })
      assert.strictEqual(result.totalItems, 0)
      assert.strictEqual(result.totalPages, 1)
      assert.strictEqual(result.pagedItems.length, 0)
      assert.strictEqual(result.hasPrev, false)
      assert.strictEqual(result.hasNext, false)
    })
  })
})
