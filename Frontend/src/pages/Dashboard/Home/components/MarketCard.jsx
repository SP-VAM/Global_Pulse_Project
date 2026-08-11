import Sparkline from "../../../../components/common/Sparkline/Sparkline.jsx"

export default function MarketCard({ item, series, style }) {
  const color = item.positive ? "var(--green)" : "var(--red)"
  return (
    <article className="market-card card-appear" style={style}>
      <header className="market-card__head">
        <span className="market-card__label">{item.label}</span>
      </header>
      <div className="market-card__value gp-mono">{item.value}</div>
      <div className={`market-card__change ${item.positive ? "gp-pos" : "gp-neg"}`}>{item.change}</div>
      <div className="market-card__chart">
        <Sparkline points={series} color={color} area height={70} strokeWidth={2} />
      </div>
    </article>
  )
}
