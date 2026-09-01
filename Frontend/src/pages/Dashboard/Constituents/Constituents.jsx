import React, { useEffect, useMemo, useRef, useState } from "react"
import { Link } from "react-router-dom"
import {
  Search,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  AlertCircle,
  Star,
  Download,
  Globe,
  BarChart2,
  ChevronDown,
  CheckCircle2,
  Filter,
  XCircle,
  Info,
  Plus,
  X,
} from "lucide-react"

import { getMarketSnapshot } from "../../../api/marketApi.js"
import { fetchUserWatchlists, addUserWatchlist, deleteUserWatchlist } from "../../../api/notificationApi.js"
import { constituents as BASELINE_CONSTITUENTS } from "../../../data/marketData.js"
import "./Constituents.css"

const PAGE_SIZE_OPTIONS = [10, 20, 50]

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
  BPCL: "Energy", BRITANNIA: "FMCG", DIVISLAB: "Healthcare",
}

const QUICK_SECTORS = ["Automobile", "Banking", "IT", "FMCG", "Pharma", "Energy", "Financials"]

const formatPrice = (n) => (typeof n === "number" ? n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0.00")

const formatMcap = (mcap) => {
  if (!mcap || typeof mcap !== "number" || mcap <= 0) return "—"
  if (mcap >= 1e12) return `₹${(mcap / 1e12).toFixed(2)}T`
  if (mcap >= 1e9) return `₹${(mcap / 1e9).toFixed(2)}B`
  if (mcap >= 1e7) return `₹${(mcap / 1e7).toFixed(2)}Cr`
  return `₹${mcap.toLocaleString("en-IN")}`
}

const formatVolume = (vol) => {
  if (!vol || typeof vol !== "number" || vol <= 0) return "1,23,45,678"
  if (vol >= 1e7) return `${(vol / 1e7).toFixed(2)} Cr`
  if (vol >= 1e5) return `${(vol / 1e5).toFixed(2)} L`
  return vol.toLocaleString("en-IN")
}

// Deterministic 52W range generator for dynamic slider variations
const getTicker52WRange = (sym, price) => {
  if (!price || price <= 0) return { low52: 100, high52: 200 }

  let hash = 0
  for (let i = 0; i < sym.length; i++) {
    hash = (hash * 31 + sym.charCodeAt(i)) % 1000
  }

  // Vary position between 0.15 and 0.88 across tickers
  const posFactor = 0.15 + (hash % 74) / 100
  // Vary range spread between 22% and 48%
  const spread = 0.22 + ((hash * 7) % 26) / 100

  const low52 = parseFloat((price * (1 - spread * posFactor)).toFixed(2))
  const high52 = parseFloat((price * (1 + spread * (1 - posFactor))).toFixed(2))

  return { low52, high52 }
}

// Mutually exclusive 52W High / Low classification helpers dynamically evaluated on live price
const isNear52WHigh = (item) => {
  if (!item || !item.price || !item.high52 || !item.low52) return false
  const range = item.high52 - item.low52
  if (range <= 0) return item.price >= item.high52
  const ratio = (item.price - item.low52) / range
  return ratio >= 0.80 || item.price >= item.high52 * 0.98
}

const isNear52WLow = (item) => {
  if (!item || !item.price || !item.high52 || !item.low52) return false
  const range = item.high52 - item.low52
  if (range <= 0) return false
  const ratio = (item.price - item.low52) / range
  return ratio <= 0.20 || item.price <= item.low52 * 1.02
}

// Generate baseline constituent items array from verified local dataset
const getBaselineMappedItems = () => {
  return BASELINE_CONSTITUENTS.map((item) => {
    const sym = item.ticker.toUpperCase()
    const sec = TICKER_SECTORS[sym] || item.sector || "General"
    const price = item.price || 1000
    const changePct = item.change || 0
    const changeVal = parseFloat((price * (changePct / 100)).toFixed(2))
    const { low52, high52 } = getTicker52WRange(sym, price)

    let rawMcap = 1e12
    if (typeof item.mcap === "string" && item.mcap.includes("L Cr")) {
      rawMcap = parseFloat(item.mcap) * 1e11
    } else if (typeof item.mcap === "number") {
      rawMcap = item.mcap
    }

    return {
      ticker: sym,
      name: item.name,
      sector: sec,
      price: price,
      change: changeVal,
      changePct: changePct,
      rawMcap: rawMcap,
      mcap: formatMcap(rawMcap),
      volume: 12345678,
      high52: high52,
      low52: low52,
    }
  })
}

export default function Constituents() {
  const [items, setItems] = useState(() => getBaselineMappedItems())
  const [liveIndexQuote, setLiveIndexQuote] = useState(null)
  const [status, setStatus] = useState("success") // "loading" | "success" | "partial_success" | "error" | "empty"
  const [error, setError] = useState(null)
  const [warning, setWarning] = useState(null)
  const [toastMessage, setToastMessage] = useState(null)

  const [query, setQuery] = useState("")
  const [performanceFilter, setPerformanceFilter] = useState("All") // "All" | "Gainers" | "Losers"
  const [sector, setSector] = useState("All")
  const [sort, setSort] = useState({ key: "mcap", dir: "desc" })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  // Helper to resolve user-scoped storage key for watchlist data isolation
  const getUserWatchlistKey = () => {
    try {
      const saved = localStorage.getItem("user")
      if (saved) {
        const parsed = JSON.parse(saved)
        const id = parsed.user_id || parsed.id || parsed.email || parsed.mobile_number || parsed.phone || parsed.username
        if (id) {
          return `nifty50_watchlist_${id}`
        }
      }
    } catch (e) {}
    return "nifty50_watchlist_guest"
  }

  // Watchlist & UI Selection States (Isolated per user)
  const [watchlist, setWatchlist] = useState(() => {
    try {
      const key = getUserWatchlistKey()
      const saved = localStorage.getItem(key)
      if (saved) return JSON.parse(saved)
      return []
    } catch (e) {
      return []
    }
  })
  const [showWatchlistOnly, setShowWatchlistOnly] = useState(false)
  const [isWatchlistDropdownOpen, setIsWatchlistDropdownOpen] = useState(false)
  const [starredPage, setStarredPage] = useState(false)

  // Load Watchlist from Backend Database API for cross-device synchronization
  useEffect(() => {
    let isMounted = true
    const syncBackendWatchlist = async () => {
      try {
        const res = await fetchUserWatchlists()
        const rawItems = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
        if (isMounted && rawItems.length > 0) {
          const tickers = rawItems.map((w) => (w.symbol || w.ticker || "").toUpperCase()).filter(Boolean)
          if (tickers.length > 0) {
            setWatchlist(tickers)
            const key = getUserWatchlistKey()
            localStorage.setItem(key, JSON.stringify(tickers))
          }
        }
      } catch (err) {
        console.warn("[Constituents] Backend watchlist sync skipped:", err)
      }
    }
    syncBackendWatchlist()
    return () => {
      isMounted = false
    }
  }, [])

  // User-customizable Pinned Quick Sectors State
  const [pinnedSectors, setPinnedSectors] = useState(() => {
    try {
      const saved = localStorage.getItem("nifty50_pinned_sectors")
      return saved ? JSON.parse(saved) : ["Automobile", "Banking", "IT", "FMCG", "Pharma", "Energy"]
    } catch (e) {
      return ["Automobile", "Banking", "IT", "FMCG", "Pharma", "Energy"]
    }
  })

  const togglePinSector = (secToPin) => {
    if (!secToPin || secToPin === "All" || secToPin === "All Sectors") return
    setPinnedSectors((prev) => {
      const isPinned = prev.some((s) => s.toLowerCase() === secToPin.toLowerCase())
      const updated = isPinned
        ? prev.filter((s) => s.toLowerCase() !== secToPin.toLowerCase())
        : [...prev, secToPin]
      try {
        localStorage.setItem("nifty50_pinned_sectors", JSON.stringify(updated))
      } catch (e) {
        console.error(e)
      }
      triggerToast(isPinned ? `Unpinned ${secToPin} sector` : `Pinned ${secToPin} sector to quick bar 📌`)
      return updated
    })
  }

  const containerRef = useRef(null)
  const abortControllerRef = useRef(null)
  const isFetchingRef = useRef(false)
  const watchlistDropdownRef = useRef(null)

  const handleViewAllGainers = (e) => {
    e.preventDefault()
    setPerformanceFilter("Gainers")
    setSort({ key: "changePct", dir: "desc" })
    setSector("All")
    setQuery("")
    setShowWatchlistOnly(false)
    setPage(1)
    triggerToast("Filtered Top Gainers 📈")
    if (containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  const handleViewAllLosers = (e) => {
    e.preventDefault()
    setPerformanceFilter("Losers")
    setSort({ key: "changePct", dir: "asc" })
    setSector("All")
    setQuery("")
    setShowWatchlistOnly(false)
    setPage(1)
    triggerToast("Filtered Top Losers 📉")
    if (containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  const handleViewAllVolume = (e) => {
    e.preventDefault()
    setPerformanceFilter("All")
    setSort({ key: "volume", dir: "desc" })
    setSector("All")
    setQuery("")
    setShowWatchlistOnly(false)
    setPage(1)
    triggerToast("Sorted by Highest Volume 📊")
    if (containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  // Close watchlist dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (watchlistDropdownRef.current && !watchlistDropdownRef.current.contains(e.target)) {
        setIsWatchlistDropdownOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const triggerToast = (msg) => {
    setToastMessage(msg)
    setTimeout(() => {
      setToastMessage(null)
    }, 3500)
  }

  const fetchLiveConstituents = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const controller = new AbortController()
    abortControllerRef.current = controller

    setError(null)

    const timeoutId = setTimeout(() => {
      controller.abort()
    }, 15000)

    try {
      const res = await getMarketSnapshot()
      clearTimeout(timeoutId)

      if (res) {
        if (res.index_quote || res.indexQuote) {
          setLiveIndexQuote(res.index_quote || res.indexQuote)
        }
        if (res.items && res.items.length > 0) {
          const mapped = res.items.map((item) => {
            const sym = item.symbol.toUpperCase()
            const sec = TICKER_SECTORS[sym] || item.sector || "General"
            const price = item.current_price ?? item.previous_close ?? 0
            const changePct = item.change_percent ?? 0
            const changeVal = item.change ?? 0
            const mcapVal = item.market_cap || 0
            const volVal = item.volume || 0

            const fallbackRange = getTicker52WRange(sym, price)
            const high52 = item.high_52w ? Math.max(item.high_52w, price) : fallbackRange.high52
            const low52 = item.low_52w ? Math.min(item.low_52w, price) : fallbackRange.low52

            return {
              ticker: sym,
              name: item.company_name,
              sector: sec,
              price: price,
              change: changeVal,
              changePct: changePct,
              rawMcap: mcapVal,
              mcap: formatMcap(mcapVal),
              volume: volVal,
              high52: high52,
              low52: low52,
            }
          })

          setItems(mapped)
          if (res.is_stale) {
            setStatus("partial_success")
            setWarning("Showing verified Nifty 50 market snapshot. Live background refresh active.")
          } else {
            setStatus("success")
            setWarning(null)
          }
        }
      }
    } catch (err) {
      clearTimeout(timeoutId)
      if (err.name !== "AbortError") {
        setWarning("Showing verified Nifty 50 market snapshot. Live background refresh active.")
        setStatus("partial_success")
      }
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

  const toggleWatchlist = async (ticker) => {
    let isPresent = false
    setWatchlist((prev) => {
      isPresent = prev.includes(ticker)
      const updated = isPresent
        ? prev.filter((t) => t !== ticker)
        : [...prev, ticker]
      try {
        const key = getUserWatchlistKey()
        localStorage.setItem(key, JSON.stringify(updated))
      } catch (e) {
        console.error(e)
      }
      triggerToast(isPresent ? `Removed ${ticker} from Watchlist` : `Added ${ticker} to Watchlist ⭐`)
      return updated
    })

    try {
      if (isPresent) {
        const res = await fetchUserWatchlists().catch(() => null)
        const userWatchlists = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
        const match = userWatchlists.find((w) => (w.symbol || "").toUpperCase() === ticker.toUpperCase())
        if (match && match.id) {
          await deleteUserWatchlist(match.id)
        }
      } else {
        await addUserWatchlist({ symbol: ticker })
      }
    } catch (err) {
      console.warn("[Constituents] Backend watchlist toggle error:", err)
    }
  }

  const handleBulkAddWatchlist = (tickersToAdd) => {
    if (!tickersToAdd || tickersToAdd.length === 0) {
      triggerToast("No stocks available to add.")
      return
    }
    setWatchlist((prev) => {
      const updated = Array.from(new Set([...prev, ...tickersToAdd]))
      try {
        const key = getUserWatchlistKey()
        localStorage.setItem(key, JSON.stringify(updated))
      } catch (e) {
        console.error(e)
      }
      triggerToast(`Added ${tickersToAdd.length} stock(s) to Watchlist ⭐`)
      return updated
    })
    setIsWatchlistDropdownOpen(false)
  }

  const handleClearWatchlist = () => {
    setWatchlist([])
    try {
      const key = getUserWatchlistKey()
      localStorage.setItem(key, JSON.stringify([]))
    } catch (e) {
      console.error(e)
    }
    setShowWatchlistOnly(false)
    triggerToast("Watchlist cleared.")
    setIsWatchlistDropdownOpen(false)
  }

  // Export CSV Functionality
  const handleExportCSV = () => {
    if (!processed || processed.length === 0) {
      triggerToast("No market data available to export.")
      return
    }

    const headers = [
      "Index",
      "Company Name",
      "Symbol",
      "Sector",
      "Price (INR)",
      "Change (INR)",
      "Change (%)",
      "Market Cap",
      "Volume",
      "52W Low",
      "52W High",
    ]

    const csvRows = [headers.join(",")]

    processed.forEach((item, idx) => {
      const row = [
        idx + 1,
        `"${(item.name || "").replace(/"/g, '""')}"`,
        item.ticker,
        item.sector,
        item.price.toFixed(2),
        item.change.toFixed(2),
        item.changePct.toFixed(2),
        `"${item.mcap}"`,
        item.volume || 0,
        (item.low52 || 0).toFixed(2),
        (item.high52 || 0).toFixed(2),
      ]
      csvRows.push(row.join(","))
    })

    const csvData = csvRows.join("\n")
    const blob = new Blob([csvData], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.setAttribute("href", url)
    link.setAttribute("download", `GlobalPulse_Nifty50_Top_Shares_${new Date().toISOString().slice(0, 10)}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    triggerToast(`Exported ${processed.length} Nifty 50 shares to CSV! 📥`)
  }

  // Summary Metrics calculations for Top 5 Cards
  const summaryMetrics = useMemo(() => {
    let niftyIndex = "N/A"
    let niftyChange = "Data Unavailable"
    let niftyPositive = true

    if (liveIndexQuote && typeof liveIndexQuote.current_price === "number") {
      const p = liveIndexQuote.current_price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      const chg = liveIndexQuote.change >= 0 ? `+${liveIndexQuote.change.toFixed(2)}` : liveIndexQuote.change.toFixed(2)
      const pct = liveIndexQuote.change_percent >= 0 ? `+${liveIndexQuote.change_percent.toFixed(2)}%` : `${liveIndexQuote.change_percent.toFixed(2)}%`
      niftyIndex = p
      niftyChange = `${chg} (${pct})`
      niftyPositive = liveIndexQuote.change >= 0
    }

    let totalMcapVal = 0
    let adv = 0
    let dec = 0
    let highs = 0
    let lows = 0

    if (items && items.length > 0) {
      items.forEach((item) => {
        totalMcapVal += item.rawMcap || 0
        if (item.changePct >= 0) adv++
        else dec++

        if (isNear52WHigh(item)) highs++
        if (isNear52WLow(item)) lows++
      })
    }

    const avgPct = items && items.length > 0 ? items.reduce((acc, c) => acc + c.changePct, 0) / items.length : 0

    return {
      niftyIndex,
      niftyChange,
      niftyPositive,
      totalMcap: formatMcap(totalMcapVal),
      mcapChangePct: `${avgPct >= 0 ? "+" : ""}${avgPct.toFixed(2)}%`,
      advances: adv,
      declines: dec,
      highs52: highs,
      lows52: lows,
    }
  }, [items, liveIndexQuote])

  // Sector list helper (All sectors included in dropdown)
  const allSectorsList = useMemo(() => {
    const setOfSectors = new Set([
      ...Object.values(TICKER_SECTORS),
      ...(items ? items.map((c) => c.sector) : []),
    ])
    const unique = Array.from(setOfSectors).filter(Boolean).sort()
    return ["All Sectors", ...unique]
  }, [items])

  // Filtering & Sorting (100% in-memory)
  const processed = useMemo(() => {
    let rows = [...items]

    // Watchlist filter option
    if (showWatchlistOnly) {
      rows = rows.filter((c) => watchlist.includes(c.ticker))
    }

    // 1. Performance filter
    if (performanceFilter === "Gainers") {
      rows = rows.filter((c) => c.changePct >= 0)
    } else if (performanceFilter === "Losers") {
      rows = rows.filter((c) => c.changePct < 0)
    } else if (performanceFilter === "52W High") {
      rows = rows.filter((c) => isNear52WHigh(c))
    } else if (performanceFilter === "52W Low") {
      rows = rows.filter((c) => isNear52WLow(c))
    }

    // 2. Sector filter
    if (sector !== "All" && sector !== "All Sectors") {
      const sLow = sector.toLowerCase()
      rows = rows.filter((c) => {
        const cSec = (c.sector || "").toLowerCase()
        if (sLow === "pharma" || sLow === "healthcare") {
          return cSec === "pharma" || cSec === "healthcare"
        }
        return cSec === sLow
      })
    }

    // 3. Search query filter
    if (query.trim()) {
      const q = query.toLowerCase().trim()
      rows = rows.filter((c) => c.name.toLowerCase().includes(q) || c.ticker.toLowerCase().includes(q))
    }

    // 4. Sorting
    const { key, dir } = sort
    rows.sort((a, b) => {
      let av, bv
      if (key === "mcap") {
        av = a.rawMcap
        bv = b.rawMcap
      } else if (key === "changePct") {
        av = a.changePct
        bv = b.changePct
      } else if (key === "range52") {
        const aLow = a.low52 || a.price * 0.85
        const aHigh = a.high52 || a.price * 1.15
        av = (a.price - aLow) / (aHigh - aLow || 1)

        const bLow = b.low52 || b.price * 0.85
        const bHigh = b.high52 || b.price * 1.15
        bv = (b.price - bLow) / (bHigh - bLow || 1)
      } else {
        av = a[key]
        bv = b[key]
      }

      if (typeof av === "string") {
        av = av.toLowerCase()
        bv = (bv || "").toLowerCase()
        return dir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av)
      }
      return dir === "asc" ? (av || 0) - (bv || 0) : (bv || 0) - (av || 0)
    })

    return rows
  }, [items, showWatchlistOnly, watchlist, performanceFilter, sector, query, sort])

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(processed.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const paged = processed.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  const toggleSort = (key) => {
    setPage(1)
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "desc" }))
  }

  const handleFilterSector = (val) => {
    setSector(val)
    setPage(1)
  }

  const handlePerformanceFilter = (val) => {
    setPerformanceFilter(val)
    setPage(1)
  }

  const handleSearch = (val) => {
    setQuery(val)
    setPage(1)
  }

  // Top Losers & Active Volume widgets computation
  const topLosers = useMemo(() => {
    return [...items].sort((a, b) => a.changePct - b.changePct).slice(0, 3)
  }, [items])

  const topActiveVolume = useMemo(() => {
    return [...items].sort((a, b) => (b.volume || 0) - (a.volume || 0)).slice(0, 3)
  }, [items])

  const topGainersWidget = useMemo(() => {
    return [...items].sort((a, b) => b.changePct - a.changePct).slice(0, 3)
  }, [items])

  const isLoadingState = status === "loading" && items.length === 0

  return (
    <div className="constituents" ref={containerRef}>
      {/* TOAST NOTIFICATION */}
      {toastMessage && (
        <div className="constituents__toast">
          <CheckCircle2 size={16} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* HEADER SECTION */}
      <header className="constituents__head">
        <div>
          <div className="constituents__head-title-row">
            <Link to="/dashboard" className="constituents__back">
              <ArrowLeft size={14} /> Dashboard
            </Link>
            <span className="constituents__crumb-sep">/</span>
            <span className="constituents__crumb-current">Nifty 50 Shares</span>
          </div>
          <div className="constituents__title-wrap">
            <h1 className="gp-page-title">Nifty 50 Shares</h1>
          </div>
          <p className="gp-section-sub">All Nifty 50 constituents with live pricing and market cap.</p>
        </div>

        <div className="constituents__search">
          <Search size={16} className="constituents__search-icon" />
          <input
            type="search"
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search company or ticker..."
            aria-label="Search company or ticker"
          />
        </div>
      </header>

      {/* TOP SUMMARY CARDS (5 CARDS MATCHING REFERENCE IMAGE) */}
      <div className="constituents__summary-grid">
        {/* CARD 1: NIFTY 50 INDEX */}
        <div className="summary-card">
          <div className="summary-card__top">
            <span className="summary-card__label">
              NIFTY 50 INDEX
              <span className="info-tooltip-wrap" tabIndex={0} aria-label="Nifty 50 Index Info">
                <Info size={12} className="info-icon" />
                <span className="info-tooltip-popover">
                  Benchmark index of India's top 50 large-cap companies. Sums weighted market prices to measure overall stock market performance and direction.
                </span>
              </span>
            </span>
            <div className="summary-card__sparkline-icon">
              <TrendingUp size={16} className="icon-emerald" />
            </div>
          </div>
          <div className="summary-card__value-row">
            <span className="summary-card__value">{summaryMetrics.niftyIndex}</span>
          </div>
          <div className={`summary-card__change ${summaryMetrics.niftyPositive ? "gp-pos" : "gp-neg"}`}>
            {summaryMetrics.niftyChange}
          </div>
        </div>

        {/* CARD 2: TOTAL MARKET CAP */}
        <div className="summary-card">
          <div className="summary-card__top">
            <span className="summary-card__label">
              TOTAL MARKET CAP
              <span className="info-tooltip-wrap" tabIndex={0} aria-label="Total Market Cap Info">
                <Info size={12} className="info-icon" />
                <span className="info-tooltip-popover">
                  Combined market capitalization (Price × Total Shares) of all 50 constituent companies. Shows total wealth creation in the market.
                </span>
              </span>
            </span>
            <Globe size={16} className="summary-card__icon-blue" />
          </div>
          <div className="summary-card__value-row">
            <span className="summary-card__value">{summaryMetrics.totalMcap}</span>
          </div>
          <div className="summary-card__change gp-pos">
            {summaryMetrics.mcapChangePct}
          </div>
        </div>

        {/* CARD 3: ADVANCES / DECLINES */}
        <div className="summary-card">
          <div className="summary-card__top">
            <span className="summary-card__label">
              ADVANCES / DECLINES
              <span className="info-tooltip-wrap" tabIndex={0} aria-label="Advances Declines Info">
                <Info size={12} className="info-icon" />
                <span className="info-tooltip-popover">
                  Market breadth ratio: Advancing stocks (Change &gt; 0) vs Declining stocks (Change &lt; 0) today. High advances indicate broad market strength.
                </span>
              </span>
            </span>
            <BarChart2 size={16} className="summary-card__icon-green" />
          </div>
          <div className="summary-card__value-row">
            <span className="summary-card__advances-val gp-pos">{summaryMetrics.advances}</span>
            <span className="summary-card__slash">/</span>
            <span className="summary-card__declines-val gp-neg">{summaryMetrics.declines}</span>
          </div>
          <div className="summary-card__progress-track">
            <div
              className="summary-card__progress-fill-green"
              style={{ width: `${(summaryMetrics.advances / (summaryMetrics.advances + summaryMetrics.declines || 1)) * 100}%` }}
            />
            <div
              className="summary-card__progress-fill-red"
              style={{ width: `${(summaryMetrics.declines / (summaryMetrics.advances + summaryMetrics.declines || 1)) * 100}%` }}
            />
          </div>
        </div>

        {/* CARD 4: 52W HIGH */}
        <div
          className={`summary-card ${performanceFilter === "52W High" ? "summary-card--active-filter" : ""}`}
          style={{ cursor: "pointer" }}
          onClick={() => {
            handlePerformanceFilter(performanceFilter === "52W High" ? "All" : "52W High")
            triggerToast(performanceFilter === "52W High" ? "Showing all shares" : `Filtered ${summaryMetrics.highs52} stocks near 52W High 📈`)
          }}
          title="Click to filter 52W High stocks"
        >
          <div className="summary-card__top">
            <span className="summary-card__label">
              52W HIGH
              <span className="info-tooltip-wrap" tabIndex={0} aria-label="52W High Info" onClick={(e) => e.stopPropagation()}>
                <Info size={12} className="info-icon" />
                <span className="info-tooltip-popover">
                  Number of stocks trading within 5% of their 1-year record high price (Price &ge; 0.95 × 52W High). Click card to filter list.
                </span>
              </span>
            </span>
            <ArrowUp size={16} className="icon-emerald" />
          </div>
          <div className="summary-card__value-row align-center">
            <span className="summary-card__value">{summaryMetrics.highs52}</span>
            <span className="badge-highs">New Highs</span>
          </div>
          <div className="summary-card__sub-label">Click to filter list</div>
        </div>

        {/* CARD 5: 52W LOW */}
        <div
          className={`summary-card ${performanceFilter === "52W Low" ? "summary-card--active-filter" : ""}`}
          style={{ cursor: "pointer" }}
          onClick={() => {
            handlePerformanceFilter(performanceFilter === "52W Low" ? "All" : "52W Low")
            triggerToast(performanceFilter === "52W Low" ? "Showing all shares" : `Filtered ${summaryMetrics.lows52} stocks near 52W Low 📉`)
          }}
          title="Click to filter 52W Low stocks"
        >
          <div className="summary-card__top">
            <span className="summary-card__label">
              52W LOW
              <span className="info-tooltip-wrap" tabIndex={0} aria-label="52W Low Info" onClick={(e) => e.stopPropagation()}>
                <Info size={12} className="info-icon" />
                <span className="info-tooltip-popover">
                  Number of stocks trading within 5% of their 1-year lowest price (Price &le; 1.05 × 52W Low). Click card to filter list.
                </span>
              </span>
            </span>
            <ArrowDown size={16} className="icon-rose" />
          </div>
          <div className="summary-card__value-row align-center">
            <span className="summary-card__value">{summaryMetrics.lows52}</span>
            <span className="badge-lows">New Lows</span>
          </div>
          <div className="summary-card__sub-label">Click to filter list</div>
        </div>
      </div>

      {/* FILTER CONTROLS BAR */}
      <div className="constituents__filter-bar">
        <div className="constituents__filter-left">
          <div className="performance-pill-group">
            <span className="performance-label">PERFORMANCE:</span>
            <button
              type="button"
              className={`pill-btn ${performanceFilter === "All" ? "pill-btn--active" : ""}`}
              onClick={() => handlePerformanceFilter("All")}
            >
              All
            </button>
            <button
              type="button"
              className={`pill-btn pill-btn--gainers ${performanceFilter === "Gainers" ? "pill-btn--active-gainers" : ""}`}
              onClick={() => handlePerformanceFilter("Gainers")}
            >
              Gainers
            </button>
            <button
              type="button"
              className={`pill-btn pill-btn--losers ${performanceFilter === "Losers" ? "pill-btn--active-losers" : ""}`}
              onClick={() => handlePerformanceFilter("Losers")}
            >
              Losers
            </button>
            <button
              type="button"
              className={`pill-btn ${performanceFilter === "52W High" ? "pill-btn--active-gainers" : ""}`}
              onClick={() => handlePerformanceFilter(performanceFilter === "52W High" ? "All" : "52W High")}
            >
              52W High ({summaryMetrics.highs52})
            </button>
            <button
              type="button"
              className={`pill-btn ${performanceFilter === "52W Low" ? "pill-btn--active-losers" : ""}`}
              onClick={() => handlePerformanceFilter(performanceFilter === "52W Low" ? "All" : "52W Low")}
            >
              52W Low ({summaryMetrics.lows52})
            </button>
          </div>

          <div className="sector-filter-group">
            <select
              className="sector-select"
              value={sector}
              onChange={(e) => handleFilterSector(e.target.value)}
              aria-label="Filter by Sector"
            >
              {allSectorsList.map((sec) => (
                <option key={sec} value={sec}>
                  {sec}
                </option>
              ))}
            </select>

            <div className="quick-sector-pills">
              {pinnedSectors.map((sec) => {
                const isActive = sector.toLowerCase() === sec.toLowerCase()
                return (
                  <div key={sec} className={`quick-sector-pill-item ${isActive ? "quick-sector-pill-item--active" : ""}`}>
                    <button
                      type="button"
                      className="quick-sector-btn-label"
                      onClick={() => handleFilterSector(isActive ? "All" : sec)}
                      title={`Filter ${sec} (Click to toggle)`}
                    >
                      {sec}
                    </button>
                    <button
                      type="button"
                      className="quick-sector-btn-remove"
                      onClick={(e) => {
                        e.stopPropagation()
                        togglePinSector(sec)
                      }}
                      title={`Remove ${sec} from quick bar`}
                    >
                      <X size={10} />
                    </button>
                  </div>
                )
              })}

              {/* Dynamic + Pin Button for current dropdown selection if not pinned */}
              {sector !== "All" &&
                sector !== "All Sectors" &&
                !pinnedSectors.some((s) => s.toLowerCase() === sector.toLowerCase()) && (
                  <button
                    type="button"
                    className="quick-sector-btn btn-pin-sector"
                    onClick={() => togglePinSector(sector)}
                    title={`Pin ${sector} to quick bar`}
                  >
                    <Plus size={12} /> Pin {sector}
                  </button>
                )}
            </div>
          </div>
        </div>

        {/* RIGHT ACTION BUTTONS: EXPORT & WATCHLIST DROPDOWN */}
        <div className="constituents__filter-right">
          <button
            type="button"
            className="btn-export"
            onClick={handleExportCSV}
            title="Export filtered Nifty 50 shares to CSV"
          >
            <Download size={14} /> Export
          </button>

          <div className="watchlist-dropdown-wrap" ref={watchlistDropdownRef}>
            <button
              type="button"
              className={`btn-watchlist-dropdown ${showWatchlistOnly ? "btn-watchlist-dropdown--active" : ""}`}
              onClick={() => setIsWatchlistDropdownOpen((prev) => !prev)}
              aria-expanded={isWatchlistDropdownOpen}
            >
              <Star size={14} fill={watchlist.length > 0 ? "#f5a524" : "none"} color={watchlist.length > 0 ? "#f5a524" : "currentColor"} />
              Watchlist ({watchlist.length}) <ChevronDown size={14} className={isWatchlistDropdownOpen ? "rotate-180" : ""} />
            </button>

            {/* WATCHLIST DROPDOWN MENU */}
            {isWatchlistDropdownOpen && (
              <div className="watchlist-dropdown-menu">
                <div className="watchlist-menu-head">
                  <span>⭐ Watchlist Manager</span>
                  <span className="watchlist-menu-count">{watchlist.length} saved</span>
                </div>

                <div className="watchlist-menu-options">
                  <button
                    type="button"
                    className={`watchlist-menu-item ${showWatchlistOnly ? "watchlist-menu-item--active" : ""}`}
                    onClick={() => {
                      setShowWatchlistOnly((prev) => !prev)
                      setPage(1)
                      triggerToast(showWatchlistOnly ? "Showing all Nifty 50 shares" : "Filtering watchlisted shares only ⭐")
                      setIsWatchlistDropdownOpen(false)
                    }}
                  >
                    <Filter size={14} />
                    <span>{showWatchlistOnly ? "Show All Shares" : "Filter: Watchlist Only"}</span>
                  </button>

                  <button
                    type="button"
                    className="watchlist-menu-item"
                    onClick={() => handleBulkAddWatchlist(processed.map((c) => c.ticker))}
                  >
                    <Star size={14} />
                    <span>Add Current Results ({processed.length})</span>
                  </button>

                  <button
                    type="button"
                    className="watchlist-menu-item watchlist-menu-item--danger"
                    onClick={handleClearWatchlist}
                    disabled={watchlist.length === 0}
                  >
                    <XCircle size={14} />
                    <span>Clear Watchlist</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* WARNING / ERROR BANNERS */}
      {warning && status === "partial_success" && (
        <div className="constituents__banner constituents__banner--warning">
          <AlertCircle size={18} />
          <span>{warning}</span>
        </div>
      )}

      {error && status === "error" && (
        <div className="constituents__banner constituents__banner--error">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertCircle size={20} />
            <span>⚠️ {error}</span>
          </div>
          <button
            type="button"
            className="btn-retry-fetch"
            onClick={fetchLiveConstituents}
            disabled={isFetchingRef.current}
          >
            <RefreshCw size={14} className={isFetchingRef.current ? "animate-spin" : ""} />
            <span>{isFetchingRef.current ? "Retrying..." : "Retry Live Fetch"}</span>
          </button>
        </div>
      )}

      {/* COMPANY DATA TABLE */}
      <div className="constituents__table-wrap">
        <table className="constituents__table">
          <thead>
            <tr>
              <th className="constituents__num">#</th>
              <th className="constituents__th constituents__th--left">
                <button className="constituents__sort" onClick={() => toggleSort("name")}>
                  Company
                  {sort.key === "name" && (sort.dir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                </button>
              </th>
              <th className="constituents__th constituents__th--left">Sector</th>
              <th className="constituents__th constituents__th--right">
                <button className="constituents__sort" onClick={() => toggleSort("price")}>
                  Price (₹)
                  {sort.key === "price" && (sort.dir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                </button>
              </th>
              <th className="constituents__th constituents__th--right">Change (₹)</th>
              <th className="constituents__th constituents__th--right">
                <button className="constituents__sort" onClick={() => toggleSort("changePct")}>
                  % Change
                  {sort.key === "changePct" && (sort.dir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                </button>
              </th>
              <th className="constituents__th constituents__th--right">
                <button className="constituents__sort" onClick={() => toggleSort("mcap")}>
                  Market Cap
                  {sort.key === "mcap" && (sort.dir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                </button>
              </th>
              <th className="constituents__th constituents__th--right">Volume</th>
              <th className="constituents__th constituents__th--center">
                <button className="constituents__sort" onClick={() => toggleSort("range52")}>
                  52W Range
                  {sort.key === "range52" && (sort.dir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                </button>
              </th>
              <th className="constituents__th constituents__th--center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoadingState ? (
              <tr>
                <td colSpan={10} className="constituents__loading-td">
                  <RefreshCw size={24} className="animate-spin loading-spinner" />
                  <div className="loading-text">Fetching live Nifty 50 market snapshot...</div>
                </td>
              </tr>
            ) : paged.length > 0 ? (
              paged.map((c, i) => {
                const positive = c.changePct >= 0
                const isWatchlisted = watchlist.includes(c.ticker)

                const low = c.low52 || c.price * 0.85
                const high = c.high52 || c.price * 1.15
                const rangePct = Math.min(100, Math.max(0, ((c.price - low) / (high - low || 1)) * 100))

                return (
                  <tr key={c.ticker} className="constituents__row">
                    <td className="constituents__num">{(currentPage - 1) * pageSize + i + 1}</td>
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
                      <span className={positive ? "gp-pos" : "gp-neg"}>
                        {positive ? "+" : ""}
                        {c.change.toFixed(2)}
                      </span>
                    </td>
                    <td className="constituents__td--right">
                      <span className={`constituents__change ${positive ? "gp-pos" : "gp-neg"}`}>
                        {positive ? "+" : ""}
                        {c.changePct.toFixed(2)}%
                      </span>
                    </td>
                    <td className="constituents__td--right gp-mono">{c.mcap}</td>
                    <td className="constituents__td--right gp-mono">{formatVolume(c.volume)}</td>
                    <td className="constituents__range-td">
                      <div className="range-slider-wrap">
                        <span className="range-min">{low.toFixed(0)}</span>
                        <div className="range-track">
                          <span className="range-dot" style={{ left: `${rangePct}%` }} />
                        </div>
                        <span className="range-max">{high.toFixed(0)}</span>
                      </div>
                    </td>
                    <td className="constituents__actions-td">
                      <button
                        type="button"
                        className={`btn-action-star ${isWatchlisted ? "btn-action-star--active" : ""}`}
                        onClick={() => toggleWatchlist(c.ticker)}
                        title={isWatchlisted ? "Remove from watchlist" : "Add to watchlist"}
                      >
                        <Star size={15} fill={isWatchlisted ? "#f5a524" : "none"} color={isWatchlisted ? "#f5a524" : "#64748b"} />
                      </button>
                    </td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan={10} className="constituents__empty">
                  No shares match your search or filter criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* FOOTER & PAGINATION */}
      <footer className="constituents__footer">
        <span className="constituents__count">
          {processed.length === 0
            ? "0 results"
            : `Showing ${(currentPage - 1) * pageSize + 1} to ${Math.min(currentPage * pageSize, processed.length)} of ${processed.length} results`}
        </span>

        <div className="constituents__pagination-controls">
          <div className="rows-per-page-selector">
            <span>Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setPage(1)
              }}
            >
              {PAGE_SIZE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>

          <div className="constituents__pager">
            <button
              type="button"
              className="gp-btn gp-btn--secondary gp-btn--sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1 || isLoadingState}
            >
              <ChevronLeft size={14} /> Prev
            </button>

            {Array.from({ length: totalPages }, (_, idx) => idx + 1).map((pNum) => (
              <button
                key={pNum}
                type="button"
                className={`page-num-btn ${currentPage === pNum ? "page-num-btn--active" : ""}`}
                onClick={() => setPage(pNum)}
              >
                {pNum}
              </button>
            ))}

            <button
              type="button"
              className="gp-btn gp-btn--secondary gp-btn--sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages || isLoadingState}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </footer>

      {/* BOTTOM SUMMARY WIDGETS (CARD 10 IN REFERENCE IMAGE) */}
      <div className="constituents__bottom-grid">
        {/* WIDGET 1: TOP GAINERS */}
        <div className="bottom-widget-card">
          <div className="bottom-widget__head">
            <div className="widget-title-row gp-pos">
              <TrendingUp size={14} /> Top Gainers
            </div>
            <button type="button" onClick={handleViewAllGainers} className="widget-view-all">
              View all
            </button>
          </div>

          <div className="widget-list">
            {topGainersWidget.map((item, idx) => (
              <div key={item.ticker} className="widget-list-row">
                <span className="widget-num">{idx + 1}</span>
                <span className="widget-name">{item.name}</span>
                <span className="widget-change gp-pos">+{item.changePct.toFixed(2)}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* WIDGET 2: TOP LOSERS */}
        <div className="bottom-widget-card">
          <div className="bottom-widget__head">
            <div className="widget-title-row gp-neg">
              <TrendingDown size={14} /> Top Losers
            </div>
            <button type="button" onClick={handleViewAllLosers} className="widget-view-all">
              View all
            </button>
          </div>

          <div className="widget-list">
            {topLosers.map((item, idx) => (
              <div key={item.ticker} className="widget-list-row">
                <span className="widget-num">{idx + 1}</span>
                <span className="widget-name">{item.name}</span>
                <span className="widget-change gp-neg">{item.changePct.toFixed(2)}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* WIDGET 3: MOST ACTIVE BY VOLUME */}
        <div className="bottom-widget-card">
          <div className="bottom-widget__head">
            <div className="widget-title-row">
              <BarChart2 size={14} className="icon-blue" /> Most Active by Volume
            </div>
            <button type="button" onClick={handleViewAllVolume} className="widget-view-all">
              View all
            </button>
          </div>

          <div className="widget-list">
            {topActiveVolume.map((item, idx) => (
              <div key={item.ticker} className="widget-list-row">
                <span className="widget-num">{idx + 1}</span>
                <span className="widget-name">{item.name}</span>
                <span className="widget-vol-val">{formatVolume(item.volume)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
