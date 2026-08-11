import "./ProgressRing.css"

/**
 * Animated circular progress indicator.
 * @param {number} value - 0..100
 */
export default function ProgressRing({ value = 0, size = 92, stroke = 8, color = "var(--blue-bright)" }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const offset = c - (value / 100) * c

  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="ring__svg">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          className="ring__value"
          style={{ strokeDasharray: c, strokeDashoffset: offset, "--ring-c": c }}
        />
      </svg>
      <span className="ring__label gp-mono">{value}%</span>
    </div>
  )
}
