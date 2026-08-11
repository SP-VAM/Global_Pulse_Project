import Sparkline from "../../../../components/common/Sparkline/Sparkline.jsx"

const AXIS = ["2000", "2005", "2010", "2015", "Now"]

export default function CompanyCard({ company, series, sparkline, style }) {
  const chartData = series || sparkline || [10, 25, 40, 35, 60, 80]

  return (
    <article className="company-card card-appear" style={style} tabIndex={0}>
      <div className="company-card__top">
        <div className="company-card__header-left">
          <h3 className="company-card__name" title={company.name}>{company.name}</h3>
          <span className="company-card__ticker gp-mono">{company.ticker}</span>
        </div>
        <div className="company-card__price-block">
          <span className="company-card__price gp-mono">{company.price}</span>
          <span className={`company-card__change ${company.positive ? "gp-pos" : "gp-neg"}`}>{company.change}</span>
        </div>
      </div>

      <div className="company-card__chart">
        <Sparkline points={chartData} color="var(--blue-bright)" dots labels={AXIS} height={85} strokeWidth={2} />
      </div>
    </article>
  )
}
