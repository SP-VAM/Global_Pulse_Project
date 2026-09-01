import { useState, useRef, useEffect } from "react"
import { Link } from "react-router-dom"
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
  Laptop,
  Globe,
  LogOut,
  Clock,
} from "lucide-react"
import "./Profile.css"
import { useUser } from "../../../context/UserContext.jsx"
import { sendOtp, verifyOtp, changePassword, getActiveSessions, revokeSession, getMe, updateProfile } from "../../../api/authApi.js"
import { getUserInitial } from "../../../utils/avatarUtils.js"

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
  const { user: globalUser, updateUser, updateAvatar } = useUser()

  // Load stored user or set default initial state per requirements:
  // Initial State: Blank avatar, empty First & Last name, empty Phone Number initially.
  // Email is pre-filled from login & verified with green check icon.
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem("user")
      if (saved) {
        const parsed = JSON.parse(saved)
        const loginMethod = parsed.loginMethod || (parsed.phone && !parsed.email ? "mobile" : "email")

        // First Name & Last Name should be empty initially unless user explicitly saved them
        const firstName = parsed.firstName || ""
        const lastName = parsed.lastName || ""

        // Email pre-filled if present, empty if null
        const rawEmail = typeof parsed.email === "string" ? parsed.email : (typeof parsed.user_email === "string" ? parsed.user_email : "")
        const email = (rawEmail && (rawEmail.includes("@mobile.globalpulse") || rawEmail.includes("@user.globalpulse") || rawEmail.includes("@globalpulse.io"))) ? "" : rawEmail
        const isEmailVerified = parsed.is_email_verified || parsed.isEmailVerified || false

        // Phone is empty initially unless explicitly verified & saved
        const isPhoneVerified = parsed.is_mobile_verified || parsed.isPhoneVerified || false
        const phone = parsed.phone || parsed.mobile_number || ""

        return {
          firstName,
          lastName,
          email,
          phone,
          avatar: parsed.avatar || null,
          isEmailVerified,
          isPhoneVerified,
        }
      }
    } catch (e) {
      console.error(e)
    }
    return {
      firstName: "",
      lastName: "",
      email: "",
      phone: "",
      avatar: null,
      isEmailVerified: false,
      isPhoneVerified: false,
    }
  })

  const [formData, setFormData] = useState({ ...user })
  const [isEmailVerified, setIsEmailVerified] = useState(user.isEmailVerified)
  const [isPhoneVerified, setIsPhoneVerified] = useState(user.isPhoneVerified)

  const [isEditingEmail, setIsEditingEmail] = useState(false)
  const [isEditingPhone, setIsEditingPhone] = useState(false)

  // Validation Error state
  const [errors, setErrors] = useState({
    firstName: "",
    lastName: "",
    email: "",
    phone: "",
    photo: "",
    emailOtp: "",
    phoneOtp: "",
  })

  // Reset Confirmation Modal state
  const [showResetModal, setShowResetModal] = useState(false)
  const [show2FaModal, setShow2FaModal] = useState(false)

  // Password Error state
  const [passwordErrors, setPasswordErrors] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  })

  // Inline OTP states
  const [showEmailOtp, setShowEmailOtp] = useState(false)
  const [showPhoneOtp, setShowPhoneOtp] = useState(false)
  const [emailOtp, setEmailOtp] = useState(["", "", "", "", "", ""])
  const [phoneOtp, setPhoneOtp] = useState(["", "", "", "", "", ""])
  const [generatedEmailOtp, setGeneratedEmailOtp] = useState("")
  const [generatedPhoneOtp, setGeneratedPhoneOtp] = useState("")
  const [isSendingEmailOtp, setIsSendingEmailOtp] = useState(false)
  const [isVerifyingEmailOtp, setIsVerifyingEmailOtp] = useState(false)
  const [isSendingPhoneOtp, setIsSendingPhoneOtp] = useState(false)
  const [isVerifyingPhoneOtp, setIsVerifyingPhoneOtp] = useState(false)

  const [notificationMsg, setNotificationMsg] = useState(null)
  const fileInputRef = useRef(null)

  // Security Tab Password Change States
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [isSubmittingPassword, setIsSubmittingPassword] = useState(false)
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

  // History of last 3 passwords to prevent reuse
  const [passwordHistory, setPasswordHistory] = useState(() => {
    try {
      const saved = localStorage.getItem("passwordHistory")
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed)) return parsed
      }
    } catch (e) {
      console.error(e)
    }
    return ["password123"]
  })

  const [twoFactor, setTwoFactor] = useState(true)

  // Active Sessions States
  const [sessions, setSessions] = useState([])
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [sessionError, setSessionError] = useState(null)
  const [revokingSessionId, setRevokingSessionId] = useState(null)
  const [confirmRevokeSession, setConfirmRevokeSession] = useState(null)

  useEffect(() => {
    let isMounted = true
    const syncBackendProfile = async () => {
      try {
        const fetchedUser = await getMe()
        if (fetchedUser && typeof fetchedUser === "object" && isMounted) {
          const fetchedPhone = fetchedUser.mobile_number || fetchedUser.mobileNumber || fetchedUser.phone || ""
          const fetchedFirstName = fetchedUser.first_name || fetchedUser.firstName || ""
          const fetchedLastName = fetchedUser.last_name || fetchedUser.lastName || ""
          const rawFetchedEmail = typeof fetchedUser.email === "string" ? fetchedUser.email : ""
          const isDummyEmail = Boolean(rawFetchedEmail && (rawFetchedEmail.includes("@globalpulse.io") || rawFetchedEmail.includes("@mobile.globalpulse") || rawFetchedEmail.includes("@user.globalpulse")))
          const fetchedEmail = isDummyEmail ? "" : rawFetchedEmail
          const isPhoneVer = Boolean(fetchedUser.is_mobile_verified || fetchedUser.isMobileVerified || fetchedUser.isPhoneVerified)
          const isEmailVer = Boolean(fetchedUser.is_email_verified || fetchedUser.isEmailVerified)

          const fetchedPhoto = fetchedUser.profile_image || fetchedUser.profileImage || fetchedUser.avatar || null
          const cleanPhoto = (typeof fetchedPhoto === "string" && fetchedPhoto.trim() && fetchedPhoto !== "null" && fetchedPhoto !== "undefined") ? fetchedPhoto.trim() : null

          setFormData((prev) => ({
            ...prev,
            firstName: fetchedFirstName || prev.firstName,
            lastName: fetchedLastName || prev.lastName,
            email: fetchedEmail,
            phone: fetchedPhone || prev.phone,
            avatar: cleanPhoto !== null ? cleanPhoto : prev.avatar,
          }))

          setUser((prev) => ({
            ...prev,
            firstName: fetchedFirstName || prev.firstName,
            lastName: fetchedLastName || prev.lastName,
            first_name: fetchedFirstName || prev.firstName,
            last_name: fetchedLastName || prev.lastName,
            email: fetchedEmail,
            phone: fetchedPhone || prev.phone,
            mobile_number: fetchedPhone || prev.phone,
            avatar: cleanPhoto !== null ? cleanPhoto : prev.avatar,
            profile_image: cleanPhoto !== null ? cleanPhoto : prev.profile_image,
          }))

          if (fetchedPhone) setIsPhoneVerified(isPhoneVer)
          if (fetchedEmail) setIsEmailVerified(isEmailVer)
        }
      } catch (err) {
        console.warn("[Profile] getMe profile sync error:", err)
      }
    }
    syncBackendProfile()
    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (activeTab === "Security" || activeTab === "security") {
      fetchActiveSessions()
    }
  }, [activeTab])

  const fetchActiveSessions = async () => {
    setLoadingSessions(true)
    setSessionError(null)
    try {
      const res = await getActiveSessions()
      setSessions(res.sessions || [])
    } catch (err) {
      console.warn("[Profile] Failed to fetch active sessions:", err)
      setSessionError("Unable to load active sessions.")
    } finally {
      setLoadingSessions(false)
    }
  }

  const handleConfirmRevoke = async () => {
    if (!confirmRevokeSession) return
    const targetId = confirmRevokeSession.sessionId || confirmRevokeSession.session_id
    setRevokingSessionId(targetId)
    try {
      await revokeSession(targetId)
      showNotification("Session signed out successfully.", "success")
      setConfirmRevokeSession(null)
      fetchActiveSessions()
    } catch (err) {
      showNotification(err.message || "Failed to sign out session.", "error")
    } finally {
      setRevokingSessionId(null)
    }
  }

  const handleToggle2FA = (newVal) => {
    if (!newVal) {
      // User is disabling 2FA -> Show confirmation modal
      setShow2FaModal(true)
    } else {
      setTwoFactor(true)
      showNotification("Two-Factor Authentication enabled.", "success")
    }
  }

  // Simplified Notification States
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
    setIsEmailVerified(user.isEmailVerified)
    setIsPhoneVerified(user.isPhoneVerified)
  }, [user])

  const showNotification = (msg, type = "success") => {
    setNotificationMsg({ msg, type })
    setTimeout(() => setNotificationMsg(null), 4000)
  }

  // --- VALIDATION HELPERS ---
  const validateFirstName = (val) => {
    if (!val || val.trim() === "") {
      return ""
    }
    const lettersOnlyRegex = /^[A-Za-z\s]+$/
    if (!lettersOnlyRegex.test(val)) {
      return "First name should contain only letters."
    }
    if (val.trim().length > 50) {
      return "First name must be at most 50 characters."
    }
    return ""
  }

  const validateLastName = (val) => {
    if (!val || val.trim() === "") {
      return ""
    }
    const lettersOnlyRegex = /^[A-Za-z\s]+$/
    if (!lettersOnlyRegex.test(val)) {
      return "Last name should contain only letters."
    }
    if (val.trim().length > 50) {
      return "Last name must be at most 50 characters."
    }
    return ""
  }


  const VALID_TLDS = new Set([
    "com", "in", "org", "net", "edu", "gov", "co", "io", "me", "ai", "info", "biz",
    "dev", "app", "tech", "online", "site", "store", "global", "live", "pro", "tv",
    "xyz", "us", "uk", "ca", "au", "de", "fr", "jp", "cn", "br", "za", "eu", "cc",
    "asia", "name", "mobi", "tel", "travel", "museum", "jobs", "cat", "coop", "int",
    "mil", "arpa", "mx", "es", "it", "nl", "se", "no", "fi", "dk", "pl", "cz",
    "ch", "at", "be", "nz", "sg", "hk", "tw", "kr", "my", "id", "ph", "vn", "th",
    "pk", "bd", "ng", "eg", "ke", "sa", "ae", "il", "ir", "tr", "ua", "ro", "gr",
    "hu", "pt", "ie", "is", "cl", "pe", "ar", "ve", "ec", "py", "uy", "cloud",
    "agency", "digital", "design", "media", "studio", "center", "group", "email",
    "solutions", "company", "systems", "finance", "technology", "estate", "insurance",
    "international", "photography", "software", "services", "support", "network",
    "world", "life", "today", "space", "zone", "works", "expert", "guru", "ninja",
    "academy", "training", "events", "direct", "market", "shop"
  ])

  const validateEmail = (val) => {
    if (!val || val.trim() === "") {
      return "Please enter a valid email address."
    }

    // Do not allow spaces anywhere
    if (/\s/.test(val)) {
      return "Please enter a valid email address."
    }

    // Must contain exactly one @
    const atCount = (val.match(/@/g) || []).length
    if (atCount !== 1) {
      return "Please enter a valid email address."
    }

    const parts = val.split("@")
    const localPart = parts[0]
    const domainPart = parts[1]

    // Local part validation
    if (!localPart) {
      return "Please enter a valid email address."
    }

    // Local part allowed: letters a-z, A-Z, numbers 0-9, ., _, -
    // Do NOT allow emojis or invalid symbols (#, %, &, *, (, ), =, +, /, ?, !, etc.)
    if (!/^[a-zA-Z0-9._-]+$/.test(localPart)) {
      return "Please enter a valid email address."
    }

    // Local part should not start or end with .
    if (localPart.startsWith(".") || localPart.endsWith(".")) {
      return "Please enter a valid email address."
    }

    // Local part cannot contain consecutive dots ..
    if (/\.\./.test(localPart)) {
      return "Please enter a valid email address."
    }

    // Domain part validation
    if (!domainPart) {
      return "Please enter a valid email address."
    }

    // Domain must contain only letters, numbers, hyphen -, dot .
    // Do NOT allow spaces, _, @, special characters
    if (!/^[a-zA-Z0-9.-]+$/.test(domainPart)) {
      return "Please enter a valid email address."
    }

    // Domain cannot contain consecutive dots ..
    if (/\.\./.test(domainPart)) {
      return "Please enter a valid email address."
    }

    // Domain starting or ending with .
    if (domainPart.startsWith(".") || domainPart.endsWith(".")) {
      return "Please enter a valid email address."
    }

    const domainLabels = domainPart.split(".")

    // Domain must have at least domain name and TLD (e.g. gmail.com)
    if (domainLabels.length < 2) {
      return "Please enter a valid email address."
    }

    for (let i = 0; i < domainLabels.length; i++) {
      const label = domainLabels[i]
      if (!label) {
        return "Please enter a valid email address."
      }
      // Domain label starting or ending with hyphen -
      if (label.startsWith("-") || label.endsWith("-")) {
        return "Please enter a valid email address."
      }
    }

    // Validate TLD labels (all domain labels after index 0)
    for (let i = 1; i < domainLabels.length; i++) {
      const tldLabel = domainLabels[i].toLowerCase()
      if (!VALID_TLDS.has(tldLabel)) {
        return "Please enter a valid email address."
      }
    }

    return ""
  }

  const validatePhone = (val, isAttemptedNonDigit = false) => {
    if (isAttemptedNonDigit) {
      return "Only numbers are allowed."
    }
    if (!val || val.trim() === "") {
      return ""
    }
    const firstDigit = val.charAt(0)
    if (!["6", "7", "8", "9"].includes(firstDigit)) {
      return "Indian mobile number must start with 6, 7, 8, or 9."
    }
    if (val.length < 10) {
      return "Indian mobile number must contain exactly 10 digits."
    }
    const phoneRegex = /^[6-9][0-9]{9}$/
    if (!phoneRegex.test(val)) {
      return "Indian mobile number must contain exactly 10 digits."
    }
    return ""
  }

  const validatePhoto = (file) => {
    if (!file) return ""
    const validTypes = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    const fileNameLower = file.name.toLowerCase()
    const hasValidExt = /\.(jpg|jpeg|png|webp)$/i.test(fileNameLower)
    const isTypeValid = validTypes.includes(file.type) || hasValidExt

    if (fileNameLower.endsWith(".svg") || file.type === "image/svg+xml") {
      return "SVG files are not supported. Please upload a JPEG, PNG, or WebP image."
    }

    if (!isTypeValid || file.size > 2 * 1024 * 1024) {
      return "Please upload a valid JPEG, PNG, or WebP image file up to 2 MB."
    }
    return ""
  }

  const handlePhotoUpload = (e) => {
    const file = e.target.files[0]
    if (file) {
      const photoErr = validatePhoto(file)
      if (photoErr) {
        setErrors((prev) => ({ ...prev, photo: photoErr }))
        showNotification(photoErr, "error")
        e.target.value = ""
        return
      }

      setErrors((prev) => ({ ...prev, photo: "" }))
      const reader = new FileReader()
      reader.onloadend = async () => {
        const newAvatar = reader.result
        try {
          showNotification("Uploading profile photo...", "info")
          const updatedUser = await updateProfile({ profile_image: newAvatar })
          if (updatedUser) {
            setFormData((prev) => ({ ...prev, avatar: newAvatar }))
            setUser((prev) => ({ ...prev, avatar: newAvatar }))
            updateAvatar(newAvatar)
            showNotification("Photo updated and saved successfully!", "success")
          }
        } catch (apiErr) {
          console.error("Photo upload backend error:", apiErr)
          const errorMsg = apiErr.message || "Failed to save profile photo to server."
          setErrors((prev) => ({ ...prev, photo: errorMsg }))
          showNotification(errorMsg, "error")
        } finally {
          e.target.value = ""
        }
      }
      reader.readAsDataURL(file)
    }
  }

  const handleRemovePhoto = async () => {
    try {
      showNotification("Removing profile photo...", "info")
      await updateProfile({ profile_image: "" })
      setFormData((prev) => ({ ...prev, avatar: null }))
      setUser((prev) => ({ ...prev, avatar: null }))
      setErrors((prev) => ({ ...prev, photo: "" }))
      updateAvatar(null)
      showNotification("Photo removed successfully", "info")
    } catch (apiErr) {
      console.error("Remove photo backend error:", apiErr)
      const errorMsg = apiErr.message || "Failed to remove profile photo on server."
      showNotification(errorMsg, "error")
    }
  }


  // --- PASSWORD VALIDATION HELPERS ---
  const validateCurrentPassword = (val) => {
    const trimmed = (val || "").trim()
    if (!trimmed) {
      return "Please enter your current password."
    }
    return ""
  }

  const validateNewPassword = (val, currentPassVal) => {
    const trimmedVal = (val || "").trim()
    if (!trimmedVal) {
      return "Please enter a new password."
    }

    const isReused =
      (currentPassVal && trimmedVal === currentPassVal.trim()) ||
      passwordHistory.some((pastPass) => pastPass === trimmedVal)

    if (isReused) {
      return "You cannot reuse any of your last 3 passwords."
    }

    const hasUpper = /[A-Z]/.test(val)
    const hasLower = /[a-z]/.test(val)
    const hasNum = /[0-9]/.test(val)
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(val)

    if (val.length < 8 || !hasUpper || !hasLower || !hasNum || !hasSpecial || /^\s+$/.test(val)) {
      return "Password must contain at least 8 characters, including uppercase, lowercase, number, and special character."
    }
    return ""
  }

  const validateConfirmPassword = (val, newPassVal) => {
    if (!val) {
      return "Please confirm your new password."
    }
    if (val !== newPassVal) {
      return "Passwords do not match."
    }
    return ""
  }

  // Password Change Handlers
  const handlePasswordInputChange = (e) => {
    const { name, value } = e.target
    setPasswordForm((prev) => {
      const updated = { ...prev, [name]: value }

      let err = ""
      if (name === "currentPassword") {
        err = validateCurrentPassword(value)
      } else if (name === "newPassword") {
        err = validateNewPassword(value, updated.currentPassword)
        if (updated.confirmPassword) {
          const confirmErr = validateConfirmPassword(updated.confirmPassword, value)
          setPasswordErrors((prevErrs) => ({ ...prevErrs, confirmPassword: confirmErr }))
        }
      } else if (name === "confirmPassword") {
        err = validateConfirmPassword(value, updated.newPassword)
      }

      setPasswordErrors((prevErrs) => ({ ...prevErrs, [name]: err }))
      return updated
    })
  }

  const toggleShowPass = (field) => {
    setShowPass((prev) => ({ ...prev, [field]: !prev[field] }))
  }

  const handleCancelPassword = () => {
    setIsChangingPassword(false)
    setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" })
    setPasswordErrors({ currentPassword: "", newPassword: "", confirmPassword: "" })
    setShowPass({ current: false, new: false, confirm: false })
  }

  const handleUpdatePassword = async (e) => {
    e.preventDefault()
    if (isSubmittingPassword) return

    const { currentPassword, newPassword, confirmPassword } = passwordForm

    const curErr = validateCurrentPassword(currentPassword)
    const newErr = validateNewPassword(newPassword, currentPassword)
    const confErr = validateConfirmPassword(confirmPassword, newPassword)

    const errs = {
      currentPassword: curErr,
      newPassword: newErr,
      confirmPassword: confErr,
    }

    setPasswordErrors(errs)

    if (curErr || newErr || confErr) {
      const firstMsg = curErr || newErr || confErr
      showNotification(firstMsg, "error")
      return
    }

    try {
      setIsSubmittingPassword(true)
      const res = await changePassword({
        currentPassword: currentPassword,
        newPassword: newPassword,
        confirmPassword: confirmPassword,
      })

      setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" })
      setPasswordErrors({ currentPassword: "", newPassword: "", confirmPassword: "" })
      setShowPass({ current: false, new: false, confirm: false })
      setIsChangingPassword(false)
      showNotification(res.message || "Password updated successfully.", "success")
    } catch (err) {
      console.error("Change password error:", err)
      const errorMsg = err.message || "Failed to update password."
      if (errorMsg.toLowerCase().includes("current password")) {
        setPasswordErrors((prev) => ({ ...prev, currentPassword: "Current password is incorrect." }))
      }
      showNotification(errorMsg, "error")
    } finally {
      setIsSubmittingPassword(false)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target

    if (name === "phone") {
      let rawVal = value
      const hasNonDigits = /[^0-9]/.test(rawVal)
      let cleanVal = rawVal.replace(/[^0-9]/g, "")

      if (cleanVal.length > 10 && cleanVal.startsWith("91")) {
        cleanVal = cleanVal.slice(2)
      }
      cleanVal = cleanVal.slice(0, 10)

      setFormData((prev) => ({ ...prev, phone: cleanVal }))

      let err = ""
      if (hasNonDigits) {
        err = "Only numbers are allowed."
      } else {
        err = validatePhone(cleanVal)
      }

      if (cleanVal !== user.phone || !user.isPhoneVerified) {
        setIsPhoneVerified(false)
        setIsEditingPhone(true)
      }
      setErrors((prev) => ({ ...prev, phone: err }))
      return
    }

    if (name === "email") {
      let rawVal = value
      // Block invalid characters immediately while typing and when pasting:
      // Allow only letters, numbers, dot, underscore, hyphen, and @
      let cleanVal = rawVal.replace(/[^a-zA-Z0-9._@-]/g, "")

      // Allow at most one @ symbol
      const atIdx = cleanVal.indexOf("@")
      if (atIdx !== -1) {
        cleanVal = cleanVal.slice(0, atIdx + 1) + cleanVal.slice(atIdx + 1).replace(/@/g, "")
      }

      setFormData((prev) => ({ ...prev, email: cleanVal }))

      const err = validateEmail(cleanVal)
      if (cleanVal !== user.email || !user.isEmailVerified) {
        setIsEmailVerified(false)
        setIsEditingEmail(true)
      }
      setErrors((prev) => ({ ...prev, email: err }))
      return
    }

    setFormData((prev) => ({ ...prev, [name]: value }))

    let err = ""
    if (name === "firstName") {
      err = validateFirstName(value)
    } else if (name === "lastName") {
      err = validateLastName(value)
    }

    setErrors((prev) => ({ ...prev, [name]: err }))
  }

  const handleEmailPaste = (e) => {
    e.preventDefault()
    const pastedText = e.clipboardData.getData("text") || ""
    let cleanPasted = pastedText.replace(/[^a-zA-Z0-9._@-]/g, "")

    const inputEl = e.target
    const start = inputEl.selectionStart || 0
    const end = inputEl.selectionEnd || 0
    const currentVal = formData.email || ""
    let newValRaw = currentVal.slice(0, start) + cleanPasted + currentVal.slice(end)

    let cleanVal = newValRaw.replace(/[^a-zA-Z0-9._@-]/g, "")
    const atIdx = cleanVal.indexOf("@")
    if (atIdx !== -1) {
      cleanVal = cleanVal.slice(0, atIdx + 1) + cleanVal.slice(atIdx + 1).replace(/@/g, "")
    }

    setFormData((prev) => ({ ...prev, email: cleanVal }))
    const err = validateEmail(cleanVal)
    if (cleanVal !== user.email || !user.isEmailVerified) {
      setIsEmailVerified(false)
      setIsEditingEmail(true)
    }
    setErrors((prev) => ({ ...prev, email: err }))
  }

  // Email Flow Actions
  const handleEditEmailClick = () => {
    setIsEditingEmail(true)
    setShowEmailOtp(false)
    setErrors((prev) => ({ ...prev, email: "", emailOtp: "" }))
  }

  const handleCancelEmailClick = () => {
    setIsEditingEmail(false)
    setShowEmailOtp(false)
    setFormData((prev) => ({ ...prev, email: user?.email || "" }))
    setErrors((prev) => ({ ...prev, email: "", emailOtp: "" }))
  }

  const handleSendEmailOtp = async () => {
    if (isSendingEmailOtp) return
    if (!formData.email || !formData.email.trim()) {
      const msg = "Please enter an email address before requesting email verification."
      setErrors((prev) => ({ ...prev, email: msg }))
      showNotification(msg, "error")
      return
    }
    const emailErr = validateEmail(formData.email)
    if (emailErr) {
      setErrors((prev) => ({ ...prev, email: emailErr }))
      showNotification(emailErr, "error")
      return
    }
    setErrors((prev) => ({ ...prev, email: "", emailOtp: "" }))
    try {
      setIsSendingEmailOtp(true)
      showNotification(`Sending verification code to ${formData.email}...`, "info")
      await sendOtp({ target: formData.email, channel: "EMAIL", purpose: "PROFILE_CHANGE" })
      setEmailOtp(["", "", "", "", "", ""])
      setShowEmailOtp(true)
      showNotification(`Verification code sent to ${formData.email}. Please check your inbox.`, "success")
    } catch (err) {
      const msg = err.message || "Failed to send email verification code."
      setErrors((prev) => ({ ...prev, email: msg }))
      showNotification(msg, "error")
    } finally {
      setIsSendingEmailOtp(false)
    }
  }

  const handleVerifyEmailOtp = async () => {
    if (isVerifyingEmailOtp) return
    const code = emailOtp.join("")
    if (code.length !== 6 || !/^\d{6}$/.test(code)) {
      setErrors((prev) => ({ ...prev, emailOtp: "Please enter a valid 6-digit OTP." }))
      showNotification("Please enter a valid 6-digit OTP.", "error")
      return
    }

    try {
      setIsVerifyingEmailOtp(true)
      await verifyOtp({ target: formData.email, channel: "EMAIL", purpose: "PROFILE_CHANGE", otpCode: code })
      setIsEmailVerified(true)
      setIsEditingEmail(false)
      setShowEmailOtp(false)
      setErrors((prev) => ({ ...prev, emailOtp: "", email: "" }))
      showNotification("Email address verified successfully!", "success")
    } catch (err) {
      const msg = err.message || "Invalid OTP code. Verification failed."
      setErrors((prev) => ({ ...prev, emailOtp: msg }))
      showNotification(msg, "error")
    } finally {
      setIsVerifyingEmailOtp(false)
    }
  }

  const handleResendEmailOtp = async () => {
    if (isSendingEmailOtp) return
    try {
      setIsSendingEmailOtp(true)
      showNotification(`Resending verification code to ${formData.email}...`, "info")
      await sendOtp({ target: formData.email, channel: "EMAIL", purpose: "PROFILE_CHANGE" })
      setEmailOtp(["", "", "", "", "", ""])
      setErrors((prev) => ({ ...prev, emailOtp: "" }))
      showNotification(`New verification code sent to ${formData.email}.`, "success")
    } catch (err) {
      const msg = err.message || "Failed to resend email verification code."
      showNotification(msg, "error")
    } finally {
      setIsSendingEmailOtp(false)
    }
  }

  // Phone Flow Actions
  const handleEditPhoneClick = () => {
    setIsEditingPhone(true)
    setShowPhoneOtp(false)
    setErrors((prev) => ({ ...prev, phone: "", phoneOtp: "" }))
  }

  const handleCancelPhoneClick = () => {
    setIsEditingPhone(false)
    setShowPhoneOtp(false)
    setFormData((prev) => ({ ...prev, phone: user?.phone || "" }))
    setErrors((prev) => ({ ...prev, phone: "", phoneOtp: "" }))
  }

  const handleSendPhoneOtp = async () => {
    if (isSendingPhoneOtp) return
    if (!formData.phone || formData.phone.trim() === "") {
      const err = "Please enter your phone number."
      setErrors((prev) => ({ ...prev, phone: err }))
      showNotification(err, "error")
      return
    }
    const phoneErr = validatePhone(formData.phone)
    if (phoneErr) {
      setErrors((prev) => ({ ...prev, phone: phoneErr }))
      showNotification(phoneErr, "error")
      return
    }
    setErrors((prev) => ({ ...prev, phone: "", phoneOtp: "" }))
    try {
      setIsSendingPhoneOtp(true)
      showNotification(`Sending verification SMS to ${formData.phone}...`, "info")
      await sendOtp({ target: formData.phone, channel: "SMS", purpose: "PROFILE_CHANGE" })
      setPhoneOtp(["", "", "", "", "", ""])
      setShowPhoneOtp(true)
      showNotification(`Verification SMS sent to ${formData.phone}.`, "success")
    } catch (err) {
      const msg = err.message || "Failed to send SMS verification code."
      setErrors((prev) => ({ ...prev, phone: msg }))
      showNotification(msg, "error")
    } finally {
      setIsSendingPhoneOtp(false)
    }
  }

  const handleVerifyPhoneOtp = async () => {
    if (isVerifyingPhoneOtp) return
    const code = phoneOtp.join("")
    if (code.length !== 6 || !/^\d{6}$/.test(code)) {
      setErrors((prev) => ({ ...prev, phoneOtp: "Please enter a valid 6-digit OTP." }))
      showNotification("Please enter a valid 6-digit OTP.", "error")
      return
    }

    try {
      setIsVerifyingPhoneOtp(true)
      await verifyOtp({ target: formData.phone, channel: "SMS", purpose: "PROFILE_CHANGE", otpCode: code })
      setIsPhoneVerified(true)
      setIsEditingPhone(false)
      setShowPhoneOtp(false)
      setErrors((prev) => ({ ...prev, phoneOtp: "", phone: "" }))
      showNotification("Phone number verified successfully.", "success")
    } catch (err) {
      const msg = err.message || "Invalid OTP code. Verification failed."
      setErrors((prev) => ({ ...prev, phoneOtp: msg }))
      showNotification(msg, "error")
    } finally {
      setIsVerifyingPhoneOtp(false)
    }
  }

  const handleResendPhoneOtp = async () => {
    if (isSendingPhoneOtp) return
    try {
      setIsSendingPhoneOtp(true)
      showNotification(`Resending verification SMS to ${formData.phone}...`, "info")
      await sendOtp({ target: formData.phone, channel: "SMS", purpose: "PROFILE_CHANGE" })
      setPhoneOtp(["", "", "", "", "", ""])
      setErrors((prev) => ({ ...prev, phoneOtp: "" }))
      showNotification(`New verification SMS sent to ${formData.phone}.`, "success")
    } catch (err) {
      const msg = err.message || "Failed to resend SMS verification code."
      showNotification(msg, "error")
    } finally {
      setIsSendingPhoneOtp(false)
    }
  }



  // OTP Input navigation & numeric digit filter
  const handleOtpInputChange = (e, idx, otpState, setOtpState, inputPrefix, fieldName) => {
    const val = e.target.value
    const sanitized = val.replace(/[^0-9]/g, "")
    if (val && !sanitized) return

    const newOtp = [...otpState]
    newOtp[idx] = sanitized ? sanitized.slice(-1) : ""
    setOtpState(newOtp)

    if (fieldName) {
      setErrors((prev) => ({ ...prev, [fieldName]: "" }))
    }

    if (sanitized && idx < 5) {
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
    setFormData({ ...user })
    setIsEditingEmail(false)
    setIsEditingPhone(false)
    setIsEmailVerified(user?.isEmailVerified || false)
    setIsPhoneVerified(user?.isPhoneVerified || false)
    setShowEmailOtp(false)
    setShowPhoneOtp(false)
    setEmailOtp(["", "", "", "", "", ""])
    setPhoneOtp(["", "", "", "", "", ""])
    setErrors({
      firstName: "",
      lastName: "",
      email: "",
      phone: "",
      photo: "",
      emailOtp: "",
      phoneOtp: "",
    })
    showNotification("Form reset to current profile state", "info")
  }

  const handleSaveChanges = async (e) => {
    e.preventDefault()

    const fnErr = validateFirstName(formData.firstName)
    const lnErr = validateLastName(formData.lastName)
    const emailErr = validateEmail(formData.email)
    const phoneErr = validatePhone(formData.phone)

    const newErrors = {
      firstName: fnErr,
      lastName: lnErr,
      email: emailErr,
      phone: phoneErr,
      photo: errors.photo || "",
      emailOtp: errors.emailOtp || "",
      phoneOtp: errors.phoneOtp || "",
    }

    setErrors(newErrors)

    if (fnErr || lnErr || emailErr || phoneErr || errors.photo) {
      const firstMsg = fnErr || lnErr || emailErr || phoneErr || errors.photo
      showNotification(firstMsg, "error")
      return
    }

    if (showEmailOtp || (!isEmailVerified && formData.email !== user.email)) {
      showNotification("Please complete email OTP verification before saving changes.", "error")
      return
    }

    if (showPhoneOtp || (formData.phone && !isPhoneVerified && formData.phone !== user.phone)) {
      showNotification("Please complete phone OTP verification before saving changes.", "error")
      return
    }

    const nameChanged =
      (formData.firstName || "").trim() !== (user?.firstName || "").trim() ||
      (formData.lastName || "").trim() !== (user?.lastName || "").trim()

    const emailChanged =
      (formData.email || "").trim().toLowerCase() !== (user?.email || "").trim().toLowerCase()

    const phoneChanged =
      (formData.phone || "").trim() !== (user?.phone || "").trim()

    const photoChanged =
      formData.avatar !== user?.avatar

    const changedFields = []
    if (nameChanged) changedFields.push("name")
    if (emailChanged) changedFields.push("email")
    if (phoneChanged) changedFields.push("phone")
    if (photoChanged) changedFields.push("photo")

    if (changedFields.length === 0) {
      showNotification("No changes were made to your profile.", "info")
      return
    }

    let toastMessage = "Profile updated successfully."
    if (changedFields.length === 1) {
      if (nameChanged) toastMessage = "Name updated successfully."
      else if (emailChanged) toastMessage = "Email address updated successfully."
      else if (phoneChanged) toastMessage = "Phone number updated successfully."
      else if (photoChanged) toastMessage = "Profile photo updated successfully."
    } else {
      toastMessage = "Profile updated successfully."
    }

    try {
      const resp = await updateProfile({
        firstName: (formData.firstName || "").trim(),
        lastName: (formData.lastName || "").trim(),
        mobileNumber: formData.phone,
        email: formData.email,
      })

      const updatedUser = {
        ...formData,
        firstName: resp?.first_name !== undefined ? resp.first_name : formData.firstName,
        lastName: resp?.last_name !== undefined ? resp.last_name : formData.lastName,
        first_name: resp?.first_name !== undefined ? resp.first_name : formData.firstName,
        last_name: resp?.last_name !== undefined ? resp.last_name : formData.lastName,
        full_name: `${formData.firstName} ${formData.lastName}`.trim(),
        mobile_number: resp?.mobile_number !== undefined ? resp.mobile_number : formData.phone,
        phone: resp?.mobile_number !== undefined ? resp.mobile_number : formData.phone,
        isEmailVerified,
        isPhoneVerified,
      }

      setUser(updatedUser)
      updateUser(updatedUser)
      showNotification(toastMessage, "success")
    } catch (apiErr) {
      console.error("[Profile] Backend updateProfile failed:", apiErr)
      const msg = apiErr.message || "Failed to save profile changes to server."
      showNotification(msg, "error")
    }
  }


  const currentTab = activeTab.toLowerCase()

  const userInitial = getUserInitial({
    first_name: formData.firstName || user?.firstName || globalUser?.first_name,
    firstName: formData.firstName || user?.firstName || globalUser?.first_name,
    last_name: formData.lastName || user?.lastName || globalUser?.last_name,
    lastName: formData.lastName || user?.lastName || globalUser?.last_name,
    username: user?.username || globalUser?.username,
    email: formData.email || user?.email || globalUser?.email,
  })

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

      {/* Header */}
      <div className="profile-header">
        <div>
          <h1 className="profile-title">Profile Settings</h1>
          <p className="profile-subtitle">
            Manage your personal information, security options, and notifications
          </p>
        </div>
      </div>

      <div className={`profile-grid${currentTab !== "profile" ? " profile-grid--single-panel" : ""}`}>
        {/* Column 1: Compact Navigation */}
        <aside className="profile-nav-card">
          <button
            type="button"
            className={`profile-nav-item ${currentTab === "profile" ? "is-active" : ""}`}
            onClick={() => setActiveTab("Profile")}
          >
            <User size={18} />
            <span>Profile</span>
          </button>
          <button
            type="button"
            className={`profile-nav-item ${currentTab === "security" ? "is-active" : ""}`}
            onClick={() => setActiveTab("Security")}
          >
            <Shield size={18} />
            <span>Security</span>
          </button>
          <button
            type="button"
            className={`profile-nav-item ${currentTab === "notification" ? "is-active" : ""}`}
            onClick={() => setActiveTab("Notification")}
          >
            <Bell size={18} />
            <span>Notification</span>
          </button>
        </aside>

        {/* Tab 1: Profile (Columns 2 & 3) */}
        {currentTab === "profile" && (
          <>
            {/* Column 2: Compact Profile Summary */}
            <div className="profile-summary-card">
              <div className="profile-avatar-ring">
                {formData.avatar ? (
                  <img
                    src={formData.avatar}
                    alt="Profile Avatar"
                    className="avatar-image"
                  />
                ) : (
                  <span className="profile-initial-avatar">
                    {userInitial}
                  </span>
                )}
              </div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handlePhotoUpload}
                accept="image/png, image/jpeg, image/jpg, image/webp"
                hidden
              />
              <div className="profile-avatar-actions">
                <button
                  type="button"
                  className="btn-change-photo"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Change Photo
                </button>
                <span className="action-dot">•</span>
                <button
                  type="button"
                  className="btn-remove-photo"
                  onClick={handleRemovePhoto}
                >
                  Remove
                </button>
              </div>
              {errors.photo && (
                <span className="field-error field-error--center">
                  <AlertCircle size={13} /> {errors.photo}
                </span>
              )}


            </div>

            {/* Column 3: Account Form Card */}
            <form className="profile-form-card" onSubmit={handleSaveChanges} noValidate>
              <h2 className="form-card-title">Account Information</h2>

              <div className="form-row--two-col">
                <div className="form-group">
                  <label className="form-label">First Name</label>
                  <input
                    type="text"
                    name="firstName"
                    maxLength={25}
                    className={`form-input${errors.firstName ? " form-input--error" : ""}`}
                    placeholder="Enter First Name"
                    value={formData.firstName}
                    onChange={handleInputChange}
                  />
                  {errors.firstName && (
                    <span className="field-error">
                      <AlertCircle size={13} /> {errors.firstName}
                    </span>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label">Last Name</label>
                  <input
                    type="text"
                    name="lastName"
                    maxLength={25}
                    className={`form-input${errors.lastName ? " form-input--error" : ""}`}
                    placeholder="Enter Last Name"
                    value={formData.lastName}
                    onChange={handleInputChange}
                  />
                  {errors.lastName && (
                    <span className="field-error">
                      <AlertCircle size={13} /> {errors.lastName}
                    </span>
                  )}
                </div>
              </div>

              {/* EMAIL ADDRESS FIELD */}
              <div className="form-group">
                <label className="form-label">Email Address</label>
                <div className="input-with-action">
                  <input
                    type="email"
                    name="email"
                    className={`form-input${isEmailVerified && !isEditingEmail ? " form-input--verified" : ""}${errors.email ? " form-input--error" : ""}`}
                    value={formData.email}
                    onChange={handleInputChange}
                    onPaste={handleEmailPaste}
                    onKeyDown={(e) => {
                      if (e.key === " ") {
                        e.preventDefault()
                      }
                    }}
                    placeholder="Enter Email Address"
                    readOnly={!isEditingEmail}
                  />
                  <div className="action-buttons">
                    {!isEditingEmail ? (
                      <>
                        {isEmailVerified && (
                          <span className="verified-badge" title="Verified Email">
                            <CheckCircle2 size={18} className="icon-emerald" />
                          </span>
                        )}
                        <button
                          type="button"
                          className="btn-edit-icon"
                          aria-label="Edit Email"
                          onClick={handleEditEmailClick}
                        >
                          <Pencil size={15} />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn-send-request"
                          disabled={isSendingEmailOtp}
                          onClick={handleSendEmailOtp}
                        >
                          {isSendingEmailOtp ? "Sending..." : "SEND REQUEST"}
                        </button>
                        <button
                          type="button"
                          className="btn-cancel-edit"
                          aria-label="Cancel Editing Email"
                          onClick={handleCancelEmailClick}
                          title="Cancel editing"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: "6px 12px",
                            fontSize: "12px",
                            fontWeight: "600",
                            color: "#94a3b8",
                            background: "rgba(255, 255, 255, 0.05)",
                            border: "1px solid rgba(255, 255, 255, 0.1)",
                            borderRadius: "6px",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                        >
                          Cancel
                        </button>
                      </>
                    )}
                  </div>
                </div>
                {errors.email && (
                  <span className="field-error">
                    <AlertCircle size={13} /> {errors.email}
                  </span>
                )}

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
                          className={`otp-box${errors.emailOtp ? " otp-box--error" : ""}`}
                          value={digit}
                          onChange={(e) =>
                            handleOtpInputChange(e, idx, emailOtp, setEmailOtp, "email-otp", "emailOtp")
                          }
                          onKeyDown={(e) =>
                            handleOtpKeyDown(e, idx, emailOtp, setEmailOtp, "email-otp")
                          }
                        />
                      ))}
                    </div>
                    {errors.emailOtp && (
                      <span className="field-error">
                        <AlertCircle size={13} /> {errors.emailOtp}
                      </span>
                    )}
                    <div className="otp-action-buttons">
                      <button
                        type="button"
                        className="btn-verify-otp"
                        disabled={isVerifyingEmailOtp}
                        onClick={handleVerifyEmailOtp}
                      >
                        {isVerifyingEmailOtp ? "Verifying..." : "Verify OTP"}
                      </button>
                      <button
                        type="button"
                        className="btn-resend-otp"
                        disabled={isSendingEmailOtp}
                        onClick={handleResendEmailOtp}
                      >
                        {isSendingEmailOtp ? "Sending..." : "Resend OTP"}
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
                    maxLength={10}
                    inputMode="numeric"
                    pattern="[6-9][0-9]{9}"
                    className={`form-input${isPhoneVerified && !isEditingPhone ? " form-input--verified" : ""}${errors.phone ? " form-input--error" : ""}`}
                    value={formData.phone}
                    onChange={handleInputChange}
                    placeholder="Enter 10-digit Indian Mobile Number"
                    readOnly={!isEditingPhone}
                  />
                  <div className="action-buttons">
                    {!isEditingPhone ? (
                      <>
                        {isPhoneVerified && (
                          <span className="verified-badge" title="Verified Phone">
                            <CheckCircle2 size={18} className="icon-emerald" />
                          </span>
                        )}
                        <button
                          type="button"
                          className="btn-edit-icon"
                          aria-label="Edit Phone"
                          onClick={handleEditPhoneClick}
                        >
                          <Pencil size={15} />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn-send-request"
                          disabled={isSendingPhoneOtp}
                          onClick={handleSendPhoneOtp}
                        >
                          {isSendingPhoneOtp ? "Sending..." : "SEND REQUEST"}
                        </button>
                        <button
                          type="button"
                          className="btn-cancel-edit"
                          aria-label="Cancel Editing Phone"
                          onClick={handleCancelPhoneClick}
                          title="Cancel editing"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: "6px 12px",
                            fontSize: "12px",
                            fontWeight: "600",
                            color: "#94a3b8",
                            background: "rgba(255, 255, 255, 0.05)",
                            border: "1px solid rgba(255, 255, 255, 0.1)",
                            borderRadius: "6px",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                        >
                          Cancel
                        </button>
                      </>
                    )}
                  </div>
                </div>
                {errors.phone && (
                  <span className="field-error">
                    <AlertCircle size={13} /> {errors.phone}
                  </span>
                )}

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
                          className={`otp-box${errors.phoneOtp ? " otp-box--error" : ""}`}
                          value={digit}
                          onChange={(e) =>
                            handleOtpInputChange(e, idx, phoneOtp, setPhoneOtp, "phone-otp", "phoneOtp")
                          }
                          onKeyDown={(e) =>
                            handleOtpKeyDown(e, idx, phoneOtp, setPhoneOtp, "phone-otp")
                          }
                        />
                      ))}
                    </div>
                    {errors.phoneOtp && (
                      <span className="field-error">
                        <AlertCircle size={13} /> {errors.phoneOtp}
                      </span>
                    )}
                    <div className="otp-action-buttons">
                      <button
                        type="button"
                        className="btn-verify-otp"
                        disabled={isVerifyingPhoneOtp}
                        onClick={handleVerifyPhoneOtp}
                      >
                        {isVerifyingPhoneOtp ? "Verifying..." : "Verify OTP"}
                      </button>
                      <button
                        type="button"
                        className="btn-resend-otp"
                        disabled={isSendingPhoneOtp}
                        onClick={handleResendPhoneOtp}
                      >
                        {isSendingPhoneOtp ? "Sending..." : "Resend OTP"}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="profile-footer-actions">
                <button
                  type="button"
                  className="btn-reset"
                  onClick={() => setShowResetModal(true)}
                >
                  Reset to Defaults
                </button>
                <button type="submit" className="btn-save">
                  Save Changes
                </button>
              </div>
            </form>
          </>
        )}

        {/* TAB 2: SECURITY */}
        {currentTab === "security" && (
          <div className="profile-tab-content">
            <div className="profile-sec-card">
              <div className="ac-sec-header">
                <Shield size={20} className="ac-sec-title-icon" />
                <h2 className="ac-sec-title">Security & Privacy</h2>
              </div>

              {/* Two Factor Auth Block */}
              <div className="ac-2fa-block">
                <div className="ac-2fa-left">
                  <div className="ac-2fa-icon-box">
                    <Smartphone size={18} />
                  </div>
                  <div>
                    <h3 className="ac-2fa-heading">Two-Factor Authentication</h3>
                    <p className="ac-2fa-sub">Protect your account with an extra layer of security.</p>
                  </div>
                </div>
                <Toggle on={twoFactor} onChange={handleToggle2FA} />
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
                <form className="change-password-card" onSubmit={handleUpdatePassword} noValidate>
                  <div className="change-pass-title-row">
                    <h3 className="change-pass-title">Change Password</h3>
                    <button
                      type="button"
                      className="btn-cancel-pass"
                      onClick={handleCancelPassword}
                    >
                      Cancel
                    </button>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Current Password</label>
                    <div className="input-pass-wrap">
                      <input
                        type={showPass.current ? "text" : "password"}
                        name="currentPassword"
                        className={`form-input${passwordErrors.currentPassword ? " form-input--error" : ""}`}
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
                        {showPass.current ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                    {passwordErrors.currentPassword && (
                      <span className="field-error">
                        <AlertCircle size={13} /> {passwordErrors.currentPassword}
                      </span>
                    )}
                    <div className="forgot-pass-link-wrap">
                      <Link to="/forgot-password" className="forgot-pass-link">
                        Forgot Password?
                      </Link>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">New Password</label>
                    <div className="input-pass-wrap">
                      <input
                        type={showPass.new ? "text" : "password"}
                        name="newPassword"
                        className={`form-input${passwordErrors.newPassword ? " form-input--error" : ""}`}
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
                        {showPass.new ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                    {passwordErrors.newPassword && (
                      <span className="field-error">
                        <AlertCircle size={13} /> {passwordErrors.newPassword}
                      </span>
                    )}
                  </div>

                  <div className="form-group">
                    <label className="form-label">Confirm New Password</label>
                    <div className="input-pass-wrap">
                      <input
                        type={showPass.confirm ? "text" : "password"}
                        name="confirmPassword"
                        className={`form-input${passwordErrors.confirmPassword ? " form-input--error" : ""}`}
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
                        {showPass.confirm ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                    {passwordErrors.confirmPassword && (
                      <span className="field-error">
                        <AlertCircle size={13} /> {passwordErrors.confirmPassword}
                      </span>
                    )}
                  </div>

                  <div className="change-pass-actions">
                    <button type="submit" className="btn-save" disabled={isSubmittingPassword}>
                      {isSubmittingPassword ? "Updating..." : "Save"}
                    </button>
                  </div>
                </form>
              )}

              {/* Active Sessions / Connected Devices Block */}
              <div className="ac-sessions-block">
                <div className="ac-sec-header" style={{ marginBottom: "16px", paddingTop: "20px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
                  <Laptop size={20} className="ac-sec-title-icon" />
                  <h2 className="ac-sec-title">Active Sessions & Devices</h2>
                  <span className="session-policy-badge" style={{ marginLeft: "auto", fontSize: "11px", color: "#38bdf8", background: "rgba(56, 189, 248, 0.1)", padding: "4px 8px", borderRadius: "6px", border: "1px solid rgba(56, 189, 248, 0.2)" }}>
                    🔒 Max Limit: 3 Active Devices
                  </span>
                </div>
                <p className="ac-2fa-sub" style={{ marginBottom: "16px" }}>
                  View and manage devices currently signed in to your account (Maximum 3 active sessions allowed).
                </p>

                {loadingSessions && (
                  <div className="sessions-state-box">
                    <div className="gp-spinner" />
                    <span>Loading active sessions...</span>
                  </div>
                )}

                {!loadingSessions && sessionError && (
                  <div className="sessions-state-box sessions-error">
                    <AlertCircle size={16} />
                    <span>{sessionError}</span>
                  </div>
                )}

                {!loadingSessions && !sessionError && sessions.length === 0 && (
                  <div className="sessions-state-box">
                    <p>No active sessions found.</p>
                  </div>
                )}

                {!loadingSessions && !sessionError && sessions.length > 0 && (
                  <div className="sessions-list-grid">
                    {sessions.slice(0, 3).map((s) => {
                      const isCurrent = s.isCurrent || s.is_current
                      const sId = s.sessionId || s.session_id
                      const devName = s.deviceName || s.device_name || "Web Browser"
                      const ipAddr = s.ipAddress || s.ip_address || "127.0.0.1"
                      const createdDate = s.createdAt || s.created_at

                      return (
                        <div key={sId} className={`session-card-item${isCurrent ? " is-current" : ""}`}>
                          <div className="session-card-left">
                            <div className="session-icon-circle">
                              <Globe size={18} />
                            </div>
                            <div className="session-details">
                              <div className="session-name-row">
                                <span className="session-device-title">{devName}</span>
                                {isCurrent && <span className="badge-current-device">This device</span>}
                              </div>
                              <div className="session-meta">
                                <span>IP: {ipAddr}</span>
                                <span>•</span>
                                <span>Signed in: {createdDate ? new Date(createdDate).toLocaleDateString() : "Recently"}</span>
                              </div>
                            </div>
                          </div>

                          {!isCurrent && (
                            <button
                              type="button"
                              className="btn-revoke-session"
                              disabled={revokingSessionId === sId}
                              onClick={() => setConfirmRevokeSession(s)}
                            >
                              {revokingSessionId === sId ? "Signing out..." : "Sign out"}
                            </button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Confirmation Modal for Revoking Session */}
        {confirmRevokeSession && (
          <div className="profile-modal-overlay">
            <div className="profile-modal-card">
              <div className="modal-header-row">
                <LogOut size={22} className="modal-icon--danger" />
                <h3 className="modal-title">Sign Out Device?</h3>
              </div>
              <p className="modal-body-text">
                Are you sure you want to sign out <strong>{confirmRevokeSession.deviceName || confirmRevokeSession.device_name || "this device"}</strong> (IP: {confirmRevokeSession.ipAddress || confirmRevokeSession.ip_address || "127.0.0.1"})?
              </p>
              <div className="modal-action-row">
                <button
                  type="button"
                  className="btn-modal-cancel"
                  onClick={() => setConfirmRevokeSession(null)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-modal-confirm--danger"
                  disabled={!!revokingSessionId}
                  onClick={handleConfirmRevoke}
                >
                  {revokingSessionId ? "Signing out..." : "Yes, Sign Out"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: NOTIFICATION */}
        {currentTab === "notification" && (
          <div className="profile-tab-content">
            <div className="profile-notif-card">
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
                    className="btn-reset"
                    onClick={handleResetNotificationDefaults}
                  >
                    Reset Default
                  </button>
                  <button
                    type="button"
                    className="btn-save"
                    onClick={handleSaveNotificationPreferences}
                  >
                    Save Preferences
                  </button>
                </div>
              </div>

              <div className="ac-notif-stack">
                {/* Card 1: Email Notifications */}
                <div className="ac-subcard ac-email-card">
                  <div className="ac-card-head">
                    <div className="ac-card-head-left">
                      <Mail size={20} className="ac-cyan-icon" />
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
                      <AlertCircle size={16} />
                      <span>
                        Please add and verify an email address in your Profile page to receive email notifications.
                      </span>
                    </div>
                  )}
                </div>

                {/* Card 2: Mobile Notifications */}
                <div className="ac-subcard ac-mobile-card">
                  <div className="ac-card-head">
                    <div className="ac-card-head-left">
                      <Smartphone size={20} className="ac-cyan-icon" />
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
                      <AlertCircle size={16} />
                      <span>
                        Please add and verify a mobile number in your Profile page to receive mobile notifications.
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Reset to Defaults Confirmation Modal */}
      {showResetModal && (
        <div className="profile-modal-overlay">
          <div className="profile-modal-card">
            <h3 className="profile-modal-title">Reset Profile Settings</h3>
            <p className="profile-modal-text">
              Are you sure you want to reset your profile settings?
            </p>
            <div className="profile-modal-actions">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setShowResetModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-modal-confirm"
                onClick={() => {
                  handleResetDefaults()
                  setShowResetModal(false)
                }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2FA Disable Confirmation Modal */}
      {show2FaModal && (
        <div className="profile-modal-overlay">
          <div className="profile-modal-card">
            <h3 className="profile-modal-title">Disable Two-Factor Authentication</h3>
            <p className="profile-modal-text">
              Are you sure you want to disable Two-Factor Authentication?
            </p>
            <div className="profile-modal-actions">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setShow2FaModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-modal-confirm"
                onClick={() => {
                  setTwoFactor(false)
                  setShow2FaModal(false)
                  showNotification("Two-Factor Authentication disabled.", "info")
                }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
