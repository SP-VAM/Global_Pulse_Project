import React, { useEffect, useMemo, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { Search, ArrowLeft, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, TrendingUp, TrendingDown, RefreshCw, AlertCircle } from "lucide-react"

import { getMarketSnapshot } from "../../../api/marketApi.js"
import "./Constituents.css"

const PAGE_SIZE = 10

const COLUMNS = [
  { key: "name", label: "Company", align: "left" },
  { key: "sector", label: "Sector", align: "left" },
  { key: "price", label: "Price (₹)", align: "right" },
  { key: "change", label: "Change", align: "right" },
  { key: "mcap", label: "Mkt Cap", align: "right" },
]

// Sector tag dictionary helper for Nifty 50 tickers
const TICKER_SECTORS = {
  RELIANCE: "Energy", TCS: "IT", HDFCBANK: "Banking", ICICIBANK: "Banking", BHARTIARTL: "Telecom",
  SBIN: "Banking", INFYS: "IT", INFY: "IT", LTIM: "IT", ITC: "FMCG", HINDUNILVR: "FMCG",
  "L&T": "Construction", LT: "Construction", BAJFINANCE: "Financials", HCLTECH: "IT", MARUTI: "Automobile",
  SUNPHARMA: "Healthcare", ADANIENT: "Energy", KOTAKBANK: "Banking", TATAMOTORS: "Automobile",
  ONGC: "Energy", NTPC: "Energy", AXISBANK: "Banking", TITAN: "Consumer", ADANIPORTS: "Services",
  POWERGRID: "Energy", ULTRACOMCEM: "Materials", COALINDIA: "Mining", "M&M": "Automobile", TATASTEEL: "Metals",
  SIEMENS: "Industrial", BAJAJFINSV: "Financials", ASIANPAINT: "Consumer", TRENT: "Retail",
  BEL: "Defense", HAL: "Defense", DLF: "Real Estate", ZOMATO: "Internet", DMART: "Retail",
  IOC: "Energy", GAIL: "Energy", REC: "Financials", PFC: "Financials", VBL: "FMCG",
  NESTLEIND: "FMCG", PIDILITIND: "Chemicals", CHOLAFIN: "Financials", SHRIRAMFIN: "Financials",
  JSWSTEEL: "Metals", GRASIM: "Materials", TECHM: "IT", INDUSINDBK: "Banking", HEROMOTOCO: "Automobile",
  DRREDDY: "Healthcare", CIPLA: "Healthcare", APOLLOHOSP: "Healthcare", EICHERMOT: "Automobile",
  BPCL: "Energy", BRITANNIA: "FMCG", DIVISLAB: "Healthcare"
}

const formatPrice = (n) => (typeof n === "number" ? n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0.00")

const formatMcap = (mcap) => {
  if (!mcap || typeof mcap !== "number" || mcap <= 0) return "—"
  if (mcap >= 1e12) return `₹${(mcap / 1e12).toFixed(2)}T`
  if (mcap >= 1e9) return `₹${(mcap / 1e9).toFixed(2)}B`
  if (mcap >= 1e7) return `₹${(mcap / 1e7).toFixed(2)}Cr`
  return `₹${mcap.toLocaleString("en-IN")}`
}

export default function Constituents() {
  const [items, setItems] = useState([])
  const [status, setStatus] = useState("loading") // "loading" | "success" | "partial_success" | "error" | "empty"
  const [error, setError] = useState(null)
  const [warning, setWarning] = useState(null)

  const [query, setQuery] = useState("")
  const [sector, setSector] = useState("All")
  const [sort, setSort] = useState({ key: "mcap", dir: "desc" })
  const [page, setPage] = useState(1)

  const abortControllerRef = React.useRef(null)
  const isFetchingRef = React.useRef(false)

  const fetchLiveConstituents = async () => {
    // Cancel any previous in-flight fetch
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const controller = new AbortController()
    abortControllerRef.current = controller
    isFetchingRef.current = true

    setStatus("loading")
    setError(null)
    setWarning(null)

    const t0 = performance.now()
    if (process.env.NODE_ENV !== "production") {
      console.log("[MARKET API] Request started | Fetching Nifty 50 constituents...")
    }

    // Set 10-second hard client timeout
    const timeoutId = setTimeout(() => {
      if (isFetchingRef.current) {
        controller.abort()
        console.warn("[MARKET API] Client request timeout after 10000ms")
      }
    }, 10000)

    try {
      const res = await getMarketSnapshot(undefined, { signal: controller.signal })
      clearTimeout(timeoutId)

      const elapsed = (performance.now() - t0).toFixed(1)
      if (process.env.NODE_ENV !== "production") {
        console.log(`[MARKET API] Response received in ${elapsed}ms | Total items: ${res?.items?.length || 0}`)
      }

      if (res && res.items && res.items.length > 0) {
        const mapped = res.items.map((item) => {
          const sym = item.symbol.toUpperCase()
          const sec = TICKER_SECTORS[sym] || "General"
          const price = item.current_price ?? item.previous_close ?? 0
          const changePct = item.change_percent ?? 0
          const mcapVal = item.market_cap || 0
          return {
            ticker: sym,
            name: item.company_name,
            sector: sec,
            price: price,
            change: changePct,
            rawChange: item.change ?? 0,
            rawMcap: mcapVal,
            mcap: formatMcap(mcapVal),
          }
        })

        setItems(mapped)
        if (mapped.length < 50) {
          setStatus("partial_success")
          setWarning(`${mapped.length} of 50 Nifty constituents loaded. Some real-time updates may be delayed.`)
        } else {
          setStatus("success")
        }
      } else {
        setItems([])
        setStatus("empty")
        setError("Market data provider returned an empty response. Please retry in a few moments.")
      }
    } catch (err) {
      clearTimeout(timeoutId)
      if (err.name === "AbortError") {
        console.warn("[MARKET API] Request aborted or timed out.")
        setError("Market data request timed out. Please click Retry to refresh live prices.")
      } else {
        console.error("[MARKET API] Fetch error:", err)
        setError(err.message || "Failed to fetch live Nifty 50 market data.")
      }
      setStatus("error")
    } finally {
      isFetchingRef.current = false
    }
  }

  useEffect(() => {
    fetchLiveConstituents()
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  const sectorsList = useMemo(() => {
    if (!items || items.length === 0) return ["All"]
    return ["All", ...Array.from(new Set(items.map((c) => c.sector))).sort()]
  }, [items])

  const processed = useMemo(() => {
    let rows = items.filter((c) => {
      const matchesQuery =
        c.name.toLowerCase().includes(query.toLowerCase()) || c.ticker.toLowerCase().includes(query.toLowerCase())
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
  }, [items, query, sector, sort])

  const totalPages = Math.max(1, Math.ceil(processed.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const paged = processed.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const toggleSort = (key) => {
    setPage(1)
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }))
  }

  const handleFilter = (value) => {
    setSector(value)
    setPage(1)
  }

  const handleSearch = (value) => {
    setQuery(value)
    setPage(1)
  }

  const loading = status === "loading"

  return (
    <div className="constituents">
      <header className="constituents__head">
        <div>
          <Link to="/dashboard" className="constituents__back">
            <ArrowLeft size={14} /> Dashboard
          </Link>
          <h1 className="gp-page-title">Top 50 Shares</h1>
          <p className="gp-section-sub">All Nifty 50 constituents with live pricing and market cap.</p>
        </div>
        <div className="constituents__search">
          <Search size={16} className="constituents__search-icon" />
          <input
            type="search"
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search company or ticker..."
            aria-label="Search constituents"
          />
        </div>
      </header>

      {/* WARNING BANNER FOR PARTIAL SUCCESS */}
      {warning && status === "partial_success" && (
        <div style={{
          background: "rgba(245, 165, 36, 0.12)",
          border: "1px solid rgba(245, 165, 36, 0.3)",
          borderRadius: "12px",
          padding: "12px 18px",
          marginBottom: "16px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          color: "#f5a524",
          fontSize: "14px",
        }}>
          <AlertCircle size={18} />
          <span>{warning}</span>
        </div>
      )}

      {/* ERROR BANNER */}
      {error && status === "error" && (
        <div style={{
          background: "rgba(239, 68, 68, 0.12)",
          border: "1px solid rgba(239, 68, 68, 0.3)",
          borderRadius: "12px",
          padding: "16px 20px",
          marginBottom: "20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          color: "#f87171"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertCircle size={20} />
            <span>⚠️ {error}</span>
          </div>
          <button
            type="button"
            onClick={fetchLiveConstituents}
            disabled={loading}
            style={{
              background: "#ef4444",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              padding: "6px 14px",
              fontSize: "13px",
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              opacity: loading ? 0.6 : 1,
            }}
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span>{loading ? "Retrying..." : "Retry Live Fetch"}</span>
          </button>
        </div>
      )}

      <div className="constituents__chips gp-chips" role="tablist" aria-label="Filter by sector">
        {sectorsList.map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={sector === s}
            className={`gp-chip${sector === s ? " gp-chip--active" : ""}`}
            onClick={() => handleFilter(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="constituents__table-wrap">
        <table className="constituents__table">
          <thead>
            <tr>
              <th className="constituents__num">#</th>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={`constituents__th constituents__th--${col.align}`}
                  aria-sort={sort.key === col.key ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                >
                  <button className="constituents__sort" onClick={() => toggleSort(col.key)}>
                    {col.label}
                    {sort.key === col.key &&
                      (sort.dir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: "40px", color: "#94a3b8" }}>
                  <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 12px auto", display: "block" }} />
                  <div>Fetching live Nifty 50 market snapshot...</div>
                </td>
              </tr>
            ) : paged.length > 0 ? (
              paged.map((c, i) => {
                const positive = c.change >= 0
                const Ch = positive ? TrendingUp : TrendingDown
                return (
                  <tr key={c.ticker} className="constituents__row">
                    <td className="constituents__num">{(currentPage - 1) * PAGE_SIZE + i + 1}</td>
                    <td>
                      <div className="constituents__company">
                        <span className="constituents__logo" aria-hidden="true">
                          {c.name.charAt(0)}
                        </span>
                        <div className="constituents__names">
                          <span className="constituents__name">{c.name}</span>
                          <span className="constituents__ticker gp-mono">{c.ticker}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="constituents__badge">{c.sector}</span>
                    </td>
                    <td className="constituents__td--right gp-mono">{formatPrice(c.price)}</td>
                    <td className="constituents__td--right">
                      <span className={`constituents__change ${positive ? "gp-pos" : "gp-neg"}`}>
                        <Ch size={12} /> {positive ? "+" : ""}
                        {c.change.toFixed(2)}%
                      </span>
                    </td>
                    <td className="constituents__td--right gp-mono">{c.mcap}</td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan={6} className="constituents__empty">
                  No shares match your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <footer className="constituents__footer">
        <span className="constituents__count">
          {processed.length === 0
            ? "0 results"
            : `Showing ${(currentPage - 1) * PAGE_SIZE + 1}–${Math.min(currentPage * PAGE_SIZE, processed.length)} of ${processed.length}`}
        </span>
        <div className="constituents__pager">
          <button
            className="gp-btn gp-btn--secondary gp-btn--sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1 || loading}
          >
            <ChevronLeft size={14} /> Prev
          </button>
          <span className="constituents__page-info gp-mono">
            {currentPage} / {totalPages}
          </span>
          <button
            className="gp-btn gp-btn--secondary gp-btn--sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages || loading}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      </footer>
    </div>
  )
}
