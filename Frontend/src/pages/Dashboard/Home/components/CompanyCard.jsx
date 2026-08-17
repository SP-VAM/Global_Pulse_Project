import React, { useMemo } from "react"
import Sparkline from "../../../../components/common/Sparkline/Sparkline.jsx"

/**
 * Format ISO date string (YYYY-MM-DD) into short date format (e.g. 'Aug 01')
 */
function formatShortDate(dateStr) {
  if (!dateStr) return ""
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleDateString("en-US", { month: "short", day: "2-digit" })
  } catch {
    return dateStr
  }
}

/**
 * Generate 4 dynamic date labels from historical data timestamps
 */
function getDynamicAxisLabels(history) {
  if (Array.isArray(history) && history.length > 0) {
    const dates = history
      .map((item) => (typeof item === "object" && item ? item.date : null))
      .filter(Boolean)

    if (dates.length >= 4) {
      const n = dates.length
      const idxs = [0, Math.floor(n / 3), Math.floor((2 * n) / 3), n - 1]
      return idxs.map((i) => formatShortDate(dates[i]))
    } else if (dates.length > 0) {
      return dates.map(formatShortDate)
    }
  }

  // Fallback: 1-month dynamic trading day markers based on current date
  const now = new Date()
  const d1 = new Date(now)
  d1.setDate(now.getDate() - 30)
  const d2 = new Date(now)
  d2.setDate(now.getDate() - 20)
  const d3 = new Date(now)
  d3.setDate(now.getDate() - 10)

  return [formatShortDate(d1), formatShortDate(d2), formatShortDate(d3), formatShortDate(now)]
}

export default function CompanyCard({ company, series, sparkline, style }) {
  const chartData = useMemo(() => {
    const raw = series || company?.series || sparkline || []
    if (Array.isArray(raw)) {
      return raw
        .map(Number)
        .filter((p) => typeof p === "number" && !isNaN(p) && isFinite(p) && p > 0)
    }
    return [10, 25, 40, 35, 60, 80]
  }, [series, company?.series, sparkline])

  const axisLabels = useMemo(() => {
    if (company?.labels && Array.isArray(company.labels) && company.labels.length > 0) {
      return company.labels
    }
    return getDynamicAxisLabels(company?.price_history || company?.history)
  }, [company?.labels, company?.price_history, company?.history])

  return (
    <article className="company-card card-appear" style={style} tabIndex={0}>
      <div className="company-card__top">
        <div className="company-card__header-left">
          <h3 className="company-card__name" title={company?.name || company?.ticker}>
            {company?.name || company?.ticker}
          </h3>
          <span className="company-card__ticker gp-mono">{company?.ticker}</span>
        </div>
        <div className="company-card__price-block">
          <span className="company-card__price gp-mono">{company?.price}</span>
          <span className={`company-card__change ${company?.positive ? "gp-pos" : "gp-neg"}`}>
            {company?.change}
          </span>
        </div>
      </div>

      <div className="company-card__chart">
        <Sparkline
          points={chartData}
          color="var(--blue-bright)"
          dots
          labels={axisLabels}
          height={55}
          strokeWidth={2}
        />
      </div>
    </article>
  )
}
