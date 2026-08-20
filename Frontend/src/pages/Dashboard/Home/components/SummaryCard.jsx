import {
  Wallet,
  TrendingUp,
  TrendingDown,
  PieChart,
  PiggyBank,
  Target,
  Newspaper,
  GraduationCap,
  Activity,
  Sparkles,
  BookOpen,
} from "lucide-react"

const ICONS = {
  Wallet,
  TrendingUp,
  PieChart,
  PiggyBank,
  Target,
  Newspaper,
  GraduationCap,
  Activity,
  Sparkles,
  BookOpen,
}

export default function SummaryCard({ item, style, onClick }) {
  const Icon = ICONS[item.icon] ?? Wallet
  const hasDirection = item.positive === true || item.positive === false
  const ChangeIcon = item.positive ? TrendingUp : TrendingDown

  return (
    <article
      className={`summary-card summary-card--${item.tone || "blue"} card-appear`}
      style={{ ...style, cursor: onClick ? "pointer" : "default" }}
      onClick={onClick}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? "button" : undefined}
      aria-label={item.label}
    >
      <span className="summary-card__icon" aria-hidden="true">
        <Icon size={18} />
      </span>
      <span className="summary-card__label">{item.label}</span>
      <span className="summary-card__value gp-mono" title={typeof item.value === "string" ? item.value : undefined}>
        {item.value}
      </span>
      <span className={`summary-card__change ${item.positive ? "gp-pos" : item.positive === false ? "gp-neg" : ""}`}>
        {hasDirection && <ChangeIcon size={13} />} {item.change}
      </span>
    </article>
  )
}
