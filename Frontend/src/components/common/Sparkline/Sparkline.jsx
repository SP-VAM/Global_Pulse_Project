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
 * Generate sharp linear path from coordinate points for authentic real-world financial peaks and dips
 */
function getSharpPath(coords) {
  if (coords.length === 0) return ""
  if (coords.length === 1) return `M ${coords[0].x.toFixed(2)} ${coords[0].y.toFixed(2)}`
  return coords.reduce((acc, pt, idx) => {
    return idx === 0 ? `M ${pt.x.toFixed(2)} ${pt.y.toFixed(2)}` : `${acc} L ${pt.x.toFixed(2)} ${pt.y.toFixed(2)}`
  }, "")
}

/**
 * Enhanced interactive animated line chart drawn with SVG.
 */
export default function Sparkline({
  points = [],
  history = [],
  color = "var(--blue-bright)",
  area = true,
  dots = false,
  labels = null,
  height = 65,
  strokeWidth = 1.4,
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

  const sharpLine = getSharpPath(coords)
  const areaPath = `${sharpLine} L ${coords[coords.length - 1].x.toFixed(2)} ${h} L ${coords[0].x.toFixed(2)} ${h} Z`
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
            <stop offset="0%" stopColor={color} stopOpacity="0.14" />
            <stop offset="100%" stopColor={color} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {area && <path d={areaPath} fill={`url(#fill-${gradId})`} className="sparkline__area" />}

        <path
          d={sharpLine}
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
            stroke="rgba(255, 255, 255, 0.2)"
            strokeWidth="1"
            strokeDasharray="2 2"
            vectorEffect="non-scaling-stroke"
          />
        )}

        {/* Current price endpoint dot or hovered point */}
        {coords.length > 0 && (
          <circle
            cx={activeCoord ? activeCoord.x : coords[coords.length - 1].x}
            cy={activeCoord ? activeCoord.y : coords[coords.length - 1].y}
            r={activeCoord ? 3 : 2}
            fill={color}
            stroke="#ffffff"
            strokeWidth={1}
            className="sparkline__dot sparkline__dot--active"
            vectorEffect="non-scaling-stroke"
          />
        )}
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
