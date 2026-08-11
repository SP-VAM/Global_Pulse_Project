import { useState, useEffect, useMemo, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Search, ArrowRight, BarChart3, RefreshCw } from "lucide-react"

import SummaryCard from "./components/SummaryCard.jsx"
import MarketOverviewCard from "./components/MarketOverviewCard.jsx"
import CompanyCard from "./components/CompanyCard.jsx"
import TopMovers from "./components/TopMovers.jsx"
import SectorCard from "./components/SectorCard.jsx"
import { useFlow } from "../../../App"
import { getMarketSnapshot } from "../../../api/marketApi.js"
import { getExpenseSummary } from "../../../api/expenseApi.js"

import {
  summaryCards,
  marketOverview,
  sectors,
  sparklines,
} from "../../../data/marketData.js"

import "./Dashboard.css"

export default function Dashboard() {
  const navigate = useNavigate()
  const { flow } = useFlow()
  const [query, setQuery] = useState("")

  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem("user")
      return saved ? JSON.parse(saved) : null
    } catch (e) {
      return null
    }
  })

  // Live Market Snapshot State
  const [liveMarketItems, setLiveMarketItems] = useState([])
  const [loadingMarket, setLoadingMarket] = useState(true)
  const [marketError, setMarketError] = useState(null)

  const fetchLiveSnapshot = async () => {
    setLoadingMarket(true)
    setMarketError(null)
    try {
      const res = await getMarketSnapshot()
      if (res && res.items && res.items.length > 0) {
        setLiveMarketItems(res.items)
      } else {
        setMarketError("Live market data unavailable")
        setLiveMarketItems([])
      }
    } catch (err) {
      console.error("[Dashboard] Live market snapshot fetch error:", err)
      setMarketError("Live market data unavailable")
      setLiveMarketItems([])
    } finally {
      setLoadingMarket(false)
    }
  }

  useEffect(() => {
    fetchLiveSnapshot()
  }, [])

  useEffect(() => {
    function refreshUser() {
      try {
        const saved = localStorage.getItem("user")
        if (saved) setCurrentUser(JSON.parse(saved))
      } catch (e) {
        console.error("Failed to refresh user in Dashboard", e)
      }
    }
    refreshUser()
    window.addEventListener("user-updated", refreshUser)
    window.addEventListener("storage", refreshUser)
    return () => {
      window.removeEventListener("user-updated", refreshUser)
      window.removeEventListener("storage", refreshUser)
    }
  }, [])

  // Live Expense Summary State
  const [expenseSummary, setExpenseSummary] = useState(null)

  const fetchExpenseSummary = useCallback(async () => {
    try {
      const now = new Date()
      const res = await getExpenseSummary(now.getFullYear(), now.getMonth() + 1)
      if (res) {
        setExpenseSummary(res)
      }
    } catch (err) {
      console.error("[Dashboard] Expense summary fetch error:", err)
    }
  }, [])

  useEffect(() => {
    fetchExpenseSummary()
    window.addEventListener("expense-updated", fetchExpenseSummary)
    window.addEventListener("focus", fetchExpenseSummary)
    return () => {
      window.removeEventListener("expense-updated", fetchExpenseSummary)
      window.removeEventListener("focus", fetchExpenseSummary)
    }
  }, [fetchExpenseSummary])

  const liveSummaryCards = useMemo(() => {
    if (!expenseSummary) return summaryCards

    const spending = expenseSummary.monthlySpending || 0
    const income = expenseSummary.monthlyIncome || 0
    const savings = expenseSummary.savings || 0
    const totalBudget = (expenseSummary.budgets || []).reduce((acc, b) => acc + (b.budgetAmount || 0), 0)
    const remainingBudget = totalBudget > 0 ? (totalBudget - spending) : 0

    const formatVal = (num) => "₹" + Math.round(num).toLocaleString("en-IN")

    return [
      {
        id: "spending",
        label: "Monthly Spending",
        value: formatVal(spending),
        change: spending > 0 ? "Logged" : "₹0 spent",
        positive: false,
        icon: "Wallet",
        tone: "blue",
      },
      {
        id: "income",
        label: "Income",
        value: formatVal(income),
        change: income > 0 ? "Logged" : "₹0 logged",
        positive: true,
        icon: "TrendingUp",
        tone: "green",
      },
      {
        id: "budget",
        label: "Remaining Budget",
        value: formatVal(remainingBudget),
        change: totalBudget === 0 ? "No budget set" : remainingBudget >= 0 ? "In budget" : "Over budget",
        positive: remainingBudget >= 0,
        icon: "PieChart",
        tone: remainingBudget >= 0 ? "amber" : "red",
      },
      {
        id: "savings",
        label: "Savings",
        value: formatVal(savings),
        change: savings >= 0 ? "Net positive" : "Deficit",
        positive: savings >= 0,
        icon: "PiggyBank",
        tone: "green",
      },
    ]
  }, [expenseSummary])

  const greetingName =
    currentUser?.full_name ||
    currentUser?.firstName ||
    currentUser?.username ||
    flow?.username ||
    "Investor"

  const displayCompanies = useMemo(() => {
    if (!liveMarketItems || liveMarketItems.length === 0) return []
    return liveMarketItems.map((item) => {
      const priceVal = item.current_price ?? item.previous_close ?? 0
      const changePct = item.change_percent ?? 0
      const positive = changePct >= 0
      const series = item.price_history ? item.price_history.map((p) => p.close || 0) : []
      return {
        id: item.symbol.toLowerCase(),
        name: item.company_name,
        ticker: item.symbol,
        price: `₹${priceVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
        change: `${positive ? "+" : ""}${changePct.toFixed(2)}%`,
        positive,
        series,
      }
    })
  }, [liveMarketItems])

  const CARDS_PER_PAGE = 4
  const ROTATE_INTERVAL_MS = 8000

  const [carouselIndex, setCarouselIndex] = useState(0)
  const [carouselVisible, setCarouselVisible] = useState(true)
  const isHovering = useRef(false)
  const timerRef = useRef(null)

  const totalCarouselPages = displayCompanies.length > 0
    ? Math.ceil(displayCompanies.length / CARDS_PER_PAGE)
    : 0

  const advanceCarousel = useCallback(() => {
    if (isHovering.current) return
    setCarouselVisible(false)
    setTimeout(() => {
      setCarouselIndex((prev) =>
        totalCarouselPages > 0 ? (prev + 1) % totalCarouselPages : 0
      )
      setCarouselVisible(true)
    }, 350)
  }, [totalCarouselPages])

  useEffect(() => {
    if (query.trim() || displayCompanies.length === 0) {
      clearInterval(timerRef.current)
      return
    }
    timerRef.current = setInterval(advanceCarousel, ROTATE_INTERVAL_MS)
    return () => clearInterval(timerRef.current)
  }, [advanceCarousel, query, displayCompanies.length])

  const filtered = useMemo(() => {
    if (query.trim()) {
      const q = query.toLowerCase()
      return displayCompanies.filter(
        (c) => c.name.toLowerCase().includes(q) || c.ticker.toLowerCase().includes(q)
      )
    }
    const start = carouselIndex * CARDS_PER_PAGE
    return displayCompanies.slice(start, start + CARDS_PER_PAGE)
  }, [displayCompanies, query, carouselIndex])

  const displayTopMovers = useMemo(() => {
    if (!liveMarketItems || liveMarketItems.length === 0) return []
    const sorted = [...liveMarketItems]
      .sort((a, b) => Math.abs(b.change_percent ?? 0) - Math.abs(a.change_percent ?? 0))
      .slice(0, 4)
    return sorted.map((item) => {
      const priceVal = item.current_price ?? item.previous_close ?? 0
      const changePct = item.change_percent ?? 0
      const positive = changePct >= 0
      return {
        id: item.symbol.toLowerCase(),
        name: item.company_name ? item.company_name.split(" ")[0] : item.symbol,
        ticker: item.symbol,
        value: priceVal.toLocaleString("en-IN", { minimumFractionDigits: 2 }),
        change: `${positive ? "+" : ""}${changePct.toFixed(2)}%`,
        positive,
      }
    })
  }, [liveMarketItems])

  return (
    <div className="dashboard-home">
      {/* Greeting */}
      <header className="dashboard__greeting">
        <h1 className="dashboard__hello">
          Hello, {greetingName} <span aria-hidden="true">&#128075;</span>
        </h1>
        <p className="dashboard__welcome">Welcome back! Here&apos;s today&apos;s market overview.</p>
      </header>

      {/* Compact summary cards + market overview */}
      <section className="dashboard__summary" aria-label="Financial summary">
        {liveSummaryCards.map((item, i) => (
          <SummaryCard key={item.id} item={item} style={{ animationDelay: `${i * 60}ms` }} />
        ))}
        <MarketOverviewCard data={marketOverview} style={{ animationDelay: `${liveSummaryCards.length * 60}ms` }} />
      </section>

      {/* Company intelligence */}
      <section className="dashboard__intel">
        <div className="dashboard__intel-head">
          <div>
            <h2 className="gp-section-title">Company Intelligence</h2>
            <p className="gp-section-sub">Deep-dive analysis of individual Nifty 50 constituents.</p>
          </div>
          <div className="dashboard__search">
            <Search size={16} className="dashboard__search-icon" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search Nifty 50 companies..."
              aria-label="Search Nifty 50 companies"
            />
          </div>
        </div>

        <div className="dashboard__intel-grid">
          <div
            className="dashboard__companies"
            onMouseEnter={() => { isHovering.current = true }}
            onMouseLeave={() => { isHovering.current = false }}
          >
            {loadingMarket ? (
              <div style={{ textAlign: "center", padding: "40px", color: "#94a3b8", gridColumn: "1 / -1" }}>
                <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 12px auto", display: "block" }} />
                <div>Fetching live market snapshot...</div>
              </div>
            ) : marketError ? (
              <div style={{ textAlign: "center", padding: "40px", color: "#f87171", gridColumn: "1 / -1" }}>
                <div>⚠️ {marketError}</div>
                <button onClick={fetchLiveSnapshot} style={{ marginTop: 12, padding: "6px 16px", borderRadius: 6, background: "#1e293b", color: "#fff", border: "1px solid #334155", cursor: "pointer" }}>
                  Retry Live Fetch
                </button>
              </div>
            ) : filtered.length > 0 ? (
              <div
                className="dashboard__carousel-wrap"
                style={{
                  opacity: carouselVisible ? 1 : 0,
                  transform: carouselVisible ? "translateY(0)" : "translateY(10px)",
                  transition: "opacity 0.35s ease, transform 0.35s ease",
                  display: "contents",
                }}
              >
                {filtered.map((c, i) => (
                  <CompanyCard
                    key={c.id + "-" + carouselIndex + "-" + i}
                    company={c}
                    series={c.series && c.series.length > 0 ? c.series : (sparklines[c.id] || sparklines[c.ticker])}
                    style={{ animationDelay: `${i * 70}ms` }}
                  />
                ))}
              </div>
            ) : (
              <p className="dashboard__empty">No companies match &ldquo;{query}&rdquo;.</p>
            )}
          </div>

          <div className="dashboard__movers-col">
            {loadingMarket ? (
              <div style={{ textAlign: "center", padding: "30px", color: "#94a3b8", background: "#1e293b", borderRadius: "12px" }}>
                <RefreshCw size={20} className="animate-spin" style={{ margin: "0 auto 8px auto", display: "block" }} />
                <div>Loading top movers...</div>
              </div>
            ) : marketError ? (
              <div style={{ textAlign: "center", padding: "30px", color: "#f87171", background: "#1e293b", borderRadius: "12px" }}>
                <div>⚠️ Top movers unavailable</div>
              </div>
            ) : (
              <TopMovers movers={displayTopMovers} style={{ animationDelay: "120ms" }} />
            )}

            {!loadingMarket && !marketError && !query.trim() && totalCarouselPages > 1 && (
              <div className="dashboard__carousel-dots">
                {Array.from({ length: totalCarouselPages }).map((_, idx) => (
                  <button
                    key={idx}
                    className={`dashboard__carousel-dot${idx === carouselIndex ? " dashboard__carousel-dot--active" : ""}`}
                    onClick={() => { setCarouselVisible(false); setTimeout(() => { setCarouselIndex(idx); setCarouselVisible(true) }, 350) }}
                    aria-label={`Go to page ${idx + 1}`}
                  />
                ))}
              </div>
            )}

            <button
              className="dashboard__viewall-btn"
              onClick={() => navigate("/dashboard/constituents")}
            >
              View All Companies
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </section>

      {/* Affected sectors */}
      <section className="dashboard__sectors" aria-label="Affected sectors">
        <h3 className="gp-section-title dashboard__sectors-title">
          <BarChart3 size={18} className="dashboard__sectors-icon" /> Affected Sectors 2000 &ndash; 2026
        </h3>
        <div className="dashboard__sectors-grid">
          {sectors.map((s, i) => (
            <SectorCard key={s.id} sector={s} style={{ animationDelay: `${i * 60}ms` }} />
          ))}
        </div>
      </section>
    </div>
  )
}
