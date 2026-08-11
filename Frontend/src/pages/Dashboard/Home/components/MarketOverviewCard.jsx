import { Activity, TrendingUp, TrendingDown } from "lucide-react"

export default function MarketOverviewCard({ data, style }) {
  const isOpen = data.status === "OPEN"
  return (
    <article className="summary-card summary-card--market card-appear" style={style}>
      <div className="summary-card__market-head">
        <span className="summary-card__icon" aria-hidden="true">
          <Activity size={18} />
        </span>
        <span className={`market-status market-status--${isOpen ? "open" : "closed"}`}>
          <span className="market-status__dot" /> {isOpen ? "Market Open" : "Closed"}
        </span>
      </div>
      <span className="summary-card__label">Market Overview</span>
      <ul className="market-mini">
        {data.indices.map((idx) => {
          const Ch = idx.positive ? TrendingUp : TrendingDown
          return (
            <li key={idx.id} className="market-mini__row">
              <span className="market-mini__name">{idx.label}</span>
              <span className="market-mini__value gp-mono">{idx.value}</span>
              <span className={`market-mini__change ${idx.positive ? "gp-pos" : "gp-neg"}`}>
                <Ch size={12} /> {idx.change}
              </span>
            </li>
          )
        })}
      </ul>
    </article>
  )
}
