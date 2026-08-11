import React, { useContext } from "react"
import { Plus, Wallet, TrendingUp } from "lucide-react"
import "./GoalPerformance.css"
import { GoalsContext } from "../../goalsContext.jsx"

export default function GoalPerformance({ onOpenUpdate, onOpenGoalModal }) {
  const { selected } = useContext(GoalsContext)

  if (!selected) {
    return (
      <div className="gp-empty-state">
        <p>No goal selected. Please set a goal.</p>
      </div>
    )
  }

  // Calculate percentage and values
  const targetVal = selected.target !== undefined && selected.target !== null ? Number(selected.target) : 400000
  const progressVal = selected.progress !== undefined && selected.progress !== null ? Number(selected.progress) : 140000
  const remainingVal = Math.max(0, targetVal - progressVal)
  const completionPct = targetVal > 0 ? Math.min(100, Math.round((progressVal / targetVal) * 100)) : 0

  // Calculate time left
  let daysLeft = 112
  if (selected.endDate) {
    const end = new Date(selected.endDate)
    const now = new Date()
    const diff = end.getTime() - now.getTime()
    daysLeft = Math.max(0, Math.ceil(diff / (1000 * 3600 * 24)))
  }

  // Format currency
  const formatCurr = (val) => {
    return "₹" + Number(val).toLocaleString("en-US")
  }

  // Sample history or real history
  const defaultHistory = [
    {
      id: "h1",
      title: "Monthly Deposit",
      subtitle: "Auto-transfer from Checking",
      amount: "+₹2,500",
      time: "Today, 09:00 AM",
      icon: "wallet",
    },
    {
      id: "h2",
      title: "Dividend Reinvestment",
      subtitle: "Vanguard S&P 500 ETF",
      amount: "+₹420",
      time: "Yesterday, 14:30 PM",
      icon: "trending",
    },
  ]

  const historyList = selected.history && selected.history.length > 0
    ? selected.history.map((h, idx) => ({
        id: h.id || `h-${idx}`,
        title: h.title || "Monthly Deposit",
        subtitle: h.subtitle || "Goal progress contribution",
        amount: h.amount ? `+₹${Number(h.amount).toLocaleString("en-US")}` : `+₹${Number(h.total || 0).toLocaleString("en-US")}`,
        time: h.date ? new Date(h.date).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "Today, 09:00 AM",
        icon: idx % 2 === 0 ? "wallet" : "trending",
      }))
    : defaultHistory

  return (
    <div className="gp-performance-container">
      {/* Top Header Actions */}
      <div className="gp-top-actions">
        <button className="gp-btn-action gp-btn--update-goal" onClick={onOpenGoalModal}>
          <Plus size={16} /> Update Goal
        </button>
        <button className="gp-btn-action gp-btn--update-progress" onClick={onOpenUpdate}>
          <Plus size={16} /> Update Progress
        </button>
      </div>

      {/* Main Grid: Left Interactive Donut, Right Stats & History */}
      <div className="gp-performance-grid">
        {/* Left Side: Interactive Concentric Donut Gauge */}
        <div className="gp-donut-section">
          <div className="gp-donut-wrapper">
            {/* SVG Concentric Rings */}
            <svg viewBox="0 0 400 400" className="gp-donut-svg">
              {/* Outer Orbit Dots */}
              <circle cx="200" cy="200" r="170" fill="none" stroke="#2563eb" strokeWidth="1" strokeDasharray="3 6" opacity="0.3" />
              <circle cx="200" cy="200" r="130" fill="none" stroke="#3b82f6" strokeWidth="1" strokeDasharray="2 4" opacity="0.25" />
              
              {/* Center Glow Circle */}
              <circle cx="200" cy="200" r="95" fill="rgba(15, 25, 48, 0.85)" stroke="#1d4ed8" strokeWidth="2" filter="drop-shadow(0 0 15px rgba(29, 78, 216, 0.4))" />

              {/* Arc Segment 1: Stocks (Top Right) */}
              <path
                d="M 200 30 A 170 170 0 0 1 370 200"
                fill="none"
                stroke="#3b82f6"
                strokeWidth="18"
                strokeLinecap="round"
              />

              {/* Arc Segment 2: Crypto (Bottom Right) */}
              <path
                d="M 365 220 A 170 170 0 0 1 210 370"
                fill="none"
                stroke="#1d4ed8"
                strokeWidth="18"
                strokeLinecap="round"
              />

              {/* Arc Segment 3: Gold/Silver (Bottom Left) */}
              <path
                d="M 190 370 A 170 170 0 0 1 35 220"
                fill="none"
                stroke="#f59e0b"
                strokeWidth="18"
                strokeLinecap="round"
              />

              {/* Arc Segment 4: Bonds (Top Left) */}
              <path
                d="M 35 190 A 170 170 0 0 1 170 35"
                fill="none"
                stroke="#b45309"
                strokeWidth="18"
                strokeLinecap="round"
              />
            </svg>

            {/* Donut Center Display */}
            <div className="gp-donut-center">
              <span className="gp-donut-pct">{completionPct}%</span>
              <span className="gp-donut-label">DIVERSIFIED</span>
            </div>

            {/* Pointer Tag 1: STOCKS */}
            <div className="gp-tag gp-tag--stocks">
              <div className="gp-tag-title">45% STOCKS</div>
              <div className="gp-tag-sub">+₹2.4k (24h)</div>
            </div>

            {/* Pointer Tag 2: CRYPTO */}
            <div className="gp-tag gp-tag--crypto">
              <div className="gp-tag-title">15% CRYPTO</div>
              <div className="gp-tag-sub">Volatile</div>
            </div>

            {/* Pointer Tag 3: GOLD/SILVER */}
            <div className="gp-tag gp-tag--gold">
              <div className="gp-tag-title">10% GOLD/SILVER</div>
              <div className="gp-tag-sub">Hedge</div>
            </div>

            {/* Pointer Tag 4: BONDS */}
            <div className="gp-tag gp-tag--bonds">
              <div className="gp-tag-title">30% BONDS</div>
              <div className="gp-tag-sub">Stable</div>
            </div>
          </div>
        </div>

        {/* Right Side: Stats & Progress History */}
        <div className="gp-stats-section">
          {/* 4 Metric Cards */}
          <div className="gp-cards-grid">
            {/* Card 1: Current Balance */}
            <div className="gp-stat-card">
              <div className="gp-stat-title">Current Balance</div>
              <div className="gp-stat-value">{formatCurr(progressVal)}</div>
            </div>

            {/* Card 2: Remaining */}
            <div className="gp-stat-card">
              <div className="gp-stat-title">Remaining</div>
              <div className="gp-stat-value">{formatCurr(remainingVal)}</div>
              <div className="gp-stat-sub">to goal</div>
            </div>

            {/* Card 3: Total Target */}
            <div className="gp-stat-card">
              <div className="gp-stat-title">Total Target</div>
              <div className="gp-stat-value">{formatCurr(targetVal)}</div>
              <div className="gp-stat-sub">FY 2024</div>
            </div>

            {/* Card 4: Time Left */}
            <div className="gp-stat-card">
              <div className="gp-stat-title">Time Left</div>
              <div className="gp-stat-value">{daysLeft} Days</div>
            </div>
          </div>

          {/* Progress History Container */}
          <div className="gp-history-card">
            <h3 className="gp-history-title">Progress History</h3>
            <div className="gp-history-list">
              {historyList.map((item) => (
                <div key={item.id} className="gp-history-item">
                  <div className="gp-history-left">
                    <div className="gp-history-icon">
                      {item.icon === "wallet" ? <Wallet size={18} /> : <TrendingUp size={18} />}
                    </div>
                    <div className="gp-history-details">
                      <div className="gp-history-name">{item.title}</div>
                      <div className="gp-history-sub">{item.subtitle}</div>
                    </div>
                  </div>
                  <div className="gp-history-right">
                    <div className="gp-history-amount">{item.amount}</div>
                    <div className="gp-history-time">{item.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}