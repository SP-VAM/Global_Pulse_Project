import "./PageHeader.css"

/**
 * Reusable page heading used across dashboard routes.
 */
export default function PageHeader({ icon: Icon, title, subtitle, action }) {
  return (
    <header className="page-header">
      <div className="page-header__main">
        {Icon && (
          <span className="page-header__icon">
            <Icon size={24} />
          </span>
        )}
        <div>
          <h1 className="page-header__title">{title}</h1>
          {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="page-header__action">{action}</div>}
    </header>
  )
}
