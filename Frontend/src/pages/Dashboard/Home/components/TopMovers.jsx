import { useNavigate } from "react-router-dom"

export default function TopMovers({ movers, data, style, onViewAll }) {
  const navigate = useNavigate()
  const list = movers || data || []
  const handleViewAll = onViewAll || (() => navigate("/dashboard/constituents"))

  return (
    <aside className="movers card-appear" style={style} aria-label="Top movers in India">
      <header className="movers__head">
        <h3 className="movers__title">Top Movers (India)</h3>
        <button className="movers__viewall" onClick={handleViewAll}>
          VIEW ALL
        </button>
      </header>

      <ul className="movers__list">
        {list.map((m, i) => (
          <li key={m.id + "-" + i} className="movers__row">
            <span className="movers__logo" aria-hidden="true">
              {m.name ? m.name.charAt(0) : "M"}
            </span>
            <div className="movers__info">
              <span className="movers__name">{m.name}</span>
              <span className="movers__ticker gp-mono">{m.ticker}</span>
            </div>
            <div className="movers__right">
              <span className="movers__value gp-mono">{m.value}</span>
              <span className={`movers__change ${m.positive ? "gp-pos" : "gp-neg"}`}>{m.change}</span>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  )
}
