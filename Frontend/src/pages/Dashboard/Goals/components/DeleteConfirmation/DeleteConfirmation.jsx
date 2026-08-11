import React, { useContext, useEffect, useRef } from "react"
import "./DeleteConfirmation.css"
import { GoalsContext } from "../../goalsContext.jsx"

export default function DeleteConfirmation({ onClose }) {
  const { selected, deleteGoal } = useContext(GoalsContext)
  const modalRef = useRef(null)

  useEffect(() => {
    document.body.classList.add("modal-open")
    function onKey(e) { if (e.key === "Escape") onClose() }
    document.addEventListener("keydown", onKey)
    return () => {
      document.body.classList.remove("modal-open")
      document.removeEventListener("keydown", onKey)
    }
  }, [onClose])

  if (!selected) return null

  function confirm() {
    deleteGoal(selected.id)
    onClose()
  }

  return (
    <div className="dc-overlay">
      <div className="dc-box" role="dialog" aria-modal="true" ref={modalRef}>
        <div className="dc-head">
          <h2 className="dc-title">Confirm Delete</h2>
        </div>
        <div className="dc-actions">
          <button type="button" className="dc-btn dc-btn--cancel" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="dc-btn dc-btn--delete" onClick={confirm}>
            Confirm Delete
          </button>
        </div>
      </div>
    </div>
  )
}
