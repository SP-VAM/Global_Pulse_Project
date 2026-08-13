import { useEffect, useRef } from "react"
import { LogOut, X } from "lucide-react"
import "./LogoutConfirmationModal.css"

export default function LogoutConfirmationModal({ open, onClose, onConfirm }) {
  const overlayRef = useRef(null)

  useEffect(() => {
    if (!open) return
    document.body.classList.add("modal-open")
    function handleKeyDown(e) {
      if (e.key === "Escape") {
        onClose()
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.body.classList.remove("modal-open")
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [open, onClose])

  if (!open) return null

  const handleBackdropClick = (e) => {
    if (e.target === overlayRef.current) {
      onClose()
    }
  }

  return (
    <div
      className="logout-modal-overlay"
      ref={overlayRef}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="logout-modal-title"
    >
      <div className="logout-modal-box">
        <div className="logout-modal-head">
          <div className="logout-modal-icon">
            <LogOut size={22} />
          </div>
          <h2 id="logout-modal-title" className="logout-modal-title">
            Confirm Logout
          </h2>
          <button
            type="button"
            className="logout-modal-close"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        <div className="logout-modal-body">
          <p>Are you sure you want to logout from GlobalPulse?</p>
        </div>

        <div className="logout-modal-actions">
          <button
            type="button"
            className="logout-btn logout-btn--cancel"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="logout-btn logout-btn--confirm"
            onClick={onConfirm}
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  )
}
