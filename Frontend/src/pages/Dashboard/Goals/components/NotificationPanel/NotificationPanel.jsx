import React from "react"
import "./NotificationPanel.css"
import { X, CheckCheck, Bell, ShieldAlert, AlertTriangle, Wallet, BookOpen, ExternalLink, TrendingUp, BrainCircuit, Newspaper, GraduationCap, Calendar } from "lucide-react"

function getTypeIcon(type) {
  switch (type?.toUpperCase()) {
    case "SECURITY":
      return <ShieldAlert size={16} className="np-type-icon np-type-icon--security" />
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
  onNotificationClick,
}) {
  const hasUnread = notifications.some((n) => !n.is_read)

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

            {!loading && !error && notifications.length === 0 && (
              <div className="np-empty">
                <Bell size={32} className="np-empty__icon" />
                <p className="np-empty__title">All caught up!</p>
                <span className="np-empty__subtitle">No new notifications right now.</span>
              </div>
            )}

            {!loading && !error && notifications.map((n) => {
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
    </>
  )
}
