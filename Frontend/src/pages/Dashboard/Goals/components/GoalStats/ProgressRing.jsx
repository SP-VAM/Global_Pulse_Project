import React, { useEffect, useRef, useState } from "react"

export default function ProgressRing({ percent = 0, size = 120 }) {
  const ref = useRef()
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    const circle = ref.current
    if (!circle) return
    const r = circle.r.baseVal.value
    const c = Math.PI * (r * 2)
    circle.style.strokeDasharray = `${c} ${c}`

    // animate stroke
    const pct = Math.max(0, Math.min(100, percent))
    const dash = (c * (100 - pct)) / 100
    circle.style.transition = "stroke-dashoffset .9s cubic-bezier(.2,.9,.2,1)"
    requestAnimationFrame(() => { circle.style.strokeDashoffset = dash })

    // animate number
    let raf
    const start = performance.now()
    const from = Number(display)
    const to = pct
    const dur = 900
    function step(t) {
      const p = Math.min(1, (t - start) / dur)
      const v = Math.round(from + (to - from) * p)
      setDisplay(v)
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [percent])

  return (
    <svg width={size} height={size} viewBox="0 0 120 120">
      <defs>
        <linearGradient id="g1" x1="0%" x2="100%">
          <stop offset="0%" stopColor="#0b62ff" />
          <stop offset="100%" stopColor="#1e7bff" />
        </linearGradient>
      </defs>
      <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
      <circle ref={ref} cx="60" cy="60" r="50" fill="none" stroke="url(#g1)" strokeWidth="10" strokeLinecap="round" transform="rotate(-90 60 60)" strokeDashoffset="0" />
      <text x="60" y="64" textAnchor="middle" fill="#e6f0ff" fontSize="18" fontWeight="600">{display}%</text>
    </svg>
  )
}
