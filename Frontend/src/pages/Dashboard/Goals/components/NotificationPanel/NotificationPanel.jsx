import React, { useState } from "react"
import "./NotificationPanel.css"
import {
  X,
  CheckCheck,
  Bell,
  ShieldAlert,
  AlertTriangle,
  Wallet,
  BookOpen,
  ExternalLink,
  TrendingUp,
  BrainCircuit,
  Newspaper,
  GraduationCap,
  Calendar,
  KeyRound,
  MailCheck,
  Lock,
  Trash2,
  Filter,
} from "lucide-react"

const SECURITY_TYPES = [
  "PASSWORD_CHANGED",
  "EMAIL_PHONE_UPDATED",
  "MULTIPLE_FAILED_LOGINS",
  "REMOTE_SESSION_REVOKED",
  "SECURITY",
]

const FINANCIAL_TYPES = [
  "BUDGET_THRESHOLD_80",
  "BUDGET_THRESHOLD_90",
  "MONTHLY_FINANCIAL_DIGEST",
  "STOCK_PRICE_TARGET",
  "ML_HIGH_CONFIDENCE_SIGNAL",
  "NEWS_SENTIMENT_SHIFT",
  "LEARNING_MODULE_COMPLETED",
  "WEEKLY_EXPENSE_REMINDER",
  "BUDGET_ALERT",
  "FINANCIAL",
  "REMINDER",
]

function getTypeIcon(type) {
  switch (type?.toUpperCase()) {
    case "SECURITY":
    case "MULTIPLE_FAILED_LOGINS":
      return <ShieldAlert size={16} className="np-type-icon np-type-icon--security" />
    case "PASSWORD_CHANGED":
      return <KeyRound size={16} className="np-type-icon np-type-icon--security" style={{ color: "#ef4444" }} />
    case "EMAIL_PHONE_UPDATED":
      return <MailCheck size={16} className="np-type-icon np-type-icon--security" style={{ color: "#3b82f6" }} />
    case "REMOTE_SESSION_REVOKED":
      return <Lock size={16} className="np-type-icon np-type-icon--security" style={{ color: "#f59e0b" }} />
    case "BUDGET_ALERT":
    case "BUDGET_THRESHOLD_80":
    case "BUDGET_THRESHOLD_90":
      return <AlertTriangle size={16} className="np-type-icon np-type-icon--financial" style={{ color: "#f59e0b" }} />
    case "MONTHLY_FINANCIAL_DIGEST":
    case "FINANCIAL":
      return <Wallet size={16} className="np-type-icon np-type-icon--financial" />
    case "STOCK_PRICE_TARGET":
      return <TrendingUp size={16} className="np-type-icon" style={{ color: "#10b981" }} />
    case "ML_HIGH_CONFIDENCE_SIGNAL":
      return <BrainCircuit size={16} className="np-type-icon" style={{ color: "#8b5cf6" }} />
    case "NEWS_SENTIMENT_SHIFT":
      return <Newspaper size={16} className="np-type-icon" style={{ color: "#3b82f6" }} />
    case "LEARNING_MODULE_COMPLETED":
      return <GraduationCap size={16} className="np-type-icon" style={{ color: "#ec4899" }} />
    case "WEEKLY_EXPENSE_REMINDER":
    case "REMINDER":
      return <Calendar size={16} className="np-type-icon np-type-icon--reminder" />
    default:
      return <Bell size={16} className="np-type-icon np-type-icon--info" />
  }
}

function formatTime(isoString) {
  if (!isoString) return "Just now"
  try {
    const pubDate = new Date(isoString)
    const now = new Date()
    const diffSec = Math.floor((now.getTime() - pubDate.getTime()) / 1000)
    if (isNaN(diffSec) || diffSec < 60) return "Just now"
    const diffMin = Math.floor(diffSec / 60)
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHours = Math.floor(diffMin / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  } catch (e) {
    return "Recently"
  }
}

export default function NotificationPanel({
  open,
  onClose,
  notifications = [],
  loading = false,
  error = null,
  onMarkAllRead,
  onClearRead,
  onNotificationClick,
}) {
  const [activeFilter, setActiveFilter] = useState("All")
  const [showClearConfirm, setShowClearConfirm] = useState(false)

  const hasUnread = notifications.some((n) => !n.is_read)
  const hasRead = notifications.some((n) => n.is_read)

  const filteredNotifications = notifications.filter((n) => {
    const type = (n.notification_type || n.type || "").toUpperCase()
    if (activeFilter === "Security") {
      return SECURITY_TYPES.includes(type)
    }
    if (activeFilter === "Financial") {
      return FINANCIAL_TYPES.includes(type)
    }
    return true
  })

  return (
    <>
      {open && <div className="np-backdrop" onClick={onClose} />}
      <div className={`np-root${open ? " is-open" : ""}`}>
        <div className="np-inner">
          <div className="np-head">
            <div className="np-head__title-group">
              <Bell size={18} className="np-head__icon" />
              <h3 className="np-head__title">Notifications</h3>
              {notifications.length > 0 && (
                <span className="np-head__count">{notifications.length}</span>
              )}
            </div>
            <div className="np-head__actions">
              {hasUnread && onMarkAllRead && (
                <button
                  className="np-btn-mark-all"
                  onClick={onMarkAllRead}
                  title="Mark all as read"
                  aria-label="Mark all as read"
                >
                  <CheckCheck size={14} />
                  <span>Mark all read</span>
                </button>
              )}
              <button className="np-close-btn" onClick={onClose} aria-label="Close notification panel">
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Sub-header Filter Tabs & Clear Action */}
          <div className="np-filter-bar">
            <div className="np-filter-tabs">
              <button
                type="button"
                className={`np-filter-tab${activeFilter === "All" ? " is-active" : ""}`}
                onClick={() => setActiveFilter("All")}
              >
                All
              </button>
              <button
                type="button"
                className={`np-filter-tab${activeFilter === "Security" ? " is-active" : ""}`}
                onClick={() => setActiveFilter("Security")}
              >
                Security
              </button>
              <button
                type="button"
                className={`np-filter-tab${activeFilter === "Financial" ? " is-active" : ""}`}
                onClick={() => setActiveFilter("Financial")}
              >
                Financial
              </button>
            </div>

            {hasRead && onClearRead && (
              <button
                type="button"
                className="np-btn-clear-read"
                onClick={() => setShowClearConfirm(true)}
                title="Clear Read Notifications"
                aria-label="Clear Read Notifications"
              >
                <Trash2 size={13} />
                <span>Clear Read</span>
              </button>
            )}
          </div>

          <div className="np-list">
            {loading && (
              <div className="np-empty">
                <div className="np-spinner" />
                <span>Loading notifications...</span>
              </div>
            )}

            {!loading && error && (
              <div className="np-empty np-error">
                <AlertTriangle size={24} />
                <span>{error}</span>
              </div>
            )}

            {!loading && !error && filteredNotifications.length === 0 && (
              <div className="np-empty">
                <Bell size={32} className="np-empty__icon" />
                <p className="np-empty__title">
                  {activeFilter === "Security"
                    ? "No Security notifications found."
                    : activeFilter === "Financial"
                    ? "No Financial notifications found."
                    : "All caught up!"}
                </p>
                <span className="np-empty__subtitle">
                  {activeFilter === "All"
                    ? "No new notifications right now."
                    : `No ${activeFilter} alerts found in your notifications.`}
                </span>
              </div>
            )}

            {!loading && !error && filteredNotifications.map((n) => {
              const isUnread = !n.is_read
              return (
                <div
                  key={n.notification_id || n.id}
                  className={`np-card${isUnread ? " is-unread" : ""}${n.action_url ? " has-link" : ""}`}
                  onClick={() => onNotificationClick && onNotificationClick(n)}
                >
                  <div className="np-card__left">
                    <div className="np-card__icon-wrap">
                      {getTypeIcon(n.notification_type || n.type)}
                    </div>
                  </div>

                  <div className="np-card__body">
                    <div className="np-card__header-row">
                      <span className="np-card__title">{n.title}</span>
                      <span className="np-card__time">
                        {formatTime(n.created_at || n.timestamp)}
                      </span>
                    </div>
                    <p className="np-card__message">{n.message || n.meta}</p>
                    {n.action_url && (
                      <div className="np-card__action-link">
                        <span>View details</span>
                        <ExternalLink size={12} />
                      </div>
                    )}
                  </div>

                  {isUnread && <span className="np-unread-dot" title="Unread" />}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {showClearConfirm && (
        <div className="np-modal-backdrop" onClick={() => setShowClearConfirm(false)}>
          <div className="np-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="np-modal-head">
              <Trash2 size={20} className="np-modal-icon--danger" />
              <h4>Clear Read Notifications?</h4>
            </div>
            <p className="np-modal-body">
              Are you sure you want to delete all read notifications? Unread notifications will remain untouched.
            </p>
            <div className="np-modal-actions">
              <button
                type="button"
                className="np-btn-modal-cancel"
                onClick={() => setShowClearConfirm(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="np-btn-modal-confirm--danger"
                onClick={() => {
                  setShowClearConfirm(false)
                  if (onClearRead) onClearRead()
                }}
              >
                Yes, Clear Read
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
