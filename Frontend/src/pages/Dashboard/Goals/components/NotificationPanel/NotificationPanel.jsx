import React from "react"
import "./NotificationPanel.css"
import { X } from "lucide-react"

export default function NotificationPanel({ open, onClose, notifications = [], loading = false, error = null }) {
  return (
    <div className={`np-root${open ? " is-open" : ""}`}>
      <div className="np-inner">
        <div className="np-head">
          <h3>Live Market & News Feed</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Close feed"><X /></button>
        </div>

        <div className="np-list">
          {loading && (
            <div className="np-empty">Loading live market feed...</div>
          )}

          {!loading && error && (
            <div className="np-empty np-error">{error}</div>
          )}

          {!loading && !error && notifications.length === 0 && (
            <div className="np-empty">No new notifications</div>
          )}

          {!loading && !error && notifications.map((n) => (
            <div key={n.id} className="np-card">
              <div style={{ flex: 1, paddingRight: 10 }}>
                <div className="np-title">{n.title}</div>
                <div className="np-meta" style={{ fontSize: "12px", marginTop: "2px" }}>{n.meta}</div>
              </div>
              <div className="np-time" style={{ fontSize: "11px", whiteSpace: "nowrap" }}>{n.time}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="np-backdrop" onClick={onClose} />
    </div>
  )
}
