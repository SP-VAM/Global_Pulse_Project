import { Laptop, Landmark, Car, Cross, Flame } from "lucide-react"

const ICONS = { Laptop, Landmark, Car, Cross, Flame }

export default function SectorCard({ sector, sectors, style }) {
  const items = sectors || (sector ? [sector] : [])
  return (
    <aside className="sectors-container card-appear" style={style}>
      <div className="sectors-grid" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {items.map((sec) => {
          const Icon = ICONS[sec.icon] ?? Laptop
          return (
            <article key={sec.id || sec.label} className={`sector-card sector-card--${sec.tone}`}>
              <span className="sector-card__icon">
                <Icon size={26} />
              </span>
              <h4 className="sector-card__label">{sec.label}</h4>
              <span className="sector-card__status">{sec.status}</span>
              <p className="sector-card__note">{sec.note}</p>
            </article>
          )
        })}
      </div>
    </aside>
  )
}
