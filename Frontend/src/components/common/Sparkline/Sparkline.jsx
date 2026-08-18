import { useState, useId, useCallback } from "react"
import "./Sparkline.css"

/**
 * Format price value to INR currency string
 */
function formatPriceINR(val) {
  if (typeof val !== "number" || isNaN(val)) return ""
  return "₹" + val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/**
 * Format ISO date string into short readable format (e.g. '04 Aug')
 */
function formatPointDate(dateStr) {
  if (!dateStr) return ""
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleDateString("en-US", { day: "2-digit", month: "short" })
  } catch {
    return dateStr
  }
}

/**
 * Generate smooth cubic Bezier path from coordinate points
 */
function getSmoothPath(coords) {
  if (coords.length === 0) return ""
  if (coords.length === 1) return `M ${coords[0].x} ${coords[0].y}`
  if (coords.length === 2) return `M ${coords[0].x} ${coords[0].y} L ${coords[1].x} ${coords[1].y}`

  let d = `M ${coords[0].x.toFixed(2)} ${coords[0].y.toFixed(2)}`
  for (let i = 0; i < coords.length - 1; i++) {
    const p0 = coords[i === 0 ? i : i - 1]
    const p1 = coords[i]
    const p2 = coords[i + 1]
    const p3 = coords[i + 2 < coords.length ? i + 2 : i + 1]

    const cp1x = p1.x + (p2.x - p0.x) / 6
    const cp1y = p1.y + (p2.y - p0.y) / 6
    const cp2x = p2.x - (p3.x - p1.x) / 6
    const cp2y = p2.y - (p3.y - p1.y) / 6

    d += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`
  }
  return d
}

/**
 * Enhanced interactive animated line chart drawn with SVG.
 */
export default function Sparkline({
  points = [],
  history = [],
  color = "var(--blue-bright)",
  area = true,
  dots = true,
  labels = null,
  height = 65,
  strokeWidth = 2.2,
}) {
  const gradId = useId()
  const [hoverIndex, setHoverIndex] = useState(null)

  const w = 100
  const h = height
  const padX = 10
  const padY = 10

  const cleanPoints = Array.isArray(points)
    ? points
        .map(Number)
        .filter((p) => typeof p === "number" && !isNaN(p) && isFinite(p) && p > 0)
    : []

  if (cleanPoints.length === 0) {
    return (
      <div className="sparkline">
        {labels && (
          <div className="sparkline__labels">
            {labels.map((l, idx) => (
              <span key={`${l}-${idx}`}>{l}</span>
            ))}
          </div>
        )}
      </div>
    )
  }

  const max = Math.max(...cleanPoints)
  const min = Math.min(...cleanPoints)
  const range = max - min || 1

  const coords = cleanPoints.map((p, i) => {
    const x = cleanPoints.length > 1 ? (i / (cleanPoints.length - 1)) * (w - padX * 2) + padX : w / 2
    const y = h - padY - ((p - min) / range) * (h - padY * 2)
    return { x, y, value: p, originalIndex: i }
  })

  const smoothLine = getSmoothPath(coords)
  const areaPath = `${smoothLine} L ${coords[coords.length - 1].x.toFixed(2)} ${h} L ${coords[0].x.toFixed(2)} ${h} Z`
  const activeCoord = hoverIndex !== null && coords[hoverIndex] ? coords[hoverIndex] : null

  // Smooth flicker-free container mouse handler
  const handleMouseMove = useCallback((e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    if (rect.width <= 0) return
    const relativeX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    const idx = Math.round(relativeX * (coords.length - 1))
    setHoverIndex(idx)
  }, [coords.length])

  // Resolve hover tooltip info
  let hoverDate = ""
  if (activeCoord && Array.isArray(history) && history[activeCoord.originalIndex]) {
    const item = history[activeCoord.originalIndex]
    hoverDate = item.date ? formatPointDate(item.date) : ""
  }

  return (
    <div
      className="sparkline"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoverIndex(null)}
    >
      {activeCoord && (
        <div className="sparkline__tooltip-badge card-appear">
          <span className="sparkline__tooltip-price">{formatPriceINR(activeCoord.value)}</span>
          {hoverDate && <span className="sparkline__tooltip-date">• {hoverDate}</span>}
        </div>
      )}

      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="sparkline__svg" role="img">
        <defs>
          <linearGradient id={`fill-${gradId}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {area && <path d={areaPath} fill={`url(#fill-${gradId})`} className="sparkline__area" />}

        <path
          d={smoothLine}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="sparkline__line"
          vectorEffect="non-scaling-stroke"
        />

        {/* Vertical hover guide line */}
        {activeCoord && (
          <line
            x1={activeCoord.x}
            y1={0}
            x2={activeCoord.x}
            y2={h}
            stroke="rgba(255, 255, 255, 0.25)"
            strokeWidth="1"
            strokeDasharray="2 2"
            vectorEffect="non-scaling-stroke"
          />
        )}

        {/* Data points */}
        {dots &&
          coords.map((c, i) => {
            const isHovered = hoverIndex === i
            return (
              <circle
                key={i}
                cx={c.x}
                cy={c.y}
                r={isHovered ? 3.5 : 2}
                fill={color}
                stroke={isHovered ? "#ffffff" : "none"}
                strokeWidth={isHovered ? 1.5 : 0}
                className={`sparkline__dot ${isHovered ? "sparkline__dot--active" : ""}`}
                vectorEffect="non-scaling-stroke"
              />
            )
          })}
      </svg>

      {labels && (
        <div className="sparkline__labels">
          {labels.map((l, idx) => (
            <span key={`${l}-${idx}`}>{l}</span>
          ))}
        </div>
      )}
    </div>
  )
}
