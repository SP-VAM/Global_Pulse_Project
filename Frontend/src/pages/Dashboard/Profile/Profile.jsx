import { useState, useRef, useEffect } from "react"
import {
  User,
  Shield,
  Bell,
  Pencil,
  CheckCircle2,
  AlertCircle,
  Smartphone,
  ChevronRight,
  Mail,
} from "lucide-react"
import "./Profile.css"

function Toggle({ on, onChange }) {
  return (
    <button
      type="button"
      className={`gp-toggle${on ? " gp-toggle--on" : ""}`}
      onClick={() => onChange && onChange(!on)}
      role="switch"
      aria-checked={on}
    >
      <span className="gp-toggle__dot" />
    </button>
  )
}

export default function Profile() {
  const [activeTab, setActiveTab] = useState("Profile")

  // Load stored user or set default values matching design
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem("user")
      if (saved) {
        const parsed = JSON.parse(saved)
        const nameParts = (parsed.full_name || parsed.username || "Alex Sterling").split(" ")
        return {
          firstName: nameParts[0] || "Alex",
          lastName: nameParts.slice(1).join(" ") || "Sterling",
          email: parsed.email || `${parsed.username || "alex.sterling"}@globalpulse.ai`,
          phone: parsed.phone || "+1 (555) 012-3456",
          avatar: parsed.avatar || null,
        }
      }
    } catch (e) {
      console.error(e)
    }
    return {
      firstName: "Alex",
      lastName: "Sterling",
      email: "alex.sterling@globalpulse.ai",
      phone: "+1 (555) 012-3456",
      avatar: null,
    }
  })

  const [formData, setFormData] = useState({ ...user })
  const [notificationMsg, setNotificationMsg] = useState(null)
  const fileInputRef = useRef(null)

  // Security & Notification tab states
  const [twoFactor, setTwoFactor] = useState(true)
  const [notifState, setNotifState] = useState({
    marketAlerts: true,
    securityAlerts: true,
    dailySummaries: false,
    portfolioUpdates: true,
    soundNotifications: true,
    mobileMasterSwitch: true,
    smsAccountActivity: true,
    smsSecurityBreaches: true,
    waTradeConfirmations: true,
    waAiStrategyAlerts: false,
  })

  const toggleNotif = (key) => setNotifState((prev) => ({ ...prev, [key]: !prev[key] }))

  useEffect(() => {
    setFormData({ ...user })
  }, [user])

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handlePhotoUpload = (e) => {
    const file = e.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setFormData((prev) => ({ ...prev, avatar: reader.result }))
        showNotification("Photo updated successfully!", "success")
      }
      reader.readAsDataURL(file)
    }
  }

  const handleRemovePhoto = () => {
    setFormData((prev) => ({ ...prev, avatar: null }))
    showNotification("Photo removed", "info")
  }

  const handleSendRequest = (field) => {
    showNotification(`Verification request sent for ${field}`, "info")
  }

  const handleResetDefaults = () => {
    const defaultData = {
      firstName: "Alex",
      lastName: "Sterling",
      email: "alex.sterling@globalpulse.ai",
      phone: "+1 (555) 012-3456",
      avatar: null,
    }
    setFormData(defaultData)
    setUser(defaultData)
    localStorage.setItem(
      "user",
      JSON.stringify({
        full_name: "Alex Sterling",
        username: "alex",
        email: "alex.sterling@globalpulse.ai",
        phone: "+1 (555) 012-3456",
      })
    )
    showNotification("Settings reset to defaults", "info")
  }

  const handleSaveChanges = (e) => {
    e.preventDefault()
    const updatedUser = {
      ...formData,
      full_name: `${formData.firstName} ${formData.lastName}`.trim(),
      username: formData.firstName.toLowerCase(),
    }
    setUser(updatedUser)
    try {
      localStorage.setItem("user", JSON.stringify(updatedUser))
    } catch (err) {
      console.error(err)
    }
    showNotification("Changes saved successfully!", "success")
  }

  const showNotification = (msg, type = "success") => {
    setNotificationMsg({ msg, type })
    setTimeout(() => setNotificationMsg(null), 3000)
  }

  // Default avatar image fallback
  const defaultAvatar =
    "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=400&q=80"

  const currentTab = activeTab.toLowerCase()

  return (
    <div className="profile-container">
      {notificationMsg && (
        <div className={`profile-toast profile-toast--${notificationMsg.type}`}>
          {notificationMsg.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{notificationMsg.msg}</span>
        </div>
      )}

      <div className="profile-layout">
        {/* Left Navigation Card */}
        <aside className="profile-sidebar-card">
          <button
            className={`profile-nav-tab ${currentTab === "profile" ? "is-active" : ""}`}
            onClick={() => setActiveTab("Profile")}
          >
            <User size={20} />
            <span>Profile</span>
          </button>
          <button
            className={`profile-nav-tab ${currentTab === "security" ? "is-active" : ""}`}
            onClick={() => setActiveTab("Security")}
          >
            <Shield size={20} />
            <span>Security</span>
          </button>
          <button
            className={`profile-nav-tab ${currentTab === "notification" ? "is-active" : ""}`}
            onClick={() => setActiveTab("Notification")}
          >
            <Bell size={20} />
            <span>Notification</span>
          </button>
        </aside>

        {/* Tab Content: Profile Tab */}
        {currentTab === "profile" && (
          <div className="profile-content-grid">
            {/* Center Avatar Card */}
            <div className="profile-avatar-card">
              <div className="avatar-ring-wrapper">
                <img
                  src={formData.avatar || defaultAvatar}
                  alt="Profile Avatar"
                  className="avatar-image"
                />
              </div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handlePhotoUpload}
                accept="image/*"
                hidden
              />
              <button
                type="button"
                className="btn-change-photo"
                onClick={() => fileInputRef.current?.click()}
              >
                Change Photo
              </button>
              <button
                type="button"
                className="btn-remove-photo"
                onClick={handleRemovePhoto}
              >
                Remove
              </button>
            </div>

            {/* Right Form Card */}
            <form className="profile-form-card" onSubmit={handleSaveChanges}>
              <div className="form-row form-row--two-col">
                <div className="form-group">
                  <label className="form-label">FIRST NAME</label>
                  <input
                    type="text"
                    name="firstName"
                    className="form-input"
                    value={formData.firstName}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">LAST NAME</label>
                  <input
                    type="text"
                    name="lastName"
                    className="form-input"
                    value={formData.lastName}
                    onChange={handleInputChange}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">EMAIL ADDRESS</label>
                <div className="input-with-action">
                  <input
                    type="email"
                    name="email"
                    className="form-input"
                    value={formData.email}
                    onChange={handleInputChange}
                    required
                  />
                  <div className="action-buttons">
                    <button
                      type="button"
                      className="btn-send-request"
                      onClick={() => handleSendRequest("Email Address")}
                    >
                      SEND REQUEST
                    </button>
                    <button
                      type="button"
                      className="btn-edit-icon"
                      aria-label="Edit Email"
                      onClick={() => handleSendRequest("Email Address")}
                    >
                      <Pencil size={16} />
                    </button>
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Phone Number</label>
                <div className="input-with-action">
                  <input
                    type="text"
                    name="phone"
                    className="form-input"
                    value={formData.phone}
                    onChange={handleInputChange}
                  />
                  <div className="action-buttons">
                    <button
                      type="button"
                      className="btn-send-request"
                      onClick={() => handleSendRequest("Phone Number")}
                    >
                      SEND REQUEST
                    </button>
                    <button
                      type="button"
                      className="btn-edit-icon"
                      aria-label="Edit Phone"
                      onClick={() => handleSendRequest("Phone Number")}
                    >
                      <Pencil size={16} />
                    </button>
                  </div>
                </div>
              </div>

              <div className="profile-footer-actions">
                <button
                  type="button"
                  className="btn-reset"
                  onClick={handleResetDefaults}
                >
                  Reset to Defaults
                </button>
                <button type="submit" className="btn-save">
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        )}

        {/* TAB 2: SECURITY */}
        {currentTab === "security" && (
          <div className="ac-security-view">
            <div className="ac-card">
              <div className="ac-sec-header">
                <Shield size={22} className="ac-sec-title-icon" />
                <h2 className="ac-sec-title">Security & Privacy</h2>
              </div>

              {/* Two Factor Auth Block */}
              <div className="ac-2fa-block">
                <div className="ac-2fa-left">
                  <div className="ac-2fa-icon-box">
                    <Smartphone size={20} />
                  </div>
                  <div>
                    <h3 className="ac-2fa-heading">Two-Factor Authentication</h3>
                    <p className="ac-2fa-sub">Protect your account with an extra layer of security.</p>
                  </div>
                </div>
                <Toggle on={twoFactor} onChange={setTwoFactor} />
              </div>

              {/* Action Cards Row */}
              <div className="ac-sec-grid">
                <div className="ac-sec-action-card">
                  <div>
                    <h4 className="ac-sec-action-title">Change Password</h4>
                    <p className="ac-sec-action-sub">Last updated 14 days ago</p>
                  </div>
                  <ChevronRight size={18} className="ac-sec-chevron" />
                </div>

                <div className="ac-sec-action-card">
                  <div>
                    <h4 className="ac-sec-action-title">Privacy Settings</h4>
                    <p className="ac-sec-action-sub">Manage data visibility</p>
                  </div>
                  <ChevronRight size={18} className="ac-sec-chevron" />
                </div>
              </div>

              {/* Recent Activity Section */}
              <div className="ac-activity-section">
                <h4 className="ac-activity-head">RECENT ACTIVITY</h4>
                <div className="ac-activity-list">
                  <div className="ac-activity-item">
                    <div className="ac-activity-left">
                      <span className="ac-dot ac-dot--blue"></span>
                      <span className="ac-activity-title">Terminal Login - New York, US</span>
                    </div>
                    <span className="ac-activity-time">Just now</span>
                  </div>

                  <div className="ac-activity-item">
                    <div className="ac-activity-left">
                      <span className="ac-dot ac-dot--gray"></span>
                      <span className="ac-activity-title">API Key Generated</span>
                    </div>
                    <span className="ac-activity-time">2h ago</span>
                  </div>

                  <div className="ac-activity-item">
                    <div className="ac-activity-left">
                      <span className="ac-dot ac-dot--gray"></span>
                      <span className="ac-activity-title">Password Changed</span>
                    </div>
                    <span className="ac-activity-time">14d ago</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: NOTIFICATION */}
        {currentTab === "notification" && (
          <div className="ac-notification-view">
            {/* Top Header & Save Controls */}
            <div className="ac-notif-header">
              <div>
                <h2 className="ac-notif-title">Alerts & Notifications</h2>
                <p className="ac-notif-sub">
                  Precision-tune your real-time intelligence stream and delivery protocols.
                </p>
              </div>
              <div className="ac-notif-actions">
                <button
                  type="button"
                  className="ac-btn-secondary"
                  onClick={() => {
                    setNotifState({
                      marketAlerts: true,
                      securityAlerts: true,
                      dailySummaries: false,
                      portfolioUpdates: true,
                      soundNotifications: true,
                      mobileMasterSwitch: true,
                      smsAccountActivity: true,
                      smsSecurityBreaches: true,
                      waTradeConfirmations: true,
                      waAiStrategyAlerts: false,
                    })
                    showNotification("Notifications reset to defaults", "info")
                  }}
                >
                  Reset Default
                </button>
                <button
                  type="button"
                  className="ac-btn-primary"
                  onClick={() => showNotification("Notification protocols saved successfully!", "success")}
                >
                  Save Protocols
                </button>
              </div>
            </div>

            {/* Grid Row 1 */}
            <div className="ac-notif-grid-top">
              {/* Email Notifications Card */}
              <div className="ac-card ac-email-card">
                <div className="ac-card-head">
                  <div className="ac-card-head-left">
                    <Mail size={20} className="ac-cyan-icon" />
                    <div>
                      <h3 className="ac-card-title-text">Email Notifications</h3>
                      <p className="ac-card-sub-text">Primary address: {user.email || "user@sovereign-intel.io"}</p>
                    </div>
                  </div>
                  <span className="ac-tag-verified">✔ VERIFIED</span>
                </div>

                <div className="ac-toggles-2x2">
                  <div className="ac-toggle-box">
                    <div>
                      <h4 className="ac-toggle-title">Market Alerts</h4>
                      <p className="ac-toggle-desc">Volatility & gap up/down news.</p>
                    </div>
                    <Toggle on={notifState.marketAlerts} onChange={() => toggleNotif("marketAlerts")} />
                  </div>

                  <div className="ac-toggle-box">
                    <div>
                      <h4 className="ac-toggle-title">Security Alerts</h4>
                      <p className="ac-toggle-desc">Login & withdrawal activity.</p>
                    </div>
                    <Toggle on={notifState.securityAlerts} onChange={() => toggleNotif("securityAlerts")} />
                  </div>

                  <div className="ac-toggle-box">
                    <div>
                      <h4 className="ac-toggle-title">Daily Summaries</h4>
                      <p className="ac-toggle-desc">Consolidated morning brief.</p>
                    </div>
                    <Toggle on={notifState.dailySummaries} onChange={() => toggleNotif("dailySummaries")} />
                  </div>

                  <div className="ac-toggle-box">
                    <div>
                      <h4 className="ac-toggle-title">Portfolio Updates</h4>
                      <p className="ac-toggle-desc">Asset rebalancing & yields.</p>
                    </div>
                    <Toggle on={notifState.portfolioUpdates} onChange={() => toggleNotif("portfolioUpdates")} />
                  </div>
                </div>

                <div className="ac-email-footer">
                  <span>System last updated: Today, 08:45 UTC</span>
                  <button type="button" className="ac-link-cyan">✎ Change Primary Email</button>
                </div>
              </div>

              {/* Push & Desktop Card */}
              <div className="ac-card ac-push-card">
                <div className="ac-card-head">
                  <div className="ac-card-head-left">
                    <Bell size={20} className="ac-cyan-icon" />
                    <h3 className="ac-card-title-text">Push & Desktop</h3>
                  </div>
                </div>

                <div className="ac-browser-perm-box">
                  <div className="ac-browser-perm-head">
                    <span>Browser Permission</span>
                    <span className="ac-badge-blocked">
                      <AlertCircle size={12} /> BLOCKED BY BROWSER
                    </span>
                  </div>
                  <button
                    type="button"
                    className="ac-btn-outline-blue"
                    onClick={() => showNotification("Browser permission requested", "info")}
                  >
                    Enable Desktop Alerts
                  </button>
                </div>

                <div className="ac-toggle-box" style={{ marginTop: 16 }}>
                  <div>
                    <h4 className="ac-toggle-title">Sound Notifications</h4>
                    <p className="ac-toggle-desc">Play tone for high-vol alerts.</p>
                  </div>
                  <Toggle on={notifState.soundNotifications} onChange={() => toggleNotif("soundNotifications")} />
                </div>
              </div>
            </div>

            {/* Bottom Card: Mobile Intelligence Stream */}
            <div className="ac-card ac-mobile-card">
              <div className="ac-mobile-head">
                <div className="ac-mobile-head-left">
                  <Smartphone size={20} className="ac-cyan-icon" />
                  <div>
                    <div className="ac-mobile-title-wrap">
                      <h3 className="ac-card-title-text">Mobile Intelligence Stream</h3>
                      <span className="ac-chip-phone">{user.phone || "+1 (...) ***-5582"}</span>
                    </div>
                    <p className="ac-card-sub-text">
                      Configure direct-to-device critical updates via SMS or WhatsApp integration.
                    </p>
                  </div>
                </div>
                <div className="ac-master-switch-wrap">
                  <span className="ac-master-switch-label">Global Mobile Master Switch</span>
                  <Toggle on={notifState.mobileMasterSwitch} onChange={() => toggleNotif("mobileMasterSwitch")} />
                </div>
              </div>

              <div className="ac-mobile-3col">
                {/* Column 1: SMS PROTOCOLS */}
                <div className="ac-mobile-col">
                  <h4 className="ac-mobile-col-title">SMS PROTOCOLS</h4>
                  <label className="ac-checkbox-label">
                    <input
                      type="checkbox"
                      checked={notifState.smsAccountActivity}
                      onChange={() => toggleNotif("smsAccountActivity")}
                      className="ac-checkbox"
                    />
                    <span>Account Activity</span>
                  </label>
                  <label className="ac-checkbox-label">
                    <input
                      type="checkbox"
                      checked={notifState.smsSecurityBreaches}
                      onChange={() => toggleNotif("smsSecurityBreaches")}
                      className="ac-checkbox"
                    />
                    <span>Security Breaches</span>
                  </label>
                </div>

                {/* Column 2: WHATSAPP DIRECT */}
                <div className="ac-mobile-col">
                  <h4 className="ac-mobile-col-title">WHATSAPP DIRECT</h4>
                  <label className="ac-checkbox-label">
                    <input
                      type="checkbox"
                      checked={notifState.waTradeConfirmations}
                      onChange={() => toggleNotif("waTradeConfirmations")}
                      className="ac-checkbox"
                    />
                    <span>Trade Confirmations</span>
                  </label>
                  <label className="ac-checkbox-label">
                    <input
                      type="checkbox"
                      checked={notifState.waAiStrategyAlerts}
                      onChange={() => toggleNotif("waAiStrategyAlerts")}
                      className="ac-checkbox"
                    />
                    <span>AI Strategy Alerts</span>
                  </label>
                </div>

                {/* Column 3: PRICE MOVEMENT */}
                <div className="ac-mobile-col">
                  <h4 className="ac-mobile-col-title">PRICE MOVEMENT (±%)</h4>
                  <div className="ac-threshold-row">
                    <span>Threshold</span>
                    <span className="ac-threshold-val">5.0%</span>
                  </div>
                  <p className="ac-mobile-col-desc">
                    Notify when tracked assets move beyond the set percentage in a 1-hour window.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
