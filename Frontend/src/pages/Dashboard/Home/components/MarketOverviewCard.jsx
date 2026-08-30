import { Activity, TrendingUp, TrendingDown } from "lucide-react"

export default function MarketOverviewCard({ data, style, onClick }) {
  const isOpen = data?.status === "OPEN"
  const nifty = data?.indices && data.indices.length > 0 && data.indices[0].value
    ? data.indices[0]
    : { label: "NIFTY 50", value: "N/A", change: "Data Unavailable", positive: true }
  
  const Ch = nifty.positive ? TrendingUp : TrendingDown

  return (
    <article
      className="summary-card summary-card--market summary-card--blue card-appear"
      style={{ ...style, cursor: onClick ? "pointer" : "default" }}
      onClick={onClick}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? "button" : undefined}
      title={onClick ? "Click to view Nifty 50 Shares" : undefined}
    >
      <div className="summary-card__market-head">
        <span className="summary-card__icon" aria-hidden="true">
          <Activity size={18} />
        </span>
        <span className={`market-status market-status--${isOpen ? "open" : "closed"}`}>
          <span className="market-status__dot" /> {isOpen ? "Market Open" : "Closed"}
        </span>
      </div>
      <span className="summary-card__label">Market Overview</span>
      <span className="summary-card__value gp-mono" title={nifty.value}>
        {nifty.value}
      </span>
      <span className={`summary-card__change ${nifty.positive ? "gp-pos" : "gp-neg"}`}>
        <Ch size={13} /> {nifty.change} ({nifty.label})
      </span>
    </article>
  )
}
