import { useState, useRef, useEffect } from "react"
import { useNavigate } from "react-router-dom"
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
  Eye,
  EyeOff,
} from "lucide-react"
import { getMe, updateProfile } from "../../../api/authApi"
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

function parseUserData(parsed) {
  if (!parsed) return null
  const nameParts = (parsed.first_name || parsed.last_name)
    ? [parsed.first_name || "", parsed.last_name || ""]
    : (parsed.full_name || parsed.username || "").split(" ")
  return {
    firstName: parsed.first_name || parsed.firstName || nameParts[0] || "",
    lastName: parsed.last_name || parsed.lastName || nameParts.slice(1).join(" ") || "",
    email: parsed.email || "",
    phone: parsed.mobile_number || parsed.mobileNumber || parsed.phone || "",
    avatar: parsed.profile_image || parsed.profileImage || parsed.avatar || null,
    isEmailVerified: parsed.isEmailVerified !== undefined ? parsed.isEmailVerified : true,
    isPhoneVerified: parsed.isPhoneVerified !== undefined ? parsed.isPhoneVerified : false,
  }
}

export default function Profile() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState("Profile")

  // Load stored user or set default initial state:
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem("user")
      if (saved) {
        const parsed = JSON.parse(saved)
        const mapped = parseUserData(parsed)
        if (mapped) return mapped
      }
    } catch (e) {
      console.error(e)
    }
    return {
      firstName: "",
      lastName: "",
      email: localStorage.getItem("email") || "elax@gmail.com",
      phone: "",
      avatar: null,
      isEmailVerified: true,
      isPhoneVerified: false,
    }
  })

  const [formData, setFormData] = useState({ ...user })
  const [isEmailVerified, setIsEmailVerified] = useState(user.isEmailVerified)
  const [isPhoneVerified, setIsPhoneVerified] = useState(user.isPhoneVerified)

  const [isEditingEmail, setIsEditingEmail] = useState(false)
  const [isEditingPhone, setIsEditingPhone] = useState(false)

  // Inline OTP states
  const [showEmailOtp, setShowEmailOtp] = useState(false)
  const [showPhoneOtp, setShowPhoneOtp] = useState(false)
  const [emailOtp, setEmailOtp] = useState(["", "", "", "", "", ""])
  const [phoneOtp, setPhoneOtp] = useState(["", "", "", "", "", ""])
  const [generatedEmailOtp, setGeneratedEmailOtp] = useState("")
  const [generatedPhoneOtp, setGeneratedPhoneOtp] = useState("")

  const [notificationMsg, setNotificationMsg] = useState(null)
  const fileInputRef = useRef(null)

  // Fetch live profile from backend on mount
  useEffect(() => {
    async function fetchLiveProfile() {
      try {
        const liveUser = await getMe()
        if (liveUser) {
          const mapped = parseUserData(liveUser)
          if (mapped) {
            setUser((prev) => ({ ...prev, ...mapped }))
            setFormData((prev) => ({ ...prev, ...mapped }))
          }
        }
      } catch (err) {
        console.warn("Could not fetch live profile from API, using cached local data:", err)
      }
    }
    fetchLiveProfile()
  }, [])

  // Security Tab Password Change States
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  })
  const [showPass, setShowPass] = useState({
    current: false,
    new: false,
    confirm: false,
  })
  const [currentSavedPassword, setCurrentSavedPassword] = useState(() => {
    try {
      const saved = localStorage.getItem("user")
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.password) return parsed.password
      }
    } catch (e) {
      console.error(e)
    }
    return "password123"
  })

  const [twoFactor, setTwoFactor] = useState(true)

  // Notification States
  const [emailNotificationsEnabled, setEmailNotificationsEnabled] = useState(() => {
    try {
      const saved = localStorage.getItem("notifPreferences")
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.emailNotificationsEnabled !== undefined) return parsed.emailNotificationsEnabled
      }
    } catch (e) {
      console.error(e)
    }
    return true
  })

  const [mobileNotificationsEnabled, setMobileNotificationsEnabled] = useState(() => {
    try {
      const saved = localStorage.getItem("notifPreferences")
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.mobileNotificationsEnabled !== undefined) return parsed.mobileNotificationsEnabled
      }
    } catch (e) {
      console.error(e)
    }
    return true
  })

  const handleSaveNotificationPreferences = () => {
    try {
      localStorage.setItem(
        "notifPreferences",
        JSON.stringify({
          emailNotificationsEnabled,
          mobileNotificationsEnabled,
        })
      )
    } catch (err) {
      console.error(err)
    }
    showNotification("Notification preferences saved successfully.", "success")
  }

  const handleResetNotificationDefaults = () => {
    setEmailNotificationsEnabled(true)
    setMobileNotificationsEnabled(true)
    try {
      localStorage.setItem(
        "notifPreferences",
        JSON.stringify({
          emailNotificationsEnabled: true,
          mobileNotificationsEnabled: true,
        })
      )
    } catch (err) {
      console.error(err)
    }
    showNotification("Notification preferences reset to defaults.", "info")
  }

  useEffect(() => {
    setFormData({ ...user })
    setIsEmailVerified(user.isEmailVerified)
    setIsPhoneVerified(user.isPhoneVerified)
  }, [user])

  const showNotification = (msg, type = "success") => {
    setNotificationMsg({ msg, type })
    setTimeout(() => setNotificationMsg(null), 4000)
  }

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

  // Email Flow Actions
  const handleEditEmailClick = () => {
    setIsEditingEmail(true)
    setIsEmailVerified(false)
    setShowEmailOtp(false)
  }

  const handleSendEmailOtp = () => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!formData.email || !emailRegex.test(formData.email.trim())) {
      showNotification("Please enter a valid email address.", "error")
      return
    }
    const mockOtp = "123456"
    setGeneratedEmailOtp(mockOtp)
    setEmailOtp(["", "", "", "", "", ""])
    setShowEmailOtp(true)
    showNotification(`OTP sent to ${formData.email}. (Demo Code: 123456)`, "info")
  }

  const handleVerifyEmailOtp = () => {
    const code = emailOtp.join("")
    if (code === generatedEmailOtp || code === "123456") {
      setIsEmailVerified(true)
      setIsEditingEmail(false)
      setShowEmailOtp(false)
      showNotification("Email address verified successfully!", "success")
    } else {
      showNotification("Invalid OTP code. Please enter valid 6-digit code (123456)", "error")
    }
  }

  const handleResendEmailOtp = () => {
    const mockOtp = "123456"
    setGeneratedEmailOtp(mockOtp)
    setEmailOtp(["", "", "", "", "", ""])
    showNotification(`New OTP sent to ${formData.email}. (Demo Code: 123456)`, "info")
  }

  // Phone Flow Actions
  const handleEditPhoneClick = () => {
    setIsEditingPhone(true)
    setIsPhoneVerified(false)
    setShowPhoneOtp(false)
  }

  const handleSendPhoneOtp = () => {
    const phoneRegex = /^[+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]{6,15}$/
    if (!formData.phone || !phoneRegex.test(formData.phone.trim())) {
      showNotification("Please enter a valid phone number.", "error")
      return
    }
    const mockOtp = "123456"
    setGeneratedPhoneOtp(mockOtp)
    setPhoneOtp(["", "", "", "", "", ""])
    setShowPhoneOtp(true)
    showNotification(`OTP sent to ${formData.phone}. (Demo Code: 123456)`, "info")
  }

  const handleVerifyPhoneOtp = () => {
    const code = phoneOtp.join("")
    if (code === generatedPhoneOtp || code === "123456") {
      setIsPhoneVerified(true)
      setIsEditingPhone(false)
      setShowPhoneOtp(false)
      showNotification("Phone number verified successfully!", "success")
    } else {
      showNotification("Invalid OTP code. Please enter valid 6-digit code (123456)", "error")
    }
  }

  const handleResendPhoneOtp = () => {
    const mockOtp = "123456"
    setGeneratedPhoneOtp(mockOtp)
    setPhoneOtp(["", "", "", "", "", ""])
    showNotification(`New OTP sent to ${formData.phone}. (Demo Code: 123456)`, "info")
  }

  // Password Change Handlers
  const handlePasswordInputChange = (e) => {
    const { name, value } = e.target
    setPasswordForm((prev) => ({ ...prev, [name]: value }))
  }

  const toggleShowPass = (field) => {
    setShowPass((prev) => ({ ...prev, [field]: !prev[field] }))
  }

  const handleSavePassword = (e) => {
    e.preventDefault()

    const { currentPassword, newPassword, confirmPassword } = passwordForm

    if (!currentPassword || !newPassword || !confirmPassword) {
      showNotification("All password fields are mandatory.", "error")
      return
    }

    if (currentPassword !== currentSavedPassword) {
      showNotification("Current password is incorrect.", "error")
      return
    }

    const hasUpper = /[A-Z]/.test(newPassword)
    const hasLower = /[a-z]/.test(newPassword)
    const hasNum = /[0-9]/.test(newPassword)
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(newPassword)

    if (newPassword.length < 8 || !hasUpper || !hasLower || !hasNum || !hasSpecial) {
      showNotification(
        "Password must contain at least 8 characters, including uppercase, lowercase, number, and special character.",
        "error"
      )
      return
    }

    if (newPassword !== confirmPassword) {
      showNotification("Passwords do not match.", "error")
      return
    }

    setCurrentSavedPassword(newPassword)
    try {
      const saved = localStorage.getItem("user")
      const parsed = saved ? JSON.parse(saved) : {}
      localStorage.setItem("user", JSON.stringify({ ...parsed, password: newPassword }))
    } catch (err) {
      console.error(err)
    }

    setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" })
    setShowPass({ current: false, new: false, confirm: false })
    setIsChangingPassword(false)
    showNotification("Password updated successfully.", "success")
  }

  // OTP Input navigation helper
  const handleOtpInputChange = (e, idx, otpState, setOtpState, inputPrefix) => {
    const val = e.target.value
    if (val.length > 1) return

    const newOtp = [...otpState]
    newOtp[idx] = val
    setOtpState(newOtp)

    if (val && idx < 5) {
      const nextInput = document.getElementById(`${inputPrefix}-${idx + 1}`)
      if (nextInput) nextInput.focus()
    }
  }

  const handleOtpKeyDown = (e, idx, otpState, setOtpState, inputPrefix) => {
    if (e.key === "Backspace" && !otpState[idx] && idx > 0) {
      const prevInput = document.getElementById(`${inputPrefix}-${idx - 1}`)
      if (prevInput) prevInput.focus()
    }
  }

  const handleResetDefaults = () => {
    const defaultData = {
      firstName: "",
      lastName: "",
      email: "elax@gmail.com",
      phone: "",
      avatar: null,
      isEmailVerified: true,
      isPhoneVerified: false,
    }
    setFormData(defaultData)
    setUser(defaultData)
    setIsEditingEmail(false)
    setIsEditingPhone(false)
    setIsEmailVerified(true)
    setIsPhoneVerified(false)
    setShowEmailOtp(false)
    setShowPhoneOtp(false)
    setEmailOtp(["", "", "", "", "", ""])
    setPhoneOtp(["", "", "", "", "", ""])

    try {
      localStorage.setItem(
        "user",
        JSON.stringify({
          ...defaultData,
          full_name: "",
        })
      )
    } catch (e) {
      console.error(e)
    }
    showNotification("Settings reset to defaults", "info")
  }

  const handleSaveChanges = async (e) => {
    e.preventDefault()

    if (showEmailOtp || (isEditingEmail && !isEmailVerified)) {
      showNotification("Please complete email OTP verification before saving changes.", "error")
      return
    }

    if (showPhoneOtp || (isEditingPhone && !isPhoneVerified)) {
      showNotification("Please complete phone OTP verification before saving changes.", "error")
      return
    }

    const updatedUser = {
      ...formData,
      full_name: `${formData.firstName} ${formData.lastName}`.trim(),
      isEmailVerified,
      isPhoneVerified,
    }

    setUser(updatedUser)
    try {
      localStorage.setItem("user", JSON.stringify(updatedUser))
      await updateProfile({
        firstName: formData.firstName.trim(),
        lastName: formData.lastName ? formData.lastName.trim() : "",
        profileImage: formData.avatar || "",
      })
    } catch (err) {
      console.error("API profile update error:", err)
    }
    showNotification("Changes saved successfully!", "success")
  }

  const currentTab = activeTab.toLowerCase()

  return (
    <div className="profile-container">
      {notificationMsg && (
        <div className={`profile-toast profile-toast--${notificationMsg.type}`}>
          {notificationMsg.type === "success" ? (
            <CheckCircle2 size={18} />
          ) : (
            <AlertCircle size={18} />
          )}
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
                {formData.avatar ? (
                  <img
                    src={formData.avatar}
                    alt="Profile Avatar"
                    className="avatar-image"
                  />
                ) : (
                  <div className="avatar-placeholder">
                    <User size={52} className="avatar-placeholder-icon" />
                  </div>
                )}
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
                    placeholder="Enter First Name"
                    value={formData.firstName}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">LAST NAME</label>
                  <input
                    type="text"
                    name="lastName"
                    className="form-input"
                    placeholder="Enter Last Name"
                    value={formData.lastName}
                    onChange={handleInputChange}
                  />
                </div>
              </div>

              {/* EMAIL ADDRESS FIELD */}
              <div className="form-group">
                <label className="form-label">EMAIL ADDRESS</label>
                <div className="input-with-action">
                  <input
                    type="email"
                    name="email"
                    className={`form-input${isEmailVerified && !isEditingEmail ? " form-input--verified" : ""}`}
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="Enter Email Address"
                    readOnly={isEmailVerified && !isEditingEmail}
                  />
                  <div className="action-buttons">
                    {isEmailVerified && !isEditingEmail ? (
                      <>
                        <span className="verified-badge" title="Verified Email">
                          <CheckCircle2 size={20} className="icon-emerald" />
                        </span>
                        <button
                          type="button"
                          className="btn-edit-icon"
                          aria-label="Edit Email"
                          onClick={handleEditEmailClick}
                        >
                          <Pencil size={16} />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn-send-request"
                          onClick={handleSendEmailOtp}
                        >
                          SEND REQUEST
                        </button>
                        <button
                          type="button"
                          className="btn-edit-icon"
                          aria-label="Edit Email"
                          onClick={handleEditEmailClick}
                        >
                          <Pencil size={16} />
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Inline Email OTP Section */}
                {showEmailOtp && (
                  <div className="otp-inline-card">
                    <div className="otp-title-row">
                      <span className="otp-label">
                        Enter 6-digit OTP sent to {formData.email}
                      </span>
                    </div>
                    <div className="otp-input-group">
                      {emailOtp.map((digit, idx) => (
                        <input
                          key={idx}
                          id={`email-otp-${idx}`}
                          type="text"
                          maxLength={1}
                          className="otp-box"
                          value={digit}
                          onChange={(e) =>
                            handleOtpInputChange(e, idx, emailOtp, setEmailOtp, "email-otp")
                          }
                          onKeyDown={(e) =>
                            handleOtpKeyDown(e, idx, emailOtp, setEmailOtp, "email-otp")
                          }
                        />
                      ))}
                    </div>
                    <div className="otp-action-buttons">
                      <button
                        type="button"
                        className="btn-verify-otp"
                        onClick={handleVerifyEmailOtp}
                      >
                        Verify OTP
                      </button>
                      <button
                        type="button"
                        className="btn-resend-otp"
                        onClick={handleResendEmailOtp}
                      >
                        Resend OTP
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* PHONE NUMBER FIELD */}
              <div className="form-group">
                <label className="form-label">Phone Number</label>
                <div className="input-with-action">
                  <input
                    type="text"
                    name="phone"
                    className={`form-input${isPhoneVerified && !isEditingPhone ? " form-input--verified" : ""}`}
                    value={formData.phone}
                    onChange={handleInputChange}
                    placeholder="Enter Phone Number"
                    readOnly={isPhoneVerified && !isEditingPhone}
                  />
                  <div className="action-buttons">
                    {isPhoneVerified && !isEditingPhone ? (
                      <>
                        <span className="verified-badge" title="Verified Phone">
                          <CheckCircle2 size={20} className="icon-emerald" />
                        </span>
                        <button
                          type="button"
                          className="btn-edit-icon"
                          aria-label="Edit Phone"
                          onClick={handleEditPhoneClick}
                        >
                          <Pencil size={16} />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn-send-request"
                          onClick={handleSendPhoneOtp}
                        >
                          SEND REQUEST
                        </button>
                        <button
                          type="button"
                          className="btn-edit-icon"
                          aria-label="Edit Phone"
                          onClick={handleEditPhoneClick}
                        >
                          <Pencil size={16} />
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Inline Phone OTP Section */}
                {showPhoneOtp && (
                  <div className="otp-inline-card">
                    <div className="otp-title-row">
                      <span className="otp-label">
                        Enter 6-digit OTP sent to {formData.phone}
                      </span>
                    </div>
                    <div className="otp-input-group">
                      {phoneOtp.map((digit, idx) => (
                        <input
                          key={idx}
                          id={`phone-otp-${idx}`}
                          type="text"
                          maxLength={1}
                          className="otp-box"
                          value={digit}
                          onChange={(e) =>
                            handleOtpInputChange(e, idx, phoneOtp, setPhoneOtp, "phone-otp")
                          }
                          onKeyDown={(e) =>
                            handleOtpKeyDown(e, idx, phoneOtp, setPhoneOtp, "phone-otp")
                          }
                        />
                      ))}
                    </div>
                    <div className="otp-action-buttons">
                      <button
                        type="button"
                        className="btn-verify-otp"
                        onClick={handleVerifyPhoneOtp}
                      >
                        Verify OTP
                      </button>
                      <button
                        type="button"
                        className="btn-resend-otp"
                        onClick={handleResendPhoneOtp}
                      >
                        Resend OTP
                      </button>
                    </div>
                  </div>
                )}
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

              {/* Change Password Card / Form */}
              {!isChangingPassword ? (
                <div className="ac-sec-grid--full">
                  <div
                    className="ac-sec-action-card ac-sec-action-card--full"
                    onClick={() => setIsChangingPassword(true)}
                  >
                    <div>
                      <h4 className="ac-sec-action-title">Change Password</h4>
                      <p className="ac-sec-action-sub">Click to update your password</p>
                    </div>
                    <ChevronRight size={18} className="ac-sec-chevron" />
                  </div>
                </div>
              ) : (
                <form className="change-password-card" onSubmit={handleSavePassword}>
                  <div className="change-pass-title-row">
                    <h3 className="change-pass-title">Change Password</h3>
                    <button
                      type="button"
                      className="btn-cancel-pass"
                      onClick={() => {
                        setIsChangingPassword(false)
                        setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" })
                      }}
                    >
                      Cancel
                    </button>
                  </div>

                  <div className="form-group">
                    <label className="form-label">CURRENT PASSWORD</label>
                    <div className="input-pass-wrap">
                      <input
                        type={showPass.current ? "text" : "password"}
                        name="currentPassword"
                        className="form-input"
                        placeholder="Enter current password"
                        value={passwordForm.currentPassword}
                        onChange={handlePasswordInputChange}
                      />
                      <button
                        type="button"
                        className="btn-eye-toggle"
                        aria-label="Toggle password visibility"
                        onClick={() => toggleShowPass("current")}
                      >
                        {showPass.current ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">NEW PASSWORD</label>
                    <div className="input-pass-wrap">
                      <input
                        type={showPass.new ? "text" : "password"}
                        name="newPassword"
                        className="form-input"
                        placeholder="Enter new password"
                        value={passwordForm.newPassword}
                        onChange={handlePasswordInputChange}
                      />
                      <button
                        type="button"
                        className="btn-eye-toggle"
                        aria-label="Toggle password visibility"
                        onClick={() => toggleShowPass("new")}
                      >
                        {showPass.new ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">CONFIRM NEW PASSWORD</label>
                    <div className="input-pass-wrap">
                      <input
                        type={showPass.confirm ? "text" : "password"}
                        name="confirmPassword"
                        className="form-input"
                        placeholder="Confirm new password"
                        value={passwordForm.confirmPassword}
                        onChange={handlePasswordInputChange}
                      />
                      <button
                        type="button"
                        className="btn-eye-toggle"
                        aria-label="Toggle password visibility"
                        onClick={() => toggleShowPass("confirm")}
                      >
                        {showPass.confirm ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  <div className="change-pass-actions">
                    <button type="submit" className="btn-save">
                      Save
                    </button>
                  </div>
                </form>
              )}
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
                  Configure your real-time email and mobile notification preferences.
                </p>
              </div>
              <div className="ac-notif-actions">
                <button
                  type="button"
                  className="ac-btn-secondary"
                  onClick={handleResetNotificationDefaults}
                >
                  Reset Default
                </button>
                <button
                  type="button"
                  className="ac-btn-primary"
                  onClick={handleSaveNotificationPreferences}
                >
                  Save Preferences
                </button>
              </div>
            </div>

            <div className="ac-notif-stack">
              {/* Card 1: Email Notifications */}
              <div className="ac-card ac-email-card">
                <div className="ac-card-head">
                  <div className="ac-card-head-left">
                    <Mail size={22} className="ac-cyan-icon" />
                    <div>
                      <h3 className="ac-card-title-text">Email Notifications</h3>
                      <p className="ac-card-sub-text">
                        {isEmailVerified && formData.email
                          ? `Primary Address: ${formData.email}`
                          : "No verified email available"}
                      </p>
                    </div>
                  </div>
                  {isEmailVerified && formData.email ? (
                    <span className="ac-tag-verified">✔ VERIFIED</span>
                  ) : null}
                </div>

                {isEmailVerified && formData.email ? (
                  <div className="ac-toggle-box">
                    <div>
                      <h4 className="ac-toggle-title">Enable Email Notifications</h4>
                      <p className="ac-toggle-desc">
                        Receive real-time alerts & market updates via email.
                      </p>
                    </div>
                    <Toggle
                      on={emailNotificationsEnabled}
                      onChange={setEmailNotificationsEnabled}
                    />
                  </div>
                ) : (
                  <div className="ac-notif-unverified-box">
                    <AlertCircle size={18} />
                    <span>
                      Please add and verify an email address in your Profile page to receive email notifications.
                    </span>
                  </div>
                )}
              </div>

              {/* Card 2: Mobile Notifications */}
              <div className="ac-card ac-mobile-card">
                <div className="ac-card-head">
                  <div className="ac-card-head-left">
                    <Smartphone size={22} className="ac-cyan-icon" />
                    <div>
                      <h3 className="ac-card-title-text">Mobile Notifications</h3>
                      <p className="ac-card-sub-text">
                        {isPhoneVerified && formData.phone
                          ? `Verified Mobile Number: ${formData.phone}`
                          : "No verified mobile number available"}
                      </p>
                    </div>
                  </div>
                  {isPhoneVerified && formData.phone ? (
                    <span className="ac-tag-verified">✔ VERIFIED</span>
                  ) : null}
                </div>

                {isPhoneVerified && formData.phone ? (
                  <div className="ac-toggle-box">
                    <div>
                      <h4 className="ac-toggle-title">Enable Mobile Notifications</h4>
                      <p className="ac-toggle-desc">
                        Receive critical alerts & trade updates directly on your mobile device.
                      </p>
                    </div>
                    <Toggle
                      on={mobileNotificationsEnabled}
                      onChange={setMobileNotificationsEnabled}
                    />
                  </div>
                ) : (
                  <div className="ac-notif-unverified-box">
                    <AlertCircle size={18} />
                    <span>
                      Please add and verify a mobile number in your Profile page to receive mobile notifications.
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
