import { Link } from "react-router-dom"
import "./Logo.css"

/**
 * GlobalPulse brand mark. The provided asset already contains the globe glyph,
 * wordmark and tagline as a single lockup, so we render it as one image.
 * @param {string} to - optional link target (pass null for a static mark)
 * @param {"sm"|"md"|"lg"} size
 */
export default function Logo({ to = "/dashboard", size = "md" }) {
  const content = (
    <span className={`logo logo--${size}`}>
      <img className="logo__img" src="/logo.png" alt="GlobalPulse" />
    </span>
  )

  if (to) {
    return (
      <Link to={to} className="logo__link" aria-label="GlobalPulse home">
        {content}
      </Link>
    )
  }
  return content
}
