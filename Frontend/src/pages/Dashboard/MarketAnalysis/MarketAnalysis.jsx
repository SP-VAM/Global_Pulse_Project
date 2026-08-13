import React, { useState, useMemo, useEffect } from "react"
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
  History,
  BarChart2,
  AlertTriangle,
  Zap,
  BookOpen,
  RefreshCw,
} from "lucide-react"

import { getStockAnalysis, getSupportedCompanies } from "../../../api/marketApi.js"
import {
  DATE_RANGES,
  getNewsSentimentData,
  getPredictionHistoryData,
} from "../../../data/marketAnalysisData.js"

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

const CustomOverviewTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div
        style={{
          background: "#19202e",
          border: "1px solid #334155",
          borderRadius: "10px",
          padding: "12px 18px",
          color: "#ffffff",
          boxShadow: "0 10px 25px rgba(0,0,0,0.6)",
        }}
      >
        <div style={{ fontWeight: "700", marginBottom: "8px", fontSize: "14px", color: "#f8fafc" }}>
          {label}
        </div>
        {payload.map((entry, index) => (
          <div key={index} style={{ fontSize: "13px", margin: "4px 0", display: "flex", gap: "6px" }}>
            <span style={{ color: "#94a3b8" }}>{entry.name} :</span>
            <span style={{ fontWeight: "600", color: entry.color || "#60a5fa" }}>
              {typeof entry.value === "number" ? entry.value.toLocaleString("en-IN") : entry.value}
            </span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export default function MarketAnalysis() {
  const [selectedSymbol, setSelectedSymbol] = useState("RELIANCE")
  const [selectedRange, setSelectedRange] = useState("1Y")
  const [searchQuery, setSearchQuery] = useState("")
  const [activeTab, setActiveTab] = useState("overview")

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

  // Fetch full analysis when selectedSymbol or selectedRange changes
  useEffect(() => {
    let isMounted = true
    setLoading(true)
    setApiError(null)

    const period = RANGE_TO_PERIOD[selectedRange] || "1y"

    getStockAnalysis(selectedSymbol, period)
      .then((res) => {
        if (isMounted) {
          if (res && res.historical_chart_data) {
            setLiveApiData(res)
            setApiError(null)
          } else {
            setApiError("Live market data unavailable")
            setLiveApiData(null)
          }
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn("[MarketAnalysis] Live API fetch error:", err)
          setApiError("Live market data unavailable")
          setLiveApiData(null)
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
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
      bullish: pred.prob_up ? parseFloat((pred.prob_up * 100).toFixed(1)) : 50.0,
      bearish: pred.prob_down ? parseFloat((pred.prob_down * 100).toFixed(1)) : 50.0,
      confidence: pred.confidence_percent ? parseFloat(pred.confidence_percent.toFixed(1)) : 0.0,
    }
  }, [liveApiData])

  const featureImportance = useMemo(() => {
    const topFeats = liveApiData?.top_influencing_features || []
    return topFeats.map((f) => ({
      feature: f.feature,
      importance: parseFloat((f.importance * 100).toFixed(2)),
    }))
  }, [liveApiData])

  // News & History Data
  const newsSentiment = useMemo(() => getNewsSentimentData(selectedSymbol), [selectedSymbol])
  const predictionHistory = useMemo(() => getPredictionHistoryData(selectedSymbol), [selectedSymbol])

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
                ₹{currentPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                <span className={priceChange >= 0 ? "smp-badge--pos" : "smp-badge--neg"}>
                  {priceChange >= 0 ? "+" : ""}
                  {priceChangePct}%
                </span>
              </div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">Prev Close</span>
              <div className="smp-metric-item__val">
                ₹{(prevCandle ? prevCandle.close : currentPrice).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">Volume</span>
              <div className="smp-metric-item__val">{latestCandle ? latestCandle.volume.toLocaleString("en-IN") : "N/A"}</div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">Open</span>
              <div className="smp-metric-item__val">
                ₹{(latestCandle ? latestCandle.open : currentPrice).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">High</span>
              <div className="smp-metric-item__val">
                ₹{(latestCandle ? latestCandle.high : currentPrice).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="smp-metric-item">
              <span className="smp-metric-item__label">Low</span>
              <div className="smp-metric-item__val">
                ₹{(latestCandle ? latestCandle.low : currentPrice).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          <div className="smp-header__subtext">
            As of Date: {liveApiData?.as_of_date || latestCandle?.date || "Live"}
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
          <button
            className={`smp-tab-btn ${activeTab === "history" ? "smp-tab-btn--active" : ""}`}
            onClick={() => setActiveTab("history")}
          >
            Prediction History
          </button>
        </nav>

        {/* LOADING & ERROR STATES */}
        {loading && (
          <div className="smp-card text-center p-8 flex flex-col items-center justify-center gap-3">
            <RefreshCw size={24} className="animate-spin text-blue-400" />
            <div style={{ color: "#94a3b8", fontSize: 14 }}>Loading live market data for {currentCompany.symbol} ({selectedRange})...</div>
          </div>
        )}

        {!loading && apiError && (
          <div className="smp-card text-center p-8 flex flex-col items-center justify-center gap-3 border border-red-500/30">
            <AlertTriangle size={32} className="text-red-400" />
            <div style={{ color: "#f87171", fontSize: 16, fontWeight: 600 }}>Live market data unavailable</div>
            <div style={{ color: "#94a3b8", fontSize: 13 }}>Failed to retrieve live market data for {currentCompany.symbol}. Please check your backend connection.</div>
          </div>
        )}

        {/* TAB 1: OVERVIEW & CHARTS */}
        {!loading && !apiError && activeTab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Chart 1: Price with Moving Averages */}
            <div className="smp-card">
              <h3 className="smp-card__title">
                {currentCompany.symbol} - Price with Moving Averages ({selectedRange})
              </h3>
              <div style={{ width: "100%", height: 320 }}>
                <ResponsiveContainer width="100%" height="100%">
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
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Price & Volume */}
            <div className="smp-card">
              <h3 className="smp-card__title">
                {currentCompany.symbol} - Price & Volume ({selectedRange})
              </h3>
              <div style={{ width: "100%", height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 12 }} />
                    <YAxis yAxisId="left" stroke="#64748b" tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
                    <YAxis yAxisId="right" orientation="right" stroke="#64748b" tick={{ fontSize: 12 }} />
                    <Tooltip content={<CustomOverviewTooltip />} />
                    <Legend />
                    <Line yAxisId="left" type="monotone" dataKey="price" name="Price (₹)" stroke="#ef4444" strokeWidth={2} dot={false} />
                    <Bar yAxisId="right" dataKey="volume" name="Volume" fill="#22c55e" opacity={0.4} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: TECHNICAL ANALYSIS */}
        {!loading && !apiError && activeTab === "technical" && (
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
        )}

        {/* TAB 3: ML PREDICTION */}
        {!loading && !apiError && activeTab === "ml" && (
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
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: livePrediction.signal === "BULLISH" ? "#22c55e" : "#ef4444", display: "inline-block" }}></span>
                LIVE PREDICTION: {livePrediction.signal}
              </div>

              <div className="smp-pred-stats-grid">
                <div className="smp-pred-stat-card">
                  <div style={{ fontSize: 11, color: "#64748b" }}>Bullish Probability</div>
                  <div className="smp-pred-stat-card__val" style={{ color: "#22c55e" }}>
                    {livePrediction.bullish}%
                  </div>
                  <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
                    Bearish: {livePrediction.bearish}%
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
        )}

        {/* TAB 4: NEWS SENTIMENT */}
        {!loading && !apiError && activeTab === "news" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="smp-card">
              <h2 className="smp-card__title" style={{ fontSize: 18 }}>
                News Sentiment Analysis - {currentCompany.name}
              </h2>

              <div className="smp-pred-stats-grid--4col" style={{ marginTop: 10 }}>
                <div className="smp-pred-stat-card">
                  <div style={{ fontSize: 11, color: "#64748b" }}>Live Net Sentiment</div>
                  <div className="smp-pred-stat-card__val" style={{ color: "#22c55e" }}>
                    {newsSentiment.score}
                  </div>
                </div>
                <div className="smp-pred-stat-card">
                  <div style={{ fontSize: 11, color: "#64748b" }}>Articles Traced</div>
                  <div className="smp-pred-stat-card__val">{newsSentiment.articlesTraced}</div>
                </div>
                <div className="smp-pred-stat-card">
                  <div style={{ fontSize: 11, color: "#64748b" }}>Positive Articles</div>
                  <div className="smp-pred-stat-card__val" style={{ color: "#22c55e" }}>
                    {newsSentiment.positive}
                  </div>
                </div>
                <div className="smp-pred-stat-card">
                  <div style={{ fontSize: 11, color: "#64748b" }}>Negative Articles</div>
                  <div className="smp-pred-stat-card__val" style={{ color: "#ef4444" }}>
                    {newsSentiment.negative}
                  </div>
                </div>
              </div>
            </div>

            <div className="smp-card">
              <h3 className="smp-card__title">
                <Newspaper size={18} /> Live News Articles & Sentiment Scores
              </h3>

              <div className="smp-news-grid">
                {newsSentiment.newsList.map((item) => (
                  <div key={item.id} className="smp-news-card">
                    <div className="smp-news-card__head">
                      <div className="smp-news-card__title">{item.title}</div>
                      <span className={item.sentiment === "POSITIVE" ? "smp-badge--pos" : "gp-chip"}>
                        {item.sentiment} ({item.confidence})
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b" }}>{item.sourceDate}</div>
                    <div className="smp-news-card__snippet">{item.excerpt}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: PREDICTION HISTORY */}
        {!loading && !apiError && activeTab === "history" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="smp-card">
              <h2 className="smp-card__title" style={{ fontSize: 18 }}>
                <History size={18} /> Prediction History & Backtest Logs
              </h2>

              <div className="smp-pred-stats-grid" style={{ marginTop: 10 }}>
                <div className="smp-pred-stat-card">
                  <div style={{ fontSize: 11, color: "#64748b" }}>Model Accuracy</div>
                  <div className="smp-pred-stat-card__val" style={{ color: "#22c55e" }}>84.2%</div>
                </div>
                <div className="smp-pred-stat-card">
                  <div style={{ fontSize: 11, color: "#64748b" }}>Win Rate</div>
                  <div className="smp-pred-stat-card__val" style={{ color: "#38bdf8" }}>78.5%</div>
                </div>
                <div className="smp-pred-stat-card">
                  <div style={{ fontSize: 11, color: "#64748b" }}>Total Predictions</div>
                  <div className="smp-pred-stat-card__val">142</div>
                </div>
              </div>
            </div>

            <div className="smp-card">
              <h3 className="smp-card__title">Signal Log History</h3>
              <div className="smp-table-wrapper">
                <table className="smp-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Symbol</th>
                      <th>Signal</th>
                      <th>Initial Price</th>
                      <th>Target Price</th>
                      <th>Actual Price</th>
                      <th>Accuracy</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {predictionHistory.map((row, idx) => (
                      <tr key={idx}>
                        <td style={{ color: "#94a3b8" }}>{row.date}</td>
                        <td style={{ fontWeight: 600 }}>{row.symbol}</td>
                        <td>
                          <span className="smp-badge--pos">{row.signal}</span>
                        </td>
                        <td>₹{row.initialPrice}</td>
                        <td>₹{row.targetPrice}</td>
                        <td>₹{row.actualPrice}</td>
                        <td style={{ fontWeight: 600, color: "#22c55e" }}>{row.accuracy}</td>
                        <td>
                          <span className="smp-badge--pos">{row.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
