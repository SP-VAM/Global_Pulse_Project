import { useId } from "react"
import "./Sparkline.css"

/**
 * Lightweight animated line chart drawn with SVG.
 * @param {number[]} points - series of values (any scale)
 * @param {string} color - stroke color
 * @param {boolean} area - render a soft gradient fill under the line
 * @param {boolean} dots - render dots on data points
 * @param {string[]} labels - optional x-axis labels
 */
export default function Sparkline({
  points = [],
  color = "var(--blue-bright)",
  area = false,
  dots = false,
  labels = null,
  height = 60,
  strokeWidth = 2,
}) {
  const gradId = useId()
  const w = 100
  const h = height
  const pad = 6

  if (!points || !Array.isArray(points) || points.length === 0) {
    return (
      <div className="sparkline">
        {labels && (
          <div className="sparkline__labels">
            {labels.map((l) => (
              <span key={l}>{l}</span>
            ))}
          </div>
        )}
      </div>
    )
  }

  const max = Math.max(...points)
  const min = Math.min(...points)
  const range = max - min || 1

  const coords = points.map((p, i) => {
    const x = (i / (points.length - 1)) * (w - pad * 2) + pad
    const y = h - pad - ((p - min) / range) * (h - pad * 2)
    return { x, y }
  })

  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(2)} ${c.y.toFixed(2)}`).join(" ")
  const areaPath = `${path} L ${coords[coords.length - 1].x.toFixed(2)} ${h} L ${coords[0].x.toFixed(2)} ${h} Z`

  return (
    <div className="sparkline">
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="sparkline__svg" role="img">
        <defs>
          <linearGradient id={`fill-${gradId}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.28" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {area && <path d={areaPath} fill={`url(#fill-${gradId})`} className="sparkline__area" />}
        <path
          d={path}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="sparkline__line"
          vectorEffect="non-scaling-stroke"
        />
        {dots &&
          coords.map((c, i) => (
            <circle
              key={i}
              cx={c.x}
              cy={c.y}
              r="2.5"
              fill={color}
              className="sparkline__dot"
              vectorEffect="non-scaling-stroke"
            />
          ))}
      </svg>
      {labels && (
        <div className="sparkline__labels">
          {labels.map((l) => (
            <span key={l}>{l}</span>
          ))}
        </div>
      )}
    </div>
  )
}
