import { useState } from "react"
import { Settings as SettingsIcon, Bell, Moon, Globe, Shield, CreditCard } from "lucide-react"

import PageHeader from "../../../components/common/PageHeader/PageHeader.jsx"
import "../../../styles/page.css"
import "./Settings.css"

function Toggle({ on, onClick }) {
  return (
    <button
      type="button"
      className={`gp-toggle${on ? " gp-toggle--on" : ""}`}
      onClick={onClick}
      role="switch"
      aria-checked={on}
    >
      <span className="gp-toggle__dot" />
    </button>
  )
}

export default function Settings() {
  const [toggles, setToggles] = useState({
    alerts: true,
    dark: true,
    weekly: false,
    twofa: true,
  })

  const flip = (key) => setToggles((t) => ({ ...t, [key]: !t[key] }))

  const rows = [
    { key: "alerts", icon: Bell, title: "Price alerts", desc: "Notify me on major index moves." },
    { key: "dark", icon: Moon, title: "Dark mode", desc: "Use the cosmic dark theme." },
    { key: "weekly", icon: Globe, title: "Weekly digest", desc: "Email summary every Monday." },
    { key: "twofa", icon: Shield, title: "Two-factor auth", desc: "Extra security on login." },
  ]

  return (
    <div className="gp-page">
      <PageHeader icon={SettingsIcon} title="Settings" subtitle="Manage your GlobalPulse preferences." />

      <section className="gp-card">
        <h3 className="gp-card__title">Preferences</h3>
        <div className="settings-list">
          {rows.map((r) => (
            <div className="settings-row" key={r.key}>
              <div className="settings-row__left">
                <span className="settings-row__icon">
                  <r.icon size={18} />
                </span>
                <div>
                  <p className="settings-row__title">{r.title}</p>
                  <p className="settings-row__desc">{r.desc}</p>
                </div>
              </div>
              <Toggle on={toggles[r.key]} onClick={() => flip(r.key)} />
            </div>
          ))}
        </div>
      </section>

      <section className="gp-card">
        <h3 className="gp-card__title">Billing</h3>
        <div className="settings-row">
          <div className="settings-row__left">
            <span className="settings-row__icon">
              <CreditCard size={18} />
            </span>
            <div>
              <p className="settings-row__title">Starter plan</p>
              <p className="settings-row__desc">Free forever · upgrade anytime</p>
            </div>
          </div>
          <button className="gp-btn">Manage</button>
        </div>
      </section>
    </div>
  )
}
