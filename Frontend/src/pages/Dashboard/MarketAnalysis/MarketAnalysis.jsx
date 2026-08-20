import React, { useState, useMemo, useEffect, useRef } from "react"
import { useSearchParams } from "react-router-dom"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  ComposedChart,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ReferenceLine,
} from "recharts"
import {
  Search,
  Activity,
  TrendingUp,
  TrendingDown,
  BrainCircuit,
  Newspaper,
  BarChart2,
  AlertTriangle,
  Zap,
  BookOpen,
  RefreshCw,
} from "lucide-react"

import { getStockAnalysis, getSupportedCompanies, getStockSentiment } from "../../../api/marketApi.js"
import { DATE_RANGES } from "../../../data/marketAnalysisData.js"

import "./MarketAnalysis.css"

const RANGE_TO_PERIOD = {
  "1D": "1d",
  "1W": "5d",
  "5D": "5d",
  "1M": "1mo",
  "3M": "3mo",
  "6M": "6mo",
  "1Y": "1y",
  "5Y": "5y",
}

// Single Source of Truth Fallback matching backend TICKER_TO_COMPANY (Exactly 50 - No TATAMOTORS or LTIM)
const FALLBACK_NIFTY_COMPANIES = [
  { symbol: "ADANIENT", name: "Adani Enterprises Ltd" },
  { symbol: "ADANIPORTS", name: "Adani Ports & Special Economic Zone Ltd" },
  { symbol: "APOLLOHOSP", name: "Apollo Hospitals Enterprise Ltd" },
  { symbol: "ASIANPAINT", name: "Asian Paints Ltd" },
  { symbol: "AXISBANK", name: "Axis Bank Ltd" },
  { symbol: "BAJAJ-AUTO", name: "Bajaj Auto Ltd" },
  { symbol: "BAJFINANCE", name: "Bajaj Finance Ltd" },
  { symbol: "BAJAJFINSV", name: "Bajaj Finserv Ltd" },
  { symbol: "BEL", name: "Bharat Electronics Ltd" },
  { symbol: "BHARTIARTL", name: "Bharti Airtel Ltd" },
  { symbol: "BPCL", name: "Bharat Petroleum Corporation Ltd" },
  { symbol: "BRITANNIA", name: "Britannia Industries Ltd" },
  { symbol: "CIPLA", name: "Cipla Ltd" },
  { symbol: "COALINDIA", name: "Coal India Ltd" },
  { symbol: "DIVISLAB", name: "Divi's Laboratories Ltd" },
  { symbol: "DRREDDY", name: "Dr. Reddy's Laboratories Ltd" },
  { symbol: "EICHERMOT", name: "Eicher Motors Ltd" },
  { symbol: "ETERNAL", name: "Eternal Ltd" },
  { symbol: "GRASIM", name: "Grasim Industries Ltd" },
  { symbol: "HCLTECH", name: "HCL Technologies Ltd" },
  { symbol: "HDFCBANK", name: "HDFC Bank Ltd" },
  { symbol: "HDFCLIFE", name: "HDFC Life Insurance Ltd" },
  { symbol: "HEROMOTOCO", name: "Hero MotoCorp Ltd" },
  { symbol: "HINDALCO", name: "Hindalco Industries Ltd" },
  { symbol: "HINDUNILVR", name: "Hindustan Unilever Ltd" },
  { symbol: "ICICIBANK", name: "ICICI Bank Ltd" },
  { symbol: "INDUSINDBK", name: "IndusInd Bank Ltd" },
  { symbol: "INFY", name: "Infosys Ltd" },
  { symbol: "ITC", name: "ITC Ltd" },
  { symbol: "JIOFIN", name: "Jio Financial Services Ltd" },
  { symbol: "JSWSTEEL", name: "JSW Steel Ltd" },
  { symbol: "KOTAKBANK", name: "Kotak Mahindra Bank Ltd" },
  { symbol: "LT", name: "Larsen & Toubro Ltd" },
  { symbol: "M&M", name: "Mahindra & Mahindra Ltd" },
  { symbol: "MARUTI", name: "Maruti Suzuki India Ltd" },
  { symbol: "NESTLEIND", name: "Nestle India Ltd" },
  { symbol: "NTPC", name: "NTPC Ltd" },
  { symbol: "ONGC", name: "Oil & Natural Gas Corporation Ltd" },
  { symbol: "POWERGRID", name: "Power Grid Corporation of India Ltd" },
  { symbol: "RELIANCE", name: "Reliance Industries Ltd" },
  { symbol: "SBILIFE", name: "SBI Life Insurance Ltd" },
  { symbol: "SBIN", name: "State Bank of India" },
  { symbol: "SHRIRAMFIN", name: "Shriram Finance Ltd" },
  { symbol: "SUNPHARMA", name: "Sun Pharmaceutical Industries Ltd" },
  { symbol: "TATACONSUM", name: "Tata Consumer Products Ltd" },
  { symbol: "TATASTEEL", name: "Tata Steel Ltd" },
  { symbol: "TCS", name: "Tata Consultancy Services Ltd" },
  { symbol: "TECHM", name: "Tech Mahindra Ltd" },
  { symbol: "TITAN", name: "Titan Company Ltd" },
  { symbol: "TRENT", name: "Trent Ltd" },
  { symbol: "ULTRACEMCO", name: "UltraTech Cement Ltd" },
  { symbol: "WIPRO", name: "Wipro Ltd" },
]

const CandlestickBar = (props) => {
  const { x, y, width, height, payload, yAxis } = props
  if (!payload || !yAxis || typeof yAxis.scale !== "function") return null

  const open = payload.open ?? payload.price ?? 0
  const close = payload.close ?? payload.price ?? 0
  const high = payload.high ?? Math.max(open, close)
  const low = payload.low ?? Math.min(open, close)

  if (open === 0 && close === 0) return null

  const yOpen = yAxis.scale(open)
  const yClose = yAxis.scale(close)
  const yHigh = yAxis.scale(high)
  const yLow = yAxis.scale(low)

  const isBullish = close >= open
  const candleColor = isBullish ? "#22c55e" : "#ef4444"

  const bodyTop = Math.min(yOpen, yClose)
  const bodyHeight = Math.max(Math.abs(yClose - yOpen), 2)
  const barWidth = Math.max(Math.min(width * 0.72, 14), 3)
  const barX = x + (width - barWidth) / 2
  const wickX = x + width / 2

  return (
    <g className="candlestick-candle">
      {/* High-Low Wick Line */}
      <line
        x1={wickX}
        y1={yHigh}
        x2={wickX}
        y2={yLow}
        stroke={candleColor}
        strokeWidth={1.5}
        strokeLinecap="round"
      />
      {/* Open-Close Candle Body */}
      <rect
        x={barX}
        y={bodyTop}
        width={barWidth}
        height={bodyHeight}
        fill={candleColor}
        stroke={candleColor}
        strokeWidth={1}
        rx={1}
      />
    </g>
  )
}

const VolumeBar = (props) => {
  const { x, y, width, height, payload } = props
  if (!payload) return null
  const isBullish = (payload.close ?? payload.price ?? 0) >= (payload.open ?? payload.close ?? 0)
  const color = isBullish ? "#22c55e" : "#ef4444"
  return (
    <rect
      x={x}
      y={y}
      width={Math.max(width - 1, 1)}
      height={height}
      fill={color}
      opacity={0.45}
      rx={1}
    />
  )
}

const CustomOverviewTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0]?.payload || {}
    const isUp = (data.close ?? data.price ?? 0) >= (data.open ?? data.close ?? 0)
    const color = isUp ? "#22c55e" : "#ef4444"

    return (
      <div
        style={{
          background: "rgba(15, 23, 42, 0.95)",
          border: "1px solid rgba(255, 255, 255, 0.14)",
          borderRadius: "10px",
          padding: "12px 16px",
          color: "#ffffff",
          boxShadow: "0 10px 30px rgba(0,0,0,0.8)",
          backdropFilter: "blur(8px)",
          minWidth: 200,
        }}
      >
        <div style={{ fontWeight: "700", marginBottom: "8px", fontSize: "13.5px", color: "#f8fafc" }}>
          {label}
        </div>
        {data.open !== undefined && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", fontSize: "12px", marginBottom: "6px" }}>
            <div><span style={{ color: "#94a3b8" }}>O: </span><span style={{ fontWeight: 600 }}>₹{Number(data.open).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span></div>
            <div><span style={{ color: "#94a3b8" }}>H: </span><span style={{ fontWeight: 600, color: "#22c55e" }}>₹{Number(data.high).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span></div>
            <div><span style={{ color: "#94a3b8" }}>L: </span><span style={{ fontWeight: 600, color: "#ef4444" }}>₹{Number(data.low).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span></div>
            <div><span style={{ color: "#94a3b8" }}>C: </span><span style={{ fontWeight: 600, color }}>₹{Number(data.close || data.price).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span></div>
          </div>
        )}
        {data.volume !== undefined && (
          <div style={{ fontSize: "12px", color: "#94a3b8", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "4px", marginBottom: "4px" }}>
            Volume: <strong style={{ color: "#cbd5e1" }}>{Number(data.volume).toLocaleString("en-IN")}</strong>
          </div>
        )}
        {payload.filter(p => p.dataKey && p.dataKey.startsWith("sma")).map((entry, index) => (
          <div key={index} style={{ fontSize: "12px", margin: "2px 0", display: "flex", justifyContent: "space-between", gap: "6px" }}>
            <span style={{ color: entry.color || "#94a3b8" }}>{entry.name} :</span>
            <span style={{ fontWeight: "600", color: entry.color || "#60a5fa" }}>
              ₹{typeof entry.value === "number" ? entry.value.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : entry.value}
            </span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export default function MarketAnalysis() {
  // Read ?symbol= query param from the URL (set by notification click)
  const [searchParams, setSearchParams] = useSearchParams()

  const [selectedSymbol, setSelectedSymbol] = useState(() => {
    // Initialise from ?symbol= if present; validated against company list later
    const urlSymbol = searchParams.get("symbol")
    return urlSymbol ? urlSymbol.toUpperCase().trim() : "RELIANCE"
  })
  const [selectedRange, setSelectedRange] = useState("1Y")
  const [chartType, setChartType] = useState("candlestick") // "candlestick" | "line"
  const [searchQuery, setSearchQuery] = useState("")
  const [activeTab, setActiveTab] = useState("overview")

  // Track whether the URL-param boot has been applied already
  const urlSymbolAppliedRef = useRef(false)

  // Client-side in-memory analysis cache for instant sub-millisecond tab/symbol switching
  const analysisCacheRef = useRef(new Map())
  const sentimentCacheRef = useRef(new Map())
  const abortControllerRef = useRef(null)
  const ongoingFetchRef = useRef(null)

  // Company List fetched directly from backend GET /api/v1/stocks/companies
  const [companies, setCompanies] = useState([])

  useEffect(() => {
    let isMounted = true
    getSupportedCompanies()
      .then((res) => {
        if (isMounted && res && res.companies && res.companies.length > 0) {
          setCompanies(
            res.companies.map((c) => ({
              symbol: c.symbol,
              name: c.company_name,
              yahoo_ticker: c.yahoo_ticker,
            }))
          )
        }
      })
      .catch((err) => {
        console.warn("[MarketAnalysis] Failed to fetch companies from backend:", err)
      })
    return () => {
      isMounted = false
    }
  }, [])

  const activeCompanies = useMemo(() => {
    return companies.length > 0 ? companies : FALLBACK_NIFTY_COMPANIES
  }, [companies])

  // Once activeCompanies is available, validate and apply the ?symbol= URL param.
  // Runs only once — prevents infinite re-render loops.
  useEffect(() => {
    if (urlSymbolAppliedRef.current) return          // already applied
    if (activeCompanies.length === 0) return         // list not loaded yet

    const urlSymbol = searchParams.get("symbol")
    if (!urlSymbol) {
      urlSymbolAppliedRef.current = true
      return
    }

    const normalised = urlSymbol.toUpperCase().trim()
    const match = activeCompanies.find((c) => c.symbol === normalised)

    if (match) {
      setSelectedSymbol(match.symbol)  // set the dropdown
      setSearchQuery("")               // clear any stale search text
    } else {
      console.warn(
        `[MarketAnalysis] URL symbol "${normalised}" not found in company list — ignoring`
      )
    }

    // Clean ?symbol= from URL after applying so back-button works cleanly
    setSearchParams({}, { replace: true })
    urlSymbolAppliedRef.current = true
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCompanies])

  // Filter company dropdown list by search query
  const filteredCompanies = useMemo(() => {
    if (!searchQuery.trim()) return activeCompanies
    const q = searchQuery.toLowerCase()
    return activeCompanies.filter(
      (c) => c.symbol.toLowerCase().includes(q) || c.name.toLowerCase().includes(q)
    )
  }, [searchQuery, activeCompanies])

  // Current company object
  const currentCompany = useMemo(() => {
    return activeCompanies.find((c) => c.symbol === selectedSymbol) || activeCompanies[0]
  }, [selectedSymbol, activeCompanies])

  // Live API Analysis State
  const [liveApiData, setLiveApiData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState(null)

  // Live News Sentiment API State
  const [sentimentData, setSentimentData] = useState(null)
  const [sentimentLoading, setSentimentLoading] = useState(true)
  const [sentimentError, setSentimentError] = useState(null)

  // Fetch analysis + sentiment in PARALLEL — both fire simultaneously.
  // Analysis data renders chart/price instantly on arrival.
  // Sentiment renders independently when it resolves.
  useEffect(() => {
    const period = RANGE_TO_PERIOD[selectedRange] || "1y"
    const analysisCacheKey = `${selectedSymbol}_${period}`
    const sentimentCacheKey = selectedSymbol
    let isMounted = true

    // ── Analysis ──────────────────────────────────────────────────────
    const cachedAnalysis = analysisCacheRef.current.get(analysisCacheKey)
    if (cachedAnalysis) {
      setLiveApiData(cachedAnalysis)
      setLoading(false)
      setApiError(null)
    } else {
      // Abort previous in-flight analysis request
      if (abortControllerRef.current) {
        try { abortControllerRef.current.abort() } catch (_) {}
        abortControllerRef.current = null
      }
      const controller = new AbortController()
      abortControllerRef.current = controller
      setLoading(true)
      setApiError(null)
    }

    // ── Sentiment ─────────────────────────────────────────────────────
    const cachedSentiment = sentimentCacheRef.current.get(sentimentCacheKey)
    if (cachedSentiment) {
      setSentimentData(cachedSentiment)
      setSentimentLoading(false)
      setSentimentError(null)
    } else {
      setSentimentLoading(true)
      setSentimentError(null)
      setSentimentData(null)
    }

    // If both already cached — nothing to fetch
    if (cachedAnalysis && cachedSentiment) return

    // Build the two fetch promises; skip whichever is already cached
    const analysisPromise = cachedAnalysis
      ? Promise.resolve(cachedAnalysis)
      : (async () => {
          const controller = abortControllerRef.current
          const res = await getStockAnalysis(selectedSymbol, period, {
            signal: controller?.signal,
          })
          return res
        })()

    const sentimentPromise = cachedSentiment
      ? Promise.resolve(cachedSentiment)
      : getStockSentiment(selectedSymbol)

    // Track in-flight analysis for dedup
    if (!cachedAnalysis) {
      ongoingFetchRef.current = { key: analysisCacheKey, promise: analysisPromise }
    }

    // Fire both simultaneously — each settles independently
    analysisPromise
      .then((res) => {
        if (!isMounted) return
        if (res && res.historical_chart_data) {
          analysisCacheRef.current.set(analysisCacheKey, res)
          setLiveApiData(res)
          setApiError(null)
        } else {
          setApiError("Live market data unavailable")
          setLiveApiData(null)
        }
      })
      .catch((err) => {
        if (!isMounted || err?.name === "AbortError") return
        console.warn("[MarketAnalysis] Analysis fetch error:", err)
        setApiError("Live market data unavailable")
        setLiveApiData(null)
      })
      .finally(() => {
        if (isMounted) setLoading(false)
        if (ongoingFetchRef.current?.key === analysisCacheKey) {
          ongoingFetchRef.current = null
        }
      })

    sentimentPromise
      .then((res) => {
        if (!isMounted) return
        if (res) {
          sentimentCacheRef.current.set(sentimentCacheKey, res)
          setSentimentData(res)
          setSentimentError(null)
        }
      })
      .catch((err) => {
        if (!isMounted) return
        console.warn("[MarketAnalysis] Sentiment fetch error:", err)
        setSentimentError("Failed to load news sentiment data")
        setSentimentData(null)
      })
      .finally(() => {
        if (isMounted) setSentimentLoading(false)
      })

    return () => {
      isMounted = false
      try { abortControllerRef.current?.abort() } catch (_) {}
      abortControllerRef.current = null
    }
  }, [selectedSymbol, selectedRange])



  // Derived Historical Chart Data Series
  const chartData = useMemo(() => {
    return liveApiData?.historical_chart_data || []
  }, [liveApiData])

  const latestCandle = useMemo(() => {
    return chartData.length > 0 ? chartData[chartData.length - 1] : null
  }, [chartData])

  const prevCandle = useMemo(() => {
    return chartData.length > 1 ? chartData[chartData.length - 2] : null
  }, [chartData])

  const currentPrice = liveApiData?.current_close || latestCandle?.close || 0
  const priceChange = liveApiData?.price_change || (latestCandle && prevCandle ? roundVal(latestCandle.close - prevCandle.close) : 0)
  const priceChangePct = liveApiData?.price_change_percent || (latestCandle && prevCandle && prevCandle.close !== 0 ? roundVal(((latestCandle.close - prevCandle.close) / prevCandle.close) * 100) : 0)

  // Technical Summary Table Data
  const indicatorTable = useMemo(() => {
    if (!liveApiData || !liveApiData.technical_indicators) return []
    const ti = liveApiData.technical_indicators
    const ma = ti.moving_averages || {}
    const bb = ti.bollinger_bands || {}

    return [
      {
        indicator: "RSI (14)",
        value: ti.rsi_14 !== undefined ? ti.rsi_14 : "N/A",
        signal: ti.rsi_status === "OVERBOUGHT" ? "Sell / Overbought" : (ti.rsi_status === "OVERSOLD" ? "Buy / Oversold" : "Neutral"),
        details: "Momentum oscillator (30-70 range)",
      },
      {
        indicator: "MACD (12, 26, 9)",
        value: ti.macd !== undefined ? ti.macd : "N/A",
        signal: ti.macd > ti.macd_signal ? "Buy (Bullish Crossover)" : "Sell (Bearish Crossover)",
        details: `Signal: ${ti.macd_signal} | Hist: ${ti.macd_histogram}`,
      },
      {
        indicator: "Bollinger Bands (20, 2)",
        value: `Mid: ₹${bb.middle || 'N/A'}`,
        signal: currentPrice > bb.upper ? "Sell (Above Upper)" : (currentPrice < bb.lower ? "Buy (Below Lower)" : "Neutral"),
        details: `Upper: ₹${bb.upper} | Lower: ₹${bb.lower}`,
      },
      {
        indicator: "SMA (20)",
        value: ma.sma20 ? `₹${ma.sma20}` : "N/A",
        signal: currentPrice > ma.sma20 ? "Buy (Above SMA 20)" : "Sell (Below SMA 20)",
        details: "Short-term trend line",
      },
      {
        indicator: "SMA (50)",
        value: ma.sma50 ? `₹${ma.sma50}` : "N/A",
        signal: currentPrice > ma.sma50 ? "Buy (Above SMA 50)" : "Sell (Below SMA 50)",
        details: "Medium-term trend line",
      },
      {
        indicator: "SMA (200)",
        value: ma.sma200 ? `₹${ma.sma200}` : "N/A",
        signal: ma.sma200 ? (currentPrice > ma.sma200 ? "Buy (Above SMA 200)" : "Sell (Below SMA 200)") : "N/A",
        details: "Long-term trend baseline",
      },
    ]
  }, [liveApiData, currentPrice])

  // ML Prediction Data
  const livePrediction = useMemo(() => {
    const pred = liveApiData?.prediction || {}
    return {
      signal: pred.signal || "NEUTRAL",
      bullish: pred.prob_up !== undefined ? parseFloat((pred.prob_up * 100).toFixed(2)) : 0.0,
      bearish: pred.prob_down !== undefined ? parseFloat((pred.prob_down * 100).toFixed(2)) : 0.0,
      neutral: pred.prob_hold !== undefined ? parseFloat((pred.prob_hold * 100).toFixed(2)) : 0.0,
      confidence: pred.confidence_percent !== undefined ? parseFloat(pred.confidence_percent.toFixed(2)) : 0.0,
    }
  }, [liveApiData])

  const featureImportance = useMemo(() => {
    const topFeats = liveApiData?.top_influencing_features || []
    return topFeats.map((f) => ({
      feature: f.feature,
      importance: parseFloat((f.importance * 100).toFixed(2)),
    }))
  }, [liveApiData])

  function roundVal(v) {
    return Math.round(v * 100) / 100
  }

  const handleSearchSubmit = (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;
    const q = searchQuery.trim().toLowerCase();
    const match = activeCompanies.find(
      (c) => c.symbol.toLowerCase() === q || c.symbol.toLowerCase().includes(q) || c.name.toLowerCase().includes(q)
    );
    if (match) {
      setSelectedSymbol(match.symbol);
    }
  };

  return (
    <div className="smp-layout">
      {/* ----------------- LEFT SIDEBAR CONTROLS ----------------- */}
      <aside className="smp-sidebar">
        <div className="smp-sidebar__brand">
          <BrainCircuit size={22} className="text-blue-500" />
          <span>Stock Predictor</span>
        </div>

        <form className="smp-sidebar__group" onSubmit={handleSearchSubmit}>
          <label className="smp-sidebar__label">
            <Search size={14} /> Search Any Company
          </label>
          <div className="smp-sidebar__hint">Direct in Company Name or NSE Symbol</div>
          <div style={{ display: "flex", gap: "6px", marginTop: "4px" }}>
            <input
              type="text"
              placeholder="Type symbol (e.g. TCS)"
              className="smp-sidebar__input"
              style={{ flex: 1 }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearchSubmit(e);
              }}
            />
            <button
              type="submit"
              onClick={handleSearchSubmit}
              className="smp-tab-btn smp-tab-btn--active"
              style={{ padding: "0 12px", height: "36px", borderRadius: "6px", fontSize: "12px", display: "inline-flex", alignItems: "center", gap: "4px" }}
            >
              <Search size={13} /> Search
            </button>
          </div>
        </form>

        <div className="smp-sidebar__group">
          <label className="smp-sidebar__label">Supported Nifty 50 Companies ({activeCompanies.length})</label>
          <select
            className="smp-sidebar__select"
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
          >
            {filteredCompanies.map((c) => (
              <option key={c.symbol} value={c.symbol}>
                {c.symbol} - {c.name}
              </option>
            ))}
          </select>
        </div>

        <div className="smp-sidebar__group">
          <label className="smp-sidebar__label">Settings</label>
          <div className="smp-sidebar__hint">Chart Date Range</div>
          <select
            className="smp-sidebar__select"
            value={selectedRange}
            onChange={(e) => setSelectedRange(e.target.value)}
          >
            {DATE_RANGES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <div className="smp-sidebar__about">
          <div className="smp-sidebar__about-title">About</div>
          <div className="smp-sidebar__about-text">
            This dashboard uses XGBoost ML models to predict stock price movements based on technical indicators, fundamentals, and news sentiment.
          </div>
        </div>
      </aside>

      {/* ----------------- MAIN CONTENT AREA ----------------- */}
      <main className="smp-main">
        {/* Main Dashboard Banner & Header Stats */}
        <header className="smp-header">
          <h1 className="smp-header__title">
            📊 Stock Market Prediction Dashboard
          </h1>
          <div className="smp-header__ticker">
            {currentCompany.symbol} - {currentCompany.name}
          </div>

          <div className="smp-metrics-grid">
            <div className="smp-metric-item">
              <span className="smp-metric-item__label">Current Price</span>
              <div className="smp-metric-item__val">
                {loading ? (
                  <span style={{ color: "#94a3b8" }}>Loading...</span>
                ) : currentPrice > 0 ? (
                  <>
                    ₹{currentPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    <span className={priceChange >= 0 ? "smp-badge--pos" : "smp-badge--neg"}>
                      {priceChange >= 0 ? "+" : ""}
                      {priceChangePct}%
                    </span>
                  </>
                ) : (
                  <span style={{ color: "#94a3b8" }}>Unavailable</span>
                )}
              </div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">Prev Close</span>
              <div className="smp-metric-item__val">
                {loading ? (
                  <span style={{ color: "#94a3b8" }}>...</span>
                ) : (prevCandle ? prevCandle.close : currentPrice) > 0 ? (
                  `₹${(prevCandle ? prevCandle.close : currentPrice).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                ) : (
                  "N/A"
                )}
              </div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">Volume</span>
              <div className="smp-metric-item__val">{loading ? "..." : (latestCandle && latestCandle.volume > 0 ? latestCandle.volume.toLocaleString("en-IN") : "N/A")}</div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">Open</span>
              <div className="smp-metric-item__val">
                {loading ? "..." : (latestCandle && latestCandle.open > 0 ? `₹${latestCandle.open.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "N/A")}
              </div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">High</span>
              <div className="smp-metric-item__val">
                {loading ? "..." : (latestCandle && latestCandle.high > 0 ? `₹${latestCandle.high.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "N/A")}
              </div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">Low</span>
              <div className="smp-metric-item__val">
                {loading ? "..." : (latestCandle && latestCandle.low > 0 ? `₹${latestCandle.low.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "N/A")}
              </div>
            </div>
          </div>

          <div className="smp-header__subtext">
            {loading ? "Fetching market data..." : `As of Date: ${liveApiData?.as_of_date || latestCandle?.date || "Live"}`}
          </div>
        </header>

        {/* Navigation Tabs Bar */}
        <nav className="smp-tabs-bar">
          <button
            className={`smp-tab-btn ${activeTab === "overview" ? "smp-tab-btn--active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            Overview & Charts
          </button>
          <button
            className={`smp-tab-btn ${activeTab === "technical" ? "smp-tab-btn--active" : ""}`}
            onClick={() => setActiveTab("technical")}
          >
            Technical Analysis
          </button>
          <button
            className={`smp-tab-btn ${activeTab === "ml" ? "smp-tab-btn--active" : ""}`}
            onClick={() => setActiveTab("ml")}
          >
            ML Prediction
          </button>
          <button
            className={`smp-tab-btn ${activeTab === "news" ? "smp-tab-btn--active" : ""}`}
            onClick={() => setActiveTab("news")}
          >
            News Sentiment
          </button>
        </nav>

        {/* TAB 1: OVERVIEW & CHARTS */}
        {activeTab === "overview" && (
          loading && !liveApiData ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div className="smp-card">
                <div className="smp-skeleton smp-skeleton-bar" style={{ width: "40%", height: 24, marginBottom: 16 }} />
                <div className="smp-skeleton smp-skeleton-chart" />
              </div>
              <div className="smp-card">
                <div className="smp-skeleton smp-skeleton-bar" style={{ width: "35%", height: 24, marginBottom: 16 }} />
                <div className="smp-skeleton smp-skeleton-chart" style={{ height: 260 }} />
              </div>
            </div>
          ) : apiError && !liveApiData ? (
            <div className="smp-card text-center p-8 flex flex-col items-center justify-center gap-3 border border-red-500/30">
              <AlertTriangle size={32} className="text-red-400" />
              <div style={{ color: "#f87171", fontSize: 16, fontWeight: 600 }}>Live market data unavailable</div>
              <div style={{ color: "#94a3b8", fontSize: 13 }}>Failed to retrieve live market data for {currentCompany.symbol}. Please check your backend connection.</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {/* Chart 1: Price with Moving Averages & Candlestick toggle */}
              <div className="smp-card">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
                  <h3 className="smp-card__title" style={{ margin: 0 }}>
                    {currentCompany.symbol} - Price Action & Moving Averages ({selectedRange})
                  </h3>
                  <div style={{ display: "flex", alignItems: "center", gap: 4, background: "rgba(255,255,255,0.06)", padding: "3px 6px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)" }}>
                    <button
                      type="button"
                      onClick={() => setChartType("candlestick")}
                      style={{
                        background: chartType === "candlestick" ? "#3b82f6" : "transparent",
                        color: chartType === "candlestick" ? "#ffffff" : "#94a3b8",
                        border: "none",
                        borderRadius: 6,
                        padding: "3px 10px",
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: "pointer",
                        transition: "all 160ms ease",
                      }}
                    >
                      Candlesticks
                    </button>
                    <button
                      type="button"
                      onClick={() => setChartType("line")}
                      style={{
                        background: chartType === "line" ? "#3b82f6" : "transparent",
                        color: chartType === "line" ? "#ffffff" : "#94a3b8",
                        border: "none",
                        borderRadius: 6,
                        padding: "3px 10px",
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: "pointer",
                        transition: "all 160ms ease",
                      }}
                    >
                      Line
                    </button>
                  </div>
                </div>

                <div style={{ width: "100%", height: 340 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    {chartType === "candlestick" ? (
                      <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 12 }} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
                        <Tooltip content={<CustomOverviewTooltip />} />
                        <Legend />
                        <Bar dataKey="close" name="Price (OHLC)" shape={<CandlestickBar />} />
                        <Line type="monotone" dataKey="sma20" name="SMA 20" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                        <Line type="monotone" dataKey="sma50" name="SMA 50" stroke="#3b82f6" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                        <Line type="monotone" dataKey="sma200" name="SMA 200" stroke="#a855f7" strokeWidth={1.5} dot={false} connectNulls={false} />
                      </ComposedChart>
                    ) : (
                      <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 12 }} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
                        <Tooltip content={<CustomOverviewTooltip />} cursor={{ stroke: "#ffffff", strokeWidth: 1 }} />
                        <Legend />
                        <Line type="monotone" dataKey="price" name="Price (₹)" stroke="#22c55e" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="sma20" name="SMA 20" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                        <Line type="monotone" dataKey="sma50" name="SMA 50" stroke="#3b82f6" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                        <Line type="monotone" dataKey="sma200" name="SMA 200" stroke="#a855f7" strokeWidth={1.5} dot={false} connectNulls={false} />
                      </LineChart>
                    )}
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 2: Price & Volume with OHLC & Colored Volume Bars */}
              <div className="smp-card">
                <h3 className="smp-card__title">
                  {currentCompany.symbol} - Price & Volume Breakdown ({selectedRange})
                </h3>
                <div style={{ width: "100%", height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 12 }} />
                      <YAxis yAxisId="left" stroke="#64748b" tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
                      <YAxis yAxisId="right" orientation="right" stroke="#64748b" tick={{ fontSize: 12 }} />
                      <Tooltip content={<CustomOverviewTooltip />} />
                      <Legend />
                      <Bar yAxisId="left" dataKey="close" name="Price (OHLC)" shape={<CandlestickBar />} />
                      <Bar yAxisId="right" dataKey="volume" name="Volume" shape={<VolumeBar />} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )
        )}

        {/* TAB 2: TECHNICAL ANALYSIS */}
        {activeTab === "technical" && (
          loading && !liveApiData ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div className="smp-card">
                <div className="smp-skeleton smp-skeleton-bar" style={{ width: "30%", height: 20, marginBottom: 12 }} />
                <div className="smp-skeleton smp-skeleton-chart" style={{ height: 160 }} />
              </div>
              <div className="smp-card">
                <div className="smp-skeleton smp-skeleton-bar" style={{ width: "25%", height: 20, marginBottom: 12 }} />
                <div className="smp-skeleton smp-skeleton-chart" style={{ height: 160 }} />
              </div>
            </div>
          ) : apiError && !liveApiData ? (
            <div className="smp-card text-center p-8 flex flex-col items-center justify-center gap-3 border border-red-500/30">
              <AlertTriangle size={32} className="text-red-400" />
              <div style={{ color: "#f87171", fontSize: 16, fontWeight: 600 }}>Technical indicators unavailable</div>
              <div style={{ color: "#94a3b8", fontSize: 13 }}>Failed to retrieve technical analysis for {currentCompany.symbol}.</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div className="smp-card">
                <h2 className="smp-card__title" style={{ fontSize: 18 }}>
                  Technical Analysis ({selectedRange})
                </h2>

                <div className="smp-learner-box">
                  <div className="smp-learner-box__title">What this means for learners</div>
                  <ul>
                    <li>
                      <strong>SMA 20/50/200:</strong> Simple Moving Averages showing short, medium, and long term trend baselines.
                    </li>
                    <li>
                      <strong>MACD:</strong> Helps spot when the momentum is getting stronger or weaker.
                    </li>
                    <li>
                      <strong>Bollinger Bands:</strong> Show whether price is high or low compared to normal volatility range.
                    </li>
                    <li>
                      <strong>RSI:</strong> Shows overall momentum (Overbought &gt; 70, Oversold &lt; 30).
                    </li>
                  </ul>
                </div>
              </div>

              {/* RSI (14) Chart */}
              <div className="smp-card">
                <h3 className="smp-card__title">RSI (14)</h3>
                <div style={{ width: "100%", height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#64748b" domain={[0, 100]} tick={{ fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: "#0f172a", borderColor: "#334155", color: "#f8fafc" }} />
                      <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "Overbought (70)", fill: "#ef4444", fontSize: 10 }} />
                      <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="3 3" label={{ value: "Oversold (30)", fill: "#22c55e", fontSize: 10 }} />
                      <Line type="monotone" dataKey="rsi" name="RSI" stroke="#06b6d4" strokeWidth={1.8} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* MACD Chart */}
              <div className="smp-card">
                <h3 className="smp-card__title">MACD</h3>
                <div style={{ width: "100%", height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: "#0f172a", borderColor: "#334155", color: "#f8fafc" }} />
                      <Legend />
                      <Line type="monotone" dataKey="macd" name="MACD" stroke="#3b82f6" strokeWidth={1.8} dot={false} />
                      <Line type="monotone" dataKey="macd_signal" name="Signal" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
                      <Bar dataKey="macd_hist" name="Histogram" fill="#10b981" opacity={0.6} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Bollinger Bands Chart */}
              <div className="smp-card">
                <h3 className="smp-card__title">Bollinger Bands (20, 2)</h3>
                <div style={{ width: "100%", height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#64748b" tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
                      <Tooltip contentStyle={{ background: "#0f172a", borderColor: "#334155", color: "#f8fafc" }} />
                      <Legend />
                      <Line type="monotone" dataKey="upper_band" name="Upper Band" stroke="#ef4444" strokeDasharray="4 4" dot={false} />
                      <Line type="monotone" dataKey="middle_band" name="Middle Band (SMA 20)" stroke="#3b82f6" dot={false} />
                      <Line type="monotone" dataKey="lower_band" name="Lower Band" stroke="#22c55e" strokeDasharray="4 4" dot={false} />
                      <Line type="monotone" dataKey="price" name="Price (₹)" stroke="#ffffff" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Technical Indicators Summary Table */}
              <div className="smp-card">
                <h3 className="smp-card__title">Technical Indicators Summary</h3>
                <div className="smp-table-wrapper">
                  <table className="smp-table">
                    <thead>
                      <tr>
                        <th>Indicator</th>
                        <th>Value</th>
                        <th>Signal</th>
                        <th>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {indicatorTable.map((row, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600 }}>{row.indicator}</td>
                          <td style={{ fontFamily: "monospace" }}>{row.value}</td>
                          <td>
                            <span
                              className={
                                row.signal.includes("Buy")
                                  ? "smp-badge--pos"
                                  : row.signal.includes("Sell")
                                  ? "smp-badge--neg"
                                  : "gp-chip"
                              }
                            >
                              {row.signal}
                            </span>
                          </td>
                          <td style={{ color: "#94a3b8" }}>{row.details}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )
        )}

        {/* TAB 3: ML PREDICTION */}
        {activeTab === "ml" && (
          loading && !liveApiData ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div className="smp-card">
                <div className="smp-skeleton smp-skeleton-bar" style={{ width: "35%", height: 22, marginBottom: 14 }} />
                <div className="smp-skeleton smp-skeleton-chart" style={{ height: 180 }} />
              </div>
              <div className="smp-card">
                <div className="smp-skeleton smp-skeleton-bar" style={{ width: "45%", height: 22, marginBottom: 14 }} />
                <div className="smp-skeleton smp-skeleton-chart" style={{ height: 220 }} />
              </div>
            </div>
          ) : apiError && !liveApiData ? (
            <div className="smp-card text-center p-8 flex flex-col items-center justify-center gap-3 border border-red-500/30">
              <AlertTriangle size={32} className="text-red-400" />
              <div style={{ color: "#f87171", fontSize: 16, fontWeight: 600 }}>ML Prediction unavailable</div>
              <div style={{ color: "#94a3b8", fontSize: 13 }}>Failed to load machine learning movement prediction for {currentCompany.symbol}.</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>ML Prediction Engine</h2>

              <div className="smp-prediction-banner">
                <div>
                  <h3 className="smp-card__title" style={{ fontSize: 16 }}>
                    <Zap size={18} className="text-yellow-400" /> Live News & Indicator Aware XGBoost Model
                  </h3>
                  <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
                    Evaluated live against historical candlestick patterns, news sentiment, and macroeconomic indicators.
                  </div>
                </div>

                <div className="smp-live-badge">
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: livePrediction.signal === "BULLISH" ? "#22c55e" : (livePrediction.signal === "BEARISH" ? "#ef4444" : "#eab308"), display: "inline-block" }}></span>
                  LIVE PREDICTION: {livePrediction.signal}
                </div>

                <div className="smp-pred-stats-grid">
                  <div className="smp-pred-stat-card">
                    <div style={{ fontSize: 11, color: "#64748b" }}>Probabilities (UP / DOWN / HOLD)</div>
                    <div className="smp-pred-stat-card__val" style={{ color: "#22c55e" }}>
                      UP: {livePrediction.bullish}%
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
                      DOWN: {livePrediction.bearish}% | HOLD: {livePrediction.neutral}%
                    </div>
                  </div>

                  <div className="smp-pred-stat-card">
                    <div style={{ fontSize: 11, color: "#64748b" }}>Model Confidence</div>
                    <div className="smp-pred-stat-card__val" style={{ color: "#eab308" }}>
                      {livePrediction.confidence}%
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
                      High Confidence Classification
                    </div>
                  </div>

                  <div className="smp-pred-stat-card">
                    <div style={{ fontSize: 11, color: "#64748b" }}>Current Price</div>
                    <div className="smp-pred-stat-card__val" style={{ color: "#38bdf8" }}>
                      ₹{currentPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
              </div>

              {/* Disclaimer Banner */}
              <div className="smp-disclaimer">
                <AlertTriangle size={20} style={{ flexShrink: 0 }} />
                <div>
                  <strong>Disclaimer:</strong> Predictions are generated by machine learning models based on historical price patterns and news sentiment. Stock markets carry inherent risk; predictions do not constitute financial advice.
                </div>
              </div>

              {/* Feature Importance Bar Chart */}
              <div className="smp-card">
                <h3 className="smp-card__title">Top Influencing Features (XGBoost Model Weights)</h3>
                <div style={{ width: "100%", height: 360 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={featureImportance} layout="vertical" margin={{ top: 10, right: 30, left: 160, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="feature" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: "#0f172a", borderColor: "#334155", color: "#f8fafc" }} />
                      <Bar dataKey="importance" name="Importance Weight (%)" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )
        )}

        {/* TAB 4: NEWS SENTIMENT */}
        {activeTab === "news" && (
          sentimentLoading && !sentimentData ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div className="smp-card">
                <div className="smp-skeleton smp-skeleton-bar" style={{ width: "35%", height: 24, marginBottom: 16 }} />
                <div className="smp-pred-stats-grid--4col">
                  <div className="smp-skeleton smp-skeleton-bar" style={{ height: 60 }} />
                  <div className="smp-skeleton smp-skeleton-bar" style={{ height: 60 }} />
                  <div className="smp-skeleton smp-skeleton-bar" style={{ height: 60 }} />
                  <div className="smp-skeleton smp-skeleton-bar" style={{ height: 60 }} />
                </div>
              </div>
              <div className="smp-card">
                <div className="smp-skeleton smp-skeleton-bar" style={{ width: "40%", height: 20, marginBottom: 16 }} />
                <div className="smp-skeleton smp-skeleton-chart" style={{ height: 180 }} />
              </div>
            </div>
          ) : sentimentError && !sentimentData ? (
            <div className="smp-card text-center p-8 flex flex-col items-center justify-center gap-3 border border-red-500/30">
              <AlertTriangle size={32} className="text-red-400" />
              <div style={{ color: "#f87171", fontSize: 16, fontWeight: 600 }}>News sentiment unavailable</div>
              <div style={{ color: "#94a3b8", fontSize: 13 }}>Failed to retrieve dynamic news sentiment for {currentCompany.symbol}.</div>
              <button
                className="smp-tab-btn smp-tab-btn--active"
                style={{ marginTop: 8 }}
                onClick={() => {
                  sentimentCacheRef.current.delete(selectedSymbol)
                  setSelectedSymbol((s) => s)
                }}
              >
                <RefreshCw size={14} /> Retry Sentiment Fetch
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div className="smp-card">
                <h2 className="smp-card__title" style={{ fontSize: 18 }}>
                  News Sentiment Analysis - {currentCompany.name}
                </h2>

                <div className="smp-pred-stats-grid--4col" style={{ marginTop: 10 }}>
                  <div className="smp-pred-stat-card">
                    <div style={{ fontSize: 11, color: "#64748b" }}>Live Net Sentiment</div>
                    <div
                      className="smp-pred-stat-card__val"
                      style={{
                        color:
                          (sentimentData?.net_sentiment || 0) > 0
                            ? "#22c55e"
                            : (sentimentData?.net_sentiment || 0) < 0
                            ? "#ef4444"
                            : "#eab308",
                      }}
                    >
                      {sentimentData?.net_sentiment !== undefined
                        ? `${sentimentData.net_sentiment >= 0 ? "+" : ""}${sentimentData.net_sentiment.toFixed(2)} (${sentimentData.sentiment_label})`
                        : "0.00 (Neutral)"}
                    </div>
                  </div>
                  <div className="smp-pred-stat-card">
                    <div style={{ fontSize: 11, color: "#64748b" }}>Articles Traced</div>
                    <div className="smp-pred-stat-card__val">{sentimentData?.articles_traced || 0}</div>
                  </div>
                  <div className="smp-pred-stat-card">
                    <div style={{ fontSize: 11, color: "#64748b" }}>Positive Articles</div>
                    <div className="smp-pred-stat-card__val" style={{ color: "#22c55e" }}>
                      {sentimentData?.positive_articles || 0}
                    </div>
                  </div>
                  <div className="smp-pred-stat-card">
                    <div style={{ fontSize: 11, color: "#64748b" }}>Negative Articles</div>
                    <div className="smp-pred-stat-card__val" style={{ color: "#ef4444" }}>
                      {sentimentData?.negative_articles || 0}
                    </div>
                  </div>
                </div>
              </div>

              <div className="smp-card">
                <h3 className="smp-card__title">
                  <Newspaper size={18} /> Live News Articles & Sentiment Scores
                </h3>

                {!sentimentData?.news_list || sentimentData.news_list.length === 0 ? (
                  <div style={{ padding: 24, textAlign: "center", color: "#94a3b8", fontSize: 14 }}>
                    No recent news articles traced for {currentCompany.name}.
                  </div>
                ) : (
                  <div className="smp-news-grid">
                    {sentimentData.news_list.map((item) => (
                      <div key={item.id} className="smp-news-card">
                        <div className="smp-news-card__head">
                          {item.url ? (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noreferrer"
                              className="smp-news-card__title"
                              style={{ textDecoration: "none", color: "inherit" }}
                            >
                              {item.title}
                            </a>
                          ) : (
                            <div className="smp-news-card__title">{item.title}</div>
                          )}
                          <span
                            className={
                              item.sentiment === "POSITIVE"
                                ? "smp-badge--pos"
                                : item.sentiment === "NEGATIVE"
                                ? "smp-badge--neg"
                                : "gp-chip"
                            }
                          >
                            {item.sentiment} ({item.confidence})
                          </span>
                        </div>
                        <div style={{ fontSize: 11, color: "#64748b" }}>{item.source_date}</div>
                        <div className="smp-news-card__snippet">{item.excerpt}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        )}
      </main>
    </div>
  )
}

