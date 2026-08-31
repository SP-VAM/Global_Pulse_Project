import { useNavigate } from "react-router-dom"
import { RefreshCw, AlertCircle } from "lucide-react"

export default function TopMovers({
  movers,
  data,
  style,
  onViewAll,
  asOfFormatted,
  marketStatus,
  isStale,
  loading,
  error,
  onRetry,
}) {
  const navigate = useNavigate()
  const rawList = movers || data || []
  const handleViewAll = onViewAll || (() => navigate("/dashboard/constituents"))

  const statusText = marketStatus
    ? marketStatus === "OPEN"
      ? "Market Open"
      : "Market Closed"
    : null

  const timestampText = asOfFormatted ? `As of ${asOfFormatted}` : null
  const staleText = isStale ? "(Delayed)" : ""
  const metaSubtitle = [timestampText, statusText ? `${statusText} ${staleText}`.trim() : null]
    .filter(Boolean)
    .join(" • ")

  return (
    <aside className="movers card-appear" style={style} aria-label="Top movers in India">
      <header className="movers__head">
        <div>
          <h3 className="movers__title">Top Movers (India)</h3>
          {metaSubtitle && (
            <span style={{ fontSize: "11px", color: "#64748b", display: "block", marginTop: "2px" }}>
              {metaSubtitle}
            </span>
          )}
        </div>
      </header>

      {loading ? (
        <div style={{ padding: "24px 16px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
          <RefreshCw size={18} className="animate-spin" style={{ margin: "0 auto 8px", display: "block" }} />
          Loading top movers...
        </div>
      ) : error ? (
        <div style={{ padding: "20px 16px", textAlign: "center", color: "#f87171", fontSize: "13px" }}>
          <AlertCircle size={20} style={{ margin: "0 auto 6px", display: "block" }} />
          <div>{error}</div>
          {onRetry && (
            <button
              onClick={onRetry}
              style={{
                marginTop: 10,
                padding: "4px 12px",
                borderRadius: 4,
                background: "#1e293b",
                color: "#fff",
                border: "1px solid #334155",
                fontSize: "12px",
                cursor: "pointer",
              }}
            >
              Retry
            </button>
          )}
        </div>
      ) : rawList.length === 0 ? (
        <div style={{ padding: "24px 16px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
          No market movers available
        </div>
      ) : (
        <ul className="movers__list">
          {rawList.map((m, i) => {
            const sym = m.symbol || m.ticker || ""
            const name = m.name || m.company_name || sym
            const yahooTicker = m.yahoo_ticker || (sym ? `${sym}.NS` : "")
            const priceVal = m.value ?? (m.current_price != null ? `₹${m.current_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "")
            const isPos = m.positive !== undefined ? m.positive : (m.change_percent >= 0 || m.direction === "up")
            const changeStr = m.change ?? `${isPos ? "+" : ""}${typeof m.change_percent === "number" ? m.change_percent.toFixed(2) : m.change_percent}%`

            return (
              <li key={(m.id || sym) + "-" + i} className="movers__row">
                <span className="movers__logo" aria-hidden="true">
                  {name ? name.charAt(0) : "M"}
                </span>
                <div className="movers__info">
                  <span className="movers__name">{name}</span>
                  <span className="movers__ticker gp-mono">{yahooTicker || sym}</span>
                </div>
                <div className="movers__right">
                  <span className="movers__value gp-mono">{priceVal}</span>
                  <span className={`movers__change ${isPos ? "gp-pos" : "gp-neg"}`}>{changeStr}</span>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </aside>
  )
}
