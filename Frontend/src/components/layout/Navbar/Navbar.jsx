import { useEffect, useRef, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Bell, ChevronDown, User, LogOut } from "lucide-react"

import Logo from "../../common/Logo/Logo.jsx"
import NotificationPanel from "../../../pages/dashboard/Goals/components/NotificationPanel/NotificationPanel.jsx"
import { getMarketSnapshot, getLatestNews } from "../../../api/marketApi.js"
import "./Navbar.css"

function formatRelativeTime(isoString) {
  if (!isoString) return "just now"
  try {
    const pubDate = new Date(isoString)
    const now = new Date()
    const diffSec = Math.floor((now.getTime() - pubDate.getTime()) / 1000)
    if (isNaN(diffSec) || diffSec < 60) return "just now"
    const diffMin = Math.floor(diffSec / 60)
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHours = Math.floor(diffMin / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  } catch (e) {
    return "just now"
  }
}

export default function Navbar() {
  const [openMenu, setOpenMenu] = useState(null) // "notif" | "profile" | null
  const navRef = useRef(null)
  const navigate = useNavigate()

  const [feedItems, setFeedItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem("user")
      return saved ? JSON.parse(saved) : null
    } catch (e) {
      return null
    }
  })

  useEffect(() => {
    function onClick(e) {
      if (navRef.current && !navRef.current.contains(e.target)) setOpenMenu(null)
    }
    document.addEventListener("mousedown", onClick)
    return () => document.removeEventListener("mousedown", onClick)
  }, [])

  // Fetch live market movers and news feed when notification dropdown opens
  useEffect(() => {
    if (openMenu !== "notif") return

    let isMounted = true
    setLoading(true)
    setError(null)

    Promise.all([
      getMarketSnapshot().catch(() => null),
      getLatestNews(3).catch(() => null),
    ])
      .then(([snapshotRes, newsRes]) => {
        if (!isMounted) return

        const items = []

        // 1. Process market movers (change_percent >= 1.5% or <= -1.5%)
        if (snapshotRes && snapshotRes.items) {
          const movers = snapshotRes.items.filter(
            (item) => Math.abs(item.change_percent || 0) >= 1.5
          )
          movers.slice(0, 3).forEach((item) => {
            const isPos = (item.change_percent || 0) >= 0
            items.push({
              id: `mover-${item.symbol}`,
              title: `${item.symbol} ${isPos ? "up +" : "down "}${item.change_percent.toFixed(2)}%`,
              meta: `${item.company_name} · ${isPos ? "Top NIFTY Gainer" : "Top NIFTY Decliner"}`,
              time: "Today",
            })
          })
        }

        // 2. Process live news articles
        if (newsRes && newsRes.articles) {
          newsRes.articles.slice(0, 3).forEach((art) => {
            items.push({
              id: `news-${art.id}`,
              title: art.headline,
              meta: `${art.source_name || "Market News"} · ${art.primary_category || "General"}`,
              time: formatRelativeTime(art.published_at_utc || art.published_at_ist),
            })
          })
        }

        setFeedItems(items)
        setLoading(false)
      })
      .catch((err) => {
        if (!isMounted) return
        console.warn("[Navbar] Feed fetch error:", err)
        setError("Notifications unavailable")
        setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [openMenu])

  const toggle = (menu) => setOpenMenu((cur) => (cur === menu ? null : menu))

  const displayName = currentUser?.full_name || currentUser?.username || "John"
  const displayEmail = currentUser?.email || (currentUser?.username ? `${currentUser.username}@globalpulse.io` : "john.abc@gmail.com")

  return (
    <header className="navbar" ref={navRef}>
      <div className="navbar__left">
        <Logo to="/dashboard" size="md" />
      </div>

      <div className="navbar__right">
        <div className="navbar__item-wrap">
          <button
            className={`navbar__icon-btn${openMenu === "notif" ? " is-active" : ""}`}
            onClick={() => toggle("notif")}
            aria-label="Notifications"
            aria-expanded={openMenu === "notif"}
          >
            <Bell size={20} />
            {feedItems.length > 0 && (
              <span className="navbar__badge">{feedItems.length}</span>
            )}
          </button>

          <NotificationPanel
            open={openMenu === "notif"}
            onClose={() => setOpenMenu(null)}
            notifications={feedItems}
            loading={loading}
            error={error}
          />
        </div>

        <div className="navbar__item-wrap">
          <button
            className={`navbar__profile${openMenu === "profile" ? " is-active" : ""}`}
            onClick={() => toggle("profile")}
            aria-label="Account menu"
            aria-expanded={openMenu === "profile"}
          >
            <span className="navbar__avatar">
              <User size={18} />
            </span>
            <ChevronDown size={16} className="navbar__chevron" />
          </button>

          {openMenu === "profile" && (
            <div className="navbar__dropdown navbar__dropdown--profile" role="menu">
              <div className="navbar__profile-head">
                <span className="navbar__avatar navbar__avatar--lg">
                  <User size={22} />
                </span>
                <div>
                  <p className="navbar__profile-name">{displayName}</p>
                  <p className="navbar__profile-email">{displayEmail}</p>
                </div>
              </div>
              <div className="navbar__menu-group">
                <Link to="/dashboard/profile" className="navbar__menu-item" onClick={() => setOpenMenu(null)}>
                  <User size={16} /> Profile
                </Link>
              </div>
              <button
                className="navbar__menu-item navbar__menu-item--danger"
                onClick={() => {
                  setOpenMenu(null)
                  localStorage.removeItem("access_token")
                  localStorage.removeItem("token")
                  navigate("/login")
                }}
              >
                <LogOut size={16} /> Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
