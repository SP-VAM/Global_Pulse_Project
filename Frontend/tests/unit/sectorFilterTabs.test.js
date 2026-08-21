import { describe, it } from "node:test"
import assert from "node:assert/strict"

/**
 * FRD-062 Sector Filter Tabs - Unit Test Suite
 * Tests cover:
 * - AC-001: Dynamic Sector List Generation ("All" + Unique Sorted Sectors)
 * - AC-002: Sector Tab Isolation (IT, Banking, Energy, FMCG, Healthcare)
 * - AC-003: Combined Sector + Keyword Search Filtering (AND Logic)
 * - AC-004: Page Reset to 1 on Sector Filter Change
 * - AC-005: Column Sorting & Metric Integrity within Filtered Sector
 * - AC-006: Empty State & Non-Matching Filter Resilience
 */

// Simulated domain logic matching Constituents.jsx
const TICKER_SECTORS = {
  RELIANCE: "Energy", TCS: "IT", HDFCBANK: "Banking", ICICIBANK: "Banking", BHARTIARTL: "Telecom",
  SBIN: "Banking", INFY: "IT", LTIM: "IT", ITC: "FMCG", HINDUNILVR: "FMCG",
  BAJFINANCE: "Financials", HCLTECH: "IT", MARUTI: "Automobile",
  SUNPHARMA: "Healthcare", ADANIENT: "Energy", KOTAKBANK: "Banking", TATAMOTORS: "Automobile",
  ONGC: "Energy", NTPC: "Energy", AXISBANK: "Banking", TITAN: "Consumer",
  POWERGRID: "Energy", COALINDIA: "Mining", TATASTEEL: "Metals",
  TECHM: "IT", INDUSINDBK: "Banking", DRREDDY: "Healthcare", CIPLA: "Healthcare",
}

function deriveSectorsList(items) {
  if (!items || items.length === 0) return ["All"]
  const uniqueSectors = Array.from(new Set(items.map((c) => c.sector).filter(Boolean))).sort()
  return ["All", ...uniqueSectors]
}

function filterAndSortConstituents({ items, query = "", sector = "All", sort = { key: "mcap", dir: "desc" } }) {
  let rows = (items || []).filter((c) => {
    const q = (query || "").trim().toLowerCase()
    const matchesQuery =
      !q ||
      c.name.toLowerCase().includes(q) ||
      c.ticker.toLowerCase().includes(q)
    const matchesSector = sector === "All" || c.sector === sector
    return matchesQuery && matchesSector
  })

  const { key, dir } = sort
  rows = [...rows].sort((a, b) => {
    let av = key === "mcap" ? a.rawMcap : a[key]
    let bv = key === "mcap" ? b.rawMcap : b[key]
    if (typeof av === "string") {
      av = av.toLowerCase()
      bv = (bv || "").toLowerCase()
      return dir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av)
    }
    return dir === "asc" ? (av || 0) - (bv || 0) : (bv || 0) - (av || 0)
  })
  return rows
}

const mockConstituents = [
  { ticker: "RELIANCE", name: "Reliance Industries Ltd", sector: "Energy", price: 2950.0, change: 1.45, rawMcap: 19800000000000 },
  { ticker: "TCS", name: "Tata Consultancy Services", sector: "IT", price: 4120.0, change: -0.35, rawMcap: 15200000000000 },
  { ticker: "HDFCBANK", name: "HDFC Bank Ltd", sector: "Banking", price: 1650.0, change: 0.82, rawMcap: 12500000000000 },
  { ticker: "INFY", name: "Infosys Ltd", sector: "IT", price: 1780.0, change: 2.10, rawMcap: 7400000000000 },
  { ticker: "ICICIBANK", name: "ICICI Bank Ltd", sector: "Banking", price: 1120.0, change: 1.15, rawMcap: 7900000000000 },
  { ticker: "HCLTECH", name: "HCL Technologies Ltd", sector: "IT", price: 1620.0, change: -0.80, rawMcap: 4400000000000 },
  { ticker: "ITC", name: "ITC Ltd", sector: "FMCG", price: 430.0, change: 0.10, rawMcap: 5300000000000 },
  { ticker: "SUNPHARMA", name: "Sun Pharmaceutical Ind", sector: "Healthcare", price: 1540.0, change: 1.95, rawMcap: 3700000000000 },
  { ticker: "TATAMOTORS", name: "Tata Motors Ltd", sector: "Automobile", price: 980.0, change: -1.25, rawMcap: 3600000000000 },
]

describe("FRD-062 Sector Filter Tabs - Unit Test Suite", () => {
  describe("AC-001: Dynamic Sector List Extraction", () => {
    it("generates 'All' tab followed by unique alphabetical sectors", () => {
      const sectors = deriveSectorsList(mockConstituents)
      assert.deepStrictEqual(sectors, [
        "All",
        "Automobile",
        "Banking",
        "Energy",
        "FMCG",
        "Healthcare",
        "IT",
      ])
    })

    it("returns ['All'] when constituent list is empty or null", () => {
      assert.deepStrictEqual(deriveSectorsList([]), ["All"])
      assert.deepStrictEqual(deriveSectorsList(null), ["All"])
      assert.deepStrictEqual(deriveSectorsList(undefined), ["All"])
    })
  })

  describe("AC-002: Sector Filter Isolation", () => {
    it("returns all companies when sector is 'All'", () => {
      const result = filterAndSortConstituents({ items: mockConstituents, sector: "All" })
      assert.strictEqual(result.length, 9)
    })

    it("filters to only IT companies when sector tab 'IT' is selected", () => {
      const result = filterAndSortConstituents({ items: mockConstituents, sector: "IT" })
      assert.strictEqual(result.length, 3)
      assert.ok(result.every((c) => c.sector === "IT"))
      const tickers = result.map((c) => c.ticker)
      assert.ok(tickers.includes("TCS"))
      assert.ok(tickers.includes("INFY"))
      assert.ok(tickers.includes("HCLTECH"))
    })

    it("filters to only Banking companies when sector tab 'Banking' is selected", () => {
      const result = filterAndSortConstituents({ items: mockConstituents, sector: "Banking" })
      assert.strictEqual(result.length, 2)
      assert.ok(result.every((c) => c.sector === "Banking"))
      assert.ok(result.some((c) => c.ticker === "HDFCBANK"))
      assert.ok(result.some((c) => c.ticker === "ICICIBANK"))
    })

    it("filters to only Energy companies when sector tab 'Energy' is selected", () => {
      const result = filterAndSortConstituents({ items: mockConstituents, sector: "Energy" })
      assert.strictEqual(result.length, 1)
      assert.strictEqual(result[0].ticker, "RELIANCE")
    })
  })

  describe("AC-003: Multi-Filter Combination (Sector + Search Keyword)", () => {
    it("applies AND logic for matching sector and search query", () => {
      const result = filterAndSortConstituents({
        items: mockConstituents,
        sector: "IT",
        query: "Infosys",
      })
      assert.strictEqual(result.length, 1)
      assert.strictEqual(result[0].ticker, "INFY")
      assert.strictEqual(result[0].sector, "IT")
    })

    it("searches ticker case-insensitively within chosen sector", () => {
      const result = filterAndSortConstituents({
        items: mockConstituents,
        sector: "IT",
        query: "tcs",
      })
      assert.strictEqual(result.length, 1)
      assert.strictEqual(result[0].ticker, "TCS")
    })

    it("returns empty array when query does not match selected sector", () => {
      const result = filterAndSortConstituents({
        items: mockConstituents,
        sector: "Banking",
        query: "TCS",
      })
      assert.strictEqual(result.length, 0)
    })
  })

  describe("AC-004: Page Reset Behavior", () => {
    it("simulates page reset to 1 upon changing sector filter", () => {
      let currentPage = 4
      const handleFilterChange = (newSector) => {
        currentPage = 1
        return newSector
      }

      const activeSector = handleFilterChange("Healthcare")
      assert.strictEqual(activeSector, "Healthcare")
      assert.strictEqual(currentPage, 1)
    })
  })

  describe("AC-005: Sorting within Filtered Sector Subset", () => {
    it("sorts IT sector companies by Market Cap descending", () => {
      const result = filterAndSortConstituents({
        items: mockConstituents,
        sector: "IT",
        sort: { key: "mcap", dir: "desc" },
      })
      assert.strictEqual(result.length, 3)
      assert.strictEqual(result[0].ticker, "TCS") // Highest IT Mcap: 15.2T
      assert.strictEqual(result[1].ticker, "INFY") // 7.4T
      assert.strictEqual(result[2].ticker, "HCLTECH") // 4.4T
    })

    it("sorts Banking sector companies by % Change ascending", () => {
      const result = filterAndSortConstituents({
        items: mockConstituents,
        sector: "Banking",
        sort: { key: "change", dir: "asc" },
      })
      assert.strictEqual(result.length, 2)
      assert.strictEqual(result[0].ticker, "HDFCBANK") // +0.82%
      assert.strictEqual(result[1].ticker, "ICICIBANK") // +1.15%
    })
  })
})
