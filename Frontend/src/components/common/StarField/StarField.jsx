import { useMemo } from "react"
import "./StarField.css"

/**
 * Animated star background with a subtle blue glow.
 * Stars are generated once and gently twinkle + drift.
 */
export default function StarField({ count = 70 }) {
  const stars = useMemo(() => {
    return Array.from({ length: count }).map((_, i) => ({
      id: i,
      top: Math.random() * 100,
      left: Math.random() * 100,
      size: Math.random() * 2 + 1,
      delay: Math.random() * 6,
      duration: Math.random() * 4 + 3,
      bright: Math.random() > 0.85,
    }))
  }, [count])

  return (
    <div className="starfield" aria-hidden="true">
      <div className="starfield__glow starfield__glow--1" />
      <div className="starfield__glow starfield__glow--2" />
      {stars.map((s) => (
        <span
          key={s.id}
          className={`starfield__star${s.bright ? " starfield__star--bright" : ""}`}
          style={{
            top: `${s.top}%`,
            left: `${s.left}%`,
            width: `${s.size}px`,
            height: `${s.size}px`,
            animationDelay: `${s.delay}s`,
            animationDuration: `${s.duration}s`,
          }}
        />
      ))}
    </div>
  )
}
