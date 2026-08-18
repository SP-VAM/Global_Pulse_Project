import { useEffect, useRef, useState, useCallback } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Bell, ChevronDown, User, LogOut } from "lucide-react"

import Logo from "../../common/Logo/Logo.jsx"
import NotificationPanel from "../../../pages/Dashboard/Goals/components/NotificationPanel/NotificationPanel.jsx"
import {
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "../../../api/notificationApi.js"
import "./Navbar.css"

export default function Navbar({ onLogoutClick }) {
  const [openMenu, setOpenMenu] = useState(null) // "notif" | "profile" | null
  const navRef = useRef(null)
  const navigate = useNavigate()

  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
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

  // Synchronize unread count from backend
  const refreshUnreadCount = useCallback(async () => {
    const token = localStorage.getItem("token") || localStorage.getItem("access_token")
    if (!token) {
      setUnreadCount(0)
      return
    }
    try {
      const res = await fetchUnreadCount()
      if (typeof res?.unread_count === "number") {
        setUnreadCount(res.unread_count)
      }
    } catch (err) {
      // Non-blocking: fail silently
      console.debug("[Navbar] Unread count fetch skipped:", err)
    }
  }, [])

  useEffect(() => {
    function onClick(e) {
      if (navRef.current && !navRef.current.contains(e.target)) setOpenMenu(null)
    }

    function refreshUser() {
      try {
        const saved = localStorage.getItem("user")
        const parsed = saved ? JSON.parse(saved) : null
        setCurrentUser(parsed)
        if (!parsed) {
          setUnreadCount(0)
          setNotifications([])
        } else {
          refreshUnreadCount()
        }
      } catch (e) {
        console.error("Failed to refresh user in Navbar", e)
      }
    }

    function handleNotificationEvent(e) {
      refreshUnreadCount()
    }

    refreshUser()
    refreshUnreadCount()

    // Register service worker for background web push if supported
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/firebase-messaging-sw.js")
        .catch((swErr) => console.debug("[SW] Push worker registration note:", swErr))
    }

    document.addEventListener("mousedown", onClick)
    window.addEventListener("user-updated", refreshUser)
    window.addEventListener("storage", refreshUser)
    window.addEventListener("notification-received", handleNotificationEvent)

    // Periodic lightweight background sync for new unread notifications (every 30s)
    const timer = setInterval(() => {
      refreshUnreadCount()
    }, 30000)

    return () => {
      document.removeEventListener("mousedown", onClick)
      window.removeEventListener("user-updated", refreshUser)
      window.removeEventListener("storage", refreshUser)
      window.removeEventListener("notification-received", handleNotificationEvent)
      clearInterval(timer)
    }
  }, [refreshUnreadCount])

  // Fetch notifications and mark as read when notification panel opens
  useEffect(() => {
    if (openMenu !== "notif") return

    let isMounted = true
    setLoading(true)
    setError(null)

    const token = localStorage.getItem("token") || localStorage.getItem("access_token")
    if (!token) {
      setNotifications([])
      setLoading(false)
      return
    }

    fetchNotifications({ limit: 50 })
      .then(async (res) => {
        if (!isMounted) return
        const notifs = res.notifications || []
        setNotifications(notifs)
        setLoading(false)

        // If unread notifications exist, mark them as read immediately upon viewing
        const hasUnread = notifs.some((n) => !n.is_read) || unreadCount > 0
        if (hasUnread) {
          // Optimistically reset unread count and badge to 0
          setUnreadCount(0)
          setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))

          try {
            await markAllNotificationsRead()
          } catch (err) {
            console.debug("[Navbar] Mark all read sync skipped:", err)
          }
        }
      })
      .catch((err) => {
        if (!isMounted) return
        console.warn("[Navbar] Notification fetch error:", err)
        setError("Notifications temporarily unavailable")
        setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [openMenu, unreadCount])

  const handleMarkAllRead = async () => {
    setUnreadCount(0)
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    try {
      await markAllNotificationsRead()
    } catch (e) {
      console.warn("Failed to mark all read:", e)
    }
  }

  const handleNotificationClick = async (notif) => {
    if (!notif) return

    if (!notif.is_read && (notif.notification_id || notif.id)) {
      const notifId = notif.notification_id || notif.id
      setNotifications((prev) =>
        prev.map((n) => ((n.notification_id || n.id) === notifId ? { ...n, is_read: true } : n))
      )
      try {
        await markNotificationRead(notifId)
      } catch (e) {
        console.debug("[Navbar] Single mark read skipped:", e)
      }
    }

    setOpenMenu(null)

    if (notif.action_url) {
      // Parse the raw action_url — it may contain a ?symbol=HCLTECH query param
      const raw = notif.action_url

      // Split path and query string
      const [rawPath, rawQuery] = raw.split("?")

      // Exhaustive path → confirmed existing route map
      const ROUTE_MAP = {
        // Expense / income / budget
        "/dashboard/expenses":        "/dashboard/expense-tracker",
        "/dashboard/expense":         "/dashboard/expense-tracker",
        "/dashboard/expense-tracker": "/dashboard/expense-tracker",
        "/dashboard/budget":          "/dashboard/expense-tracker",
        "/dashboard/income":          "/dashboard/expense-tracker",
        // Goals
        "/dashboard/goals":           "/dashboard/goals",
        "/dashboard/goal":            "/dashboard/goals",
        // Market / stocks (base path — query params handled separately below)
        "/dashboard/market-analysis": "/dashboard/market-analysis",
        "/dashboard/market":          "/dashboard/market-analysis",
        "/dashboard/stocks":          "/dashboard/market-analysis",
        "/dashboard/constituents":    "/dashboard/constituents",
        // Investments
        "/dashboard/investments":     "/dashboard",
        "/dashboard/portfolio":       "/dashboard",
        // Security / profile
        "/dashboard/profile":         "/dashboard/profile",
        "/dashboard/settings":        "/dashboard/settings",
        "/dashboard/security":        "/dashboard/profile",
        // Learning
        "/dashboard/learning-hub":    "/dashboard/learning-hub",
        "/dashboard/learn":           "/dashboard/learning-hub",
      }

      // Resolve the confirmed route for the path portion
      const resolvedPath =
        ROUTE_MAP[rawPath] ||
        (rawPath.startsWith("/dashboard/stocks")   ? "/dashboard/market-analysis" : null) ||
        (rawPath.startsWith("/dashboard/expense")  ? "/dashboard/expense-tracker"  : null) ||
        (rawPath.startsWith("/dashboard/goal")     ? "/dashboard/goals"            : null) ||
        "/dashboard"   // absolute safe fallback — always stays inside dashboard

      // Re-attach the original query string (e.g. ?symbol=HCLTECH) if present
      const targetUrl = rawQuery ? `${resolvedPath}?${rawQuery}` : resolvedPath

      navigate(targetUrl)
    }
  }



  const toggle = (menu) => setOpenMenu((cur) => (cur === menu ? null : menu))

  const userAvatar = currentUser?.profile_image || currentUser?.profileImage || currentUser?.avatar
  const fullName = [currentUser?.first_name || currentUser?.firstName, currentUser?.last_name || currentUser?.lastName].filter(Boolean).join(" ")
  const displayName = fullName || currentUser?.full_name || currentUser?.username || "John"
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
            {unreadCount > 0 && (
              <span className="navbar__badge">{unreadCount}</span>
            )}
          </button>

          <NotificationPanel
            open={openMenu === "notif"}
            onClose={() => setOpenMenu(null)}
            notifications={notifications}
            loading={loading}
            error={error}
            onMarkAllRead={handleMarkAllRead}
            onNotificationClick={handleNotificationClick}
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
              {userAvatar ? (
                <img src={userAvatar} alt="Avatar" />
              ) : (
                (displayName || "J").charAt(0).toUpperCase()
              )}
            </span>
            <span className="navbar__name">{displayName}</span>
            <ChevronDown size={14} className="navbar__chevron" />
          </button>

          {openMenu === "profile" && (
            <div className="navbar__dropdown">
              <div className="navbar__user-info">
                <div className="navbar__user-name">{displayName}</div>
                <div className="navbar__user-email">{displayEmail}</div>
              </div>
              <div className="navbar__divider" />
              <Link
                to="/dashboard/profile"
                className="navbar__dropdown-link"
                onClick={() => setOpenMenu(null)}
              >
                <User size={16} />
                <span>My Profile</span>
              </Link>
              <button
                type="button"
                className="navbar__dropdown-link navbar__dropdown-link--danger"
                onClick={() => {
                  setOpenMenu(null)
                  setUnreadCount(0)
                  setNotifications([])
                  if (onLogoutClick) onLogoutClick()
                }}
              >
                <LogOut size={16} />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
