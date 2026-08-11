import { Wallet, TrendingUp, TrendingDown, PieChart, PiggyBank } from "lucide-react"

const ICONS = { Wallet, TrendingUp, PieChart, PiggyBank }

export default function SummaryCard({ item, style }) {
  const Icon = ICONS[item.icon] ?? Wallet
  const ChangeIcon = item.positive ? TrendingUp : TrendingDown
  return (
    <article className={`summary-card summary-card--${item.tone} card-appear`} style={style}>
      <span className="summary-card__icon" aria-hidden="true">
        <Icon size={18} />
      </span>
      <span className="summary-card__label">{item.label}</span>
      <span className="summary-card__value gp-mono">{item.value}</span>
      <span className={`summary-card__change ${item.positive ? "gp-pos" : "gp-neg"}`}>
        <ChangeIcon size={13} /> {item.change}
      </span>
    </article>
  )
}
