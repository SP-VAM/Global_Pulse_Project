import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  BarChart2,
  TrendingUp,
  Globe,
  GraduationCap,
  Wallet,
  Target,
  Sparkles,
  LogOut,
} from "lucide-react"

import "./Sidebar.css"

const MAIN_LINKS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/dashboard/market-analysis", label: "Market Analysis", icon: Globe },
  { to: "/dashboard/learning-hub", label: "Learning Hub", icon: GraduationCap },
  { to: "/dashboard/expense-tracker", label: "Expense Tracker", icon: Wallet },
  { to: "/dashboard/goals", label: "Goals", icon: Target },
]

/**
 * Premium SaaS sidebar.
 * - Collapsed to 80px showing only icons.
 * - Expands to 260px on hover (icons + labels), reporting state to the layout.
 * - Active item: blue glow, white icon, left indicator bar.
 */
export default function Sidebar({ onHoverChange, onLogoutClick }) {
  return (
    <aside
      className="sidebar"
      onMouseEnter={() => onHoverChange(true)}
      onMouseLeave={() => {
        onHoverChange(false)
      }}
    >
      <div className="sidebar__top">
        <nav className="sidebar__nav" aria-label="Primary">
          <ul className="sidebar__list">
            {MAIN_LINKS.map(({ to, label, icon: Icon, end }) => (
              <li key={to}>
                <NavLink to={to} end={end} className={({ isActive }) => `sidebar__link${isActive ? " is-active" : ""}`}>
                  <span className="sidebar__indicator" />
                  <span className="sidebar__icon">
                    <Icon size={22} strokeWidth={2} />
                  </span>
                  <span className="sidebar__label">{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      <div className="sidebar__footer">
        <NavLink to="/dashboard/upgrade" className="sidebar__upgrade">
          <span className="sidebar__icon">
            <Sparkles size={20} />
          </span>
          <span className="sidebar__label">Upgrade to Pro</span>
        </NavLink>

        <button type="button" className="sidebar__link" onClick={onLogoutClick}>
          <span className="sidebar__indicator" />
          <span className="sidebar__icon">
            <LogOut size={22} />
          </span>
          <span className="sidebar__label">Logout</span>
        </button>
      </div>
    </aside>
  )
}
