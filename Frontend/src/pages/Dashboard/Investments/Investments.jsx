import { useEffect, useState, useCallback } from "react"
import { TrendingUp, Plus, Trash2, Pencil, RefreshCw, Loader2, DollarSign, ArrowUpRight, ArrowDownRight, Wallet } from "lucide-react"

import { PageHeader, Sparkline } from "../../../components/common"
import { formatINR } from "../ExpenseTracker/data.js"
import { getPortfolioSummary, addInvestment, updateInvestment, deleteInvestment } from "../../../api/portfolioApi.js"
import InvestmentModal from "./InvestmentModal.jsx"
import "../../../styles/page.css"

export default function Investments() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [summary, setSummary] = useState({
    portfolioValue: 0.0,
    investedAmount: 0.0,
    totalProfitLoss: 0.0,
    percentageReturn: 0.0,
    todaysChange: 0.0,
    totalHoldingsCount: 0,
    holdings: [],
  })

  const [modalState, setModalState] = useState(null) // { mode: 'add'|'edit', initial }

  const fetchPortfolio = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const data = await getPortfolioSummary()
      setSummary(data)
    } catch (err) {
      console.error("[Portfolio fetch error]", err)
      setError(err.message || "Failed to load investment portfolio.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPortfolio()
  }, [fetchPortfolio])

  const handleSave = async (payload) => {
    try {
      if (modalState.mode === "edit") {
        await updateInvestment(modalState.initial.investmentId, payload)
      } else {
        await addInvestment(payload)
      }
      setModalState(null)
      await fetchPortfolio()
    } catch (err) {
      alert(err.message || "Failed to save holding.")
    }
  }

  const handleDelete = async (investmentId) => {
    if (!window.confirm("Are you sure you want to delete this holding from your portfolio?")) return
    try {
      await deleteInvestment(investmentId)
      await fetchPortfolio()
    } catch (err) {
      alert(err.message || "Failed to delete holding.")
    }
  }

  const isProfit = summary.totalProfitLoss >= 0
  const isTodayPositive = summary.todaysChange >= 0

  return (
    <div className="gp-page">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
        <PageHeader icon={TrendingUp} title="Investments" subtitle="Your real-time portfolio holdings and performance tracked in PostgreSQL." />
        <div style={{ display: "flex", gap: "10px" }}>
          <button className="et-btn et-btn--muted" onClick={fetchPortfolio} disabled={loading}>
            <RefreshCw size={16} className={loading ? "spin" : ""} /> Refresh Quotes
          </button>
          <button className="et-btn et-btn--primary" onClick={() => setModalState({ mode: "add" })}>
            <Plus size={18} /> Add Holding
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", borderRadius: "8px", background: "rgba(239,75,91,0.15)", border: "1px solid #ef4b5b", color: "#ef4b5b", marginBottom: "16px" }}>
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="gp-grid gp-grid--4">
        <article className="gp-card">
          <p className="gp-card__meta">Portfolio Value</p>
          <div className="gp-stat gp-mono">{loading ? "..." : formatINR(summary.portfolioValue)}</div>
        </article>
        <article className="gp-card">
          <p className="gp-card__meta">Invested Amount</p>
          <div className="gp-stat gp-mono">{loading ? "..." : formatINR(summary.investedAmount)}</div>
        </article>
        <article className="gp-card">
          <p className="gp-card__meta">Today&apos;s Change</p>
          <div className={`gp-stat gp-mono ${isTodayPositive ? "gp-pos" : "gp-neg"}`}>
            {loading ? "..." : `${isTodayPositive ? "+" : ""}${formatINR(summary.todaysChange)}`}
          </div>
        </article>
        <article className="gp-card">
          <p className="gp-card__meta">Total Return</p>
          <div className={`gp-stat gp-mono ${isProfit ? "gp-pos" : "gp-neg"}`}>
            {loading ? "..." : `${isProfit ? "+" : ""}${summary.percentageReturn}% (${formatINR(summary.totalProfitLoss)})`}
          </div>
        </article>
      </div>

      {/* Holdings List */}
      <div className="gp-card" style={{ marginTop: 20 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 className="gp-card__title">Holdings ({summary.totalHoldingsCount})</h3>
        </div>

        {loading ? (
          <p className="et-tx__empty" style={{ padding: "30px 0" }}><Loader2 size={18} className="spin" /> Loading live market quotes...</p>
        ) : summary.holdings.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--gp-text-muted)" }}>
            <Wallet size={36} style={{ marginBottom: "10px", opacity: 0.5 }} />
            <p style={{ fontSize: "15px", fontWeight: 600 }}>No holdings in your portfolio yet.</p>
            <p style={{ fontSize: "13px", marginTop: "4px" }}>Click &quot;Add Holding&quot; above to track stocks, mutual funds, SIPs, or ETFs.</p>
          </div>
        ) : (
          <ul style={{ listStyle: "none", marginTop: 12 }}>
            {summary.holdings.map((h) => {
              const isItemGain = h.totalGainLoss >= 0
              const isTodayGain = h.todaysChange >= 0
              return (
                <li
                  key={h.investmentId}
                  style={{ display: "flex", alignItems: "center", gap: 16, padding: "16px 0", borderBottom: "1px solid var(--border)" }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <p style={{ fontWeight: 600, fontSize: 15, margin: 0 }}>{h.companyName}</p>
                      <span style={{ fontSize: "11px", fontWeight: "700", padding: "2px 6px", borderRadius: "4px", background: "rgba(47,107,255,0.15)", color: "#2f6bff" }}>{h.ticker}</span>
                      <span style={{ fontSize: "11px", fontWeight: "600", padding: "2px 6px", borderRadius: "4px", background: "rgba(255,255,255,0.06)", color: "#8a94a6" }}>{h.assetType}</span>
                    </div>
                    <p className="gp-card__meta" style={{ marginTop: "4px" }}>
                      {h.quantity} units @ {formatINR(h.purchasePrice)} · Live: {formatINR(h.currentPrice)}
                    </p>
                  </div>

                  <div style={{ width: 110 }}>
                    <Sparkline points={h.sparklinePoints.length > 0 ? h.sparklinePoints : [h.purchasePrice, h.currentPrice]} color={isTodayGain ? "var(--green)" : "var(--red)"} height={40} strokeWidth={2} />
                  </div>

                  <div style={{ textAlign: "right", width: 130 }}>
                    <p className="gp-mono" style={{ fontWeight: 600, margin: 0 }}>
                      {formatINR(h.currentValue)}
                    </p>
                    <p className={isItemGain ? "gp-pos" : "gp-neg"} style={{ fontSize: 13, fontWeight: 600, margin: "2px 0 0" }}>
                      {isItemGain ? "+" : ""}{h.percentageReturn}% ({formatINR(h.totalGainLoss)})
                    </p>
                  </div>

                  <div style={{ display: "flex", gap: "6px" }}>
                    <button className="et-budget-card__edit" title="Edit holding" onClick={() => setModalState({ mode: "edit", initial: h })}>
                      <Pencil size={15} />
                    </button>
                    <button className="et-budget-card__edit" style={{ color: "#ef4b5b" }} title="Delete holding" onClick={() => handleDelete(h.investmentId)}>
                      <Trash2 size={15} />
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <InvestmentModal
        open={!!modalState}
        mode={modalState?.mode}
        initial={modalState?.initial}
        onClose={() => setModalState(null)}
        onSave={handleSave}
      />
    </div>
  )
}
