import { useState, useEffect, useMemo, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Search, ArrowRight, BarChart3, RefreshCw } from "lucide-react"

import SummaryCard from "./components/SummaryCard.jsx"
import MarketOverviewCard from "./components/MarketOverviewCard.jsx"
import CompanyCard from "./components/CompanyCard.jsx"
import TopMovers from "./components/TopMovers.jsx"
import SectorCard from "./components/SectorCard.jsx"
import { useFlow } from "../../../App"
import { getMarketSnapshot, getTopMovers } from "../../../api/marketApi.js"
import { getExpenseSummary } from "../../../api/expenseApi.js"
import { fetchGoals } from "../../../api/goalsApi.js"

import {
  summaryCards,
  marketOverview,
  sectors,
  sparklines,
  constituents,
  topMovers,
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
  const [liveIndexQuote, setLiveIndexQuote] = useState(null)
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
      if (res && res.index_quote) {
        setLiveIndexQuote(res.index_quote)
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
    const timer = setInterval(() => {
      fetchLiveSnapshot()
    }, 30000)
    return () => clearInterval(timer)
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
    return () => {
      window.removeEventListener("expense-updated", fetchExpenseSummary)
    }
  }, [fetchExpenseSummary])

  // Live Financial Goals State
  const [goalsList, setGoalsList] = useState([])

  const fetchGoalsData = useCallback(async () => {
    try {
      const res = await fetchGoals()
      if (Array.isArray(res)) {
        setGoalsList(res)
      } else if (res && Array.isArray(res.goals)) {
        setGoalsList(res.goals)
      }
    } catch (err) {
      console.warn("[Dashboard] Goals fetch error:", err)
    }
  }, [])

  useEffect(() => {
    fetchGoalsData()
    window.addEventListener("goals-updated", fetchGoalsData)
    return () => {
      window.removeEventListener("goals-updated", fetchGoalsData)
    }
  }, [fetchGoalsData])

  // Live Top Movers State
  const [topMoversData, setTopMoversData] = useState(null)
  const [loadingMovers, setLoadingMovers] = useState(true)
  const [moversError, setMoversError] = useState(null)

  const fetchLiveTopMovers = useCallback(async () => {
    setLoadingMovers(true)
    setMoversError(null)
    try {
      const res = await getTopMovers(5)
      if (res && res.movers) {
        setTopMoversData(res)
      } else {
        setMoversError("Market data unavailable")
        setTopMoversData(null)
      }
    } catch (err) {
      console.error("[Dashboard] Top movers fetch error:", err)
      setMoversError("Market data unavailable")
      setTopMoversData(null)
    } finally {
      setLoadingMovers(false)
    }
  }, [])

  useEffect(() => {
    fetchLiveTopMovers()
  }, [fetchLiveTopMovers])

  // Learning Hub Last Active Module State
  const [lastModule, setLastModule] = useState(() => {
    try {
      const saved = localStorage.getItem("recent_learning_modules_v3")
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed) && parsed.length > 0) return parsed[0]
      }
      const prog = localStorage.getItem("lh_user_video_progress_v1")
      if (prog) {
        const parsedProg = JSON.parse(prog)
        const keys = Object.keys(parsedProg)
        if (keys.length > 0) {
          const lastKey = keys[keys.length - 1]
          return {
            title: `Module ${lastKey}`,
            progressPercentage: parsedProg[lastKey]?.progressPercentage,
          }
        }
      }
      return null
    } catch {
      return null
    }
  })

  // Summary Row: Cards 2 to 5 (Card 1 is MarketOverviewCard)
  const liveSummaryCards = useMemo(() => {
    const now = new Date()
    const currentMonthName = now.toLocaleString("en-US", { month: "long" })

    // CARD 2: Expense Tracker - That Month Net Savings
    const savings = expenseSummary ? expenseSummary.savings : null
    const hasExpenseActivity =
      expenseSummary &&
      (Number(expenseSummary.monthlyIncome) > 0 ||
        Number(expenseSummary.monthlySpending) > 0 ||
        Number(expenseSummary.savings) !== 0)

    const formatINRVal = (num) => {
      if (num === null || num === undefined) return "₹0"
      return "₹" + Math.round(num).toLocaleString("en-IN")
    }

    const netSavingsCard = {
      id: "net-savings",
      label: `Net Savings (${currentMonthName})`,
      value: expenseSummary ? formatINRVal(savings) : "₹0",
      change: hasExpenseActivity
        ? savings >= 0
          ? "Net positive"
          : "Deficit"
        : "Add your expense",
      positive: hasExpenseActivity ? savings >= 0 : null,
      icon: "PiggyBank",
      tone: "green",
      onClick: () => navigate("/dashboard/expense-tracker"),
    }

    // CARD 3: Goal Progress Percentage
    const hasGoals = Array.isArray(goalsList) && goalsList.length > 0
    let goalProgressPct = 0
    if (hasGoals) {
      const totalProgress = goalsList.reduce(
        (acc, g) => acc + (Number(g.current || g.current_quantity) || 0),
        0
      )
      const totalTarget = goalsList.reduce(
        (acc, g) => acc + (Number(g.target || g.target_quantity) || 0),
        0
      )
      goalProgressPct =
        totalTarget > 0 ? Math.min(100, Math.round((totalProgress / totalTarget) * 100)) : 0
    }

    const goalCard = {
      id: "goals",
      label: "Goal Progress",
      value: hasGoals ? `${goalProgressPct}%` : "0%",
      change: hasGoals
        ? `${goalsList.length} Active ${goalsList.length === 1 ? "Goal" : "Goals"}`
        : "Add your goal",
      positive: hasGoals ? goalProgressPct > 0 : null,
      icon: "Target",
      tone: "blue",
      onClick: () => navigate("/dashboard/goals"),
    }

    // CARD 4: Top Movers (India)
    const topMover = topMoversData && topMoversData.movers && topMoversData.movers.length > 0 ? topMoversData.movers[0] : null
    const topMoverSym = topMover ? topMover.symbol : ""
    const topMoverPct = topMover ? topMover.change_percent : 0
    const isTopPos = topMoverPct >= 0

    const topMoversCard = {
      id: "top-movers-india",
      label: "Top Movers (India)",
      value: topMover ? `${topMoverSym}` : "No Movers",
      change: topMover
        ? `${isTopPos ? "+" : ""}${topMoverPct.toFixed(2)}% (${topMover.company_name ? topMover.company_name.split(" ")[0] : topMoverSym})`
        : moversError || "Market Snapshot",
      positive: topMover ? isTopPos : null,
      icon: "Activity",
      tone: topMover ? (isTopPos ? "green" : "red") : "blue",
      onClick: () => {
        if (topMoverSym) {
          navigate(`/dashboard/market-analysis?symbol=${encodeURIComponent(topMoverSym)}`)
        } else {
          navigate("/dashboard/market-analysis")
        }
      },
    }

    // CARD 5: Learning Hub (Last Active Module)
    const hasLearning = lastModule && (lastModule.title || lastModule.name)
    const learningCard = {
      id: "learning-hub",
      label: "Learning Hub",
      value: hasLearning
        ? lastModule.title || lastModule.name
        : "Learn something new",
      change: hasLearning
        ? `${lastModule.progressPercentage || 25}% completed`
        : "Start learning",
      positive: hasLearning ? true : null,
      icon: "GraduationCap",
      tone: "purple",
      onClick: () => navigate("/dashboard/learning-hub"),
    }

    return [netSavingsCard, goalCard, topMoversCard, learningCard]
  }, [expenseSummary, goalsList, topMoversData, moversError, lastModule, navigate])

  const greetingName =
    currentUser?.full_name ||
    currentUser?.firstName ||
    currentUser?.username ||
    flow?.username ||
    "Investor"

  const displayCompanies = useMemo(() => {
    const sourceList = (liveMarketItems && liveMarketItems.length > 0)
      ? liveMarketItems
      : constituents
    if (!sourceList || sourceList.length === 0) return []
    return sourceList.map((item) => {
      const priceVal = item.current_price ?? item.previous_close ?? item.price ?? 0
      const changePct = item.change_percent ?? item.change ?? 0
      const positive = changePct >= 0
      const sym = (item.symbol || item.ticker || "").replace(".NS", "").toUpperCase()
      const compName = item.company_name || item.name || sym

      const rawHistory = item.price_history || []
      const validHistory = Array.isArray(rawHistory)
        ? rawHistory.filter(
            (p) => p && typeof p.close === "number" && !isNaN(p.close) && isFinite(p.close) && p.close > 0
          )
        : []

      const fallbackSpark = sparklines[sym.toLowerCase()] || sparklines[sym] || [10, 25, 40, 35, 60, 80]
      const series = validHistory.length > 0 ? validHistory.map((p) => p.close) : fallbackSpark

      return {
        id: sym.toLowerCase(),
        name: compName,
        ticker: sym,
        price: typeof priceVal === "number" ? `₹${priceVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : priceVal,
        change: `${positive ? "+" : ""}${typeof changePct === "number" ? changePct.toFixed(2) : changePct}%`,
        positive,
        series,
        price_history: validHistory,
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
    const q = query.trim().toLowerCase()
    if (q) {
      return displayCompanies.filter(
        (c) =>
          (c.name && c.name.toLowerCase().includes(q)) ||
          (c.ticker && c.ticker.toLowerCase().includes(q))
      )
    }
    const start = carouselIndex * CARDS_PER_PAGE
    return displayCompanies.slice(start, start + CARDS_PER_PAGE)
  }, [displayCompanies, query, carouselIndex])


  const displayTopMovers = useMemo(() => {
    if (liveMarketItems && liveMarketItems.length > 0) {
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
          value: typeof priceVal === "number" ? priceVal.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : priceVal,
          change: `${positive ? "+" : ""}${typeof changePct === "number" ? changePct.toFixed(2) : changePct}%`,
          positive,
        }
      })
    }
    return topMovers || []
  }, [liveMarketItems])

  const marketOverviewData = useMemo(() => {
    if (liveIndexQuote && liveIndexQuote.current_price) {
      const p = liveIndexQuote.current_price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      const chg = liveIndexQuote.change >= 0 ? `+${liveIndexQuote.change.toFixed(2)}` : liveIndexQuote.change.toFixed(2)
      const pct = liveIndexQuote.change_percent >= 0 ? `+${liveIndexQuote.change_percent.toFixed(2)}%` : `${liveIndexQuote.change_percent.toFixed(2)}%`
      return {
        status: liveIndexQuote.is_live ? "OPEN" : "CLOSED",
        indices: [
          {
            label: "NIFTY 50",
            value: p,
            change: `${chg} (${pct})`,
            positive: liveIndexQuote.change >= 0,
            data_state: liveIndexQuote.data_state,
          }
        ]
      }
    }
    return marketOverview
  }, [liveIndexQuote])

  return (
    <div className="dashboard-home">
      {/* Greeting */}
      <header className="dashboard__greeting">
        <h1 className="dashboard__hello">
          Hello, {greetingName} <span aria-hidden="true">&#128075;</span>
        </h1>
        <p className="dashboard__welcome">Welcome back! Here&apos;s today&apos;s market overview.</p>
      </header>

      {/* 5 Summary Cards: 1. Market Overview -> 2. Net Savings -> 3. Goal Progress -> 4. Live News & Sentiment -> 5. Learning Hub */}
      <section className="dashboard__summary" aria-label="Financial summary">
        {/* CARD 1: Market Overview (Navigates to 50 Companies) */}
        <MarketOverviewCard
          data={marketOverviewData}
          style={{ animationDelay: "0ms" }}
          onClick={() => navigate("/dashboard/constituents")}
        />

        {/* CARDS 2 to 5 */}
        {liveSummaryCards.map((item, i) => (
          <SummaryCard
            key={item.id}
            item={item}
            style={{ animationDelay: `${(i + 1) * 60}ms` }}
            onClick={item.onClick}
          />
        ))}
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
            {filtered.length > 0 ? (
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
                    onClick={() => navigate(`/dashboard/market-analysis?symbol=${encodeURIComponent(c.ticker || c.symbol)}`)}
                  />
                ))}
              </div>
            ) : marketError && displayCompanies.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px", color: "#f87171", gridColumn: "1 / -1" }}>
                <div>⚠️ {marketError}</div>
                <button onClick={fetchLiveSnapshot} style={{ marginTop: 12, padding: "6px 16px", borderRadius: 6, background: "#1e293b", color: "#fff", border: "1px solid #334155", cursor: "pointer" }}>
                  Retry Live Fetch
                </button>
              </div>
            ) : (
              <p className="dashboard__empty">No companies match &ldquo;{query}&rdquo;.</p>
            )}
          </div>

          <div className="dashboard__movers-col">
            <TopMovers
              movers={topMoversData ? topMoversData.movers : displayTopMovers}
              asOfFormatted={topMoversData ? topMoversData.as_of_formatted : null}
              marketStatus={topMoversData ? topMoversData.market_status : null}
              isStale={topMoversData ? topMoversData.is_stale : false}
              loading={loadingMovers}
              error={moversError}
              onRetry={fetchLiveTopMovers}
              onViewAll={() => navigate("/dashboard/constituents")}
              style={{ animationDelay: "120ms" }}
            />

            {!query.trim() && totalCarouselPages > 1 && (
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
