import React, { useContext, useEffect, useRef, useState } from "react"
import "./UpdateProgressModal.css"
import { GoalsContext } from "../../goalsContext.jsx"

export default function UpdateProgressModal({ onClose }) {
  const { selected, updateProgress } = useContext(GoalsContext)
  const [goalName, setGoalName] = useState(selected?.name || "Investment Goal")
  const [notes, setNotes] = useState("")
  const [amount, setAmount] = useState("")
  const [asset, setAsset] = useState("")
  const [date, setDate] = useState(new Date().toISOString().split("T")[0])
  const [error, setError] = useState("")
  const modalRef = useRef(null)

  useEffect(() => {
    document.body.classList.add("modal-open")
    return () => {
      document.body.classList.remove("modal-open")
    }
  }, [])

  if (!selected) return null

  function handleAmountChange(e) {
    const val = e.target.value.replace(/[^\d]/g, "")
    setAmount(val)
    if (error) setError("")
  }

  function handleSubmit(e) {
    e.preventDefault()
    const num = Number(amount)
    if (!amount || isNaN(num) || num <= 0) {
      setError("Please enter a valid amount.")
      return
    }

    const title = notes.trim() || "Monthly Deposit"
    const subtitle = asset.trim() ? `Auto-transfer from ${asset}` : "Goal progress contribution"
    updateProgress(selected.id, num, date, title, subtitle)
    onClose()
  }

  return (
    <div className="up-modal-overlay">
      <div className="up-modal" ref={modalRef} role="dialog" aria-modal="true">
        <div className="up-modal-head">
          <h3 className="up-modal-title">Update Progress</h3>
        </div>

        <form className="up-form" onSubmit={handleSubmit} noValidate>
          {/* GOAL NAME */}
          <div className="up-field">
            <label className="up-label">GOAL NAME</label>
            <input
              type="text"
              className="up-input"
              value={goalName}
              onChange={(e) => setGoalName(e.target.value)}
            />
          </div>

          {/* NOTE */}
          <div className="up-field">
            <label className="up-label">NOTE</label>
            <input
              type="text"
              className="up-input"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {/* ADD AMOUNT */}
          <div className="up-field">
            <label className="up-label">ADD AMOUNT</label>
            <input
              type="text"
              className={`up-input ${error ? "up-input--error" : ""}`}
              value={amount}
              onChange={handleAmountChange}
              autoFocus
            />
            {error && <div className="up-error">{error}</div>}
          </div>

          {/* ASSET */}
          <div className="up-field">
            <label className="up-label">ASSET</label>
            <select
              className="up-input"
              value={asset}
              onChange={(e) => setAsset(e.target.value)}
            >
              <option value="">Select Asset</option>
              <option value="Checking Account">Checking Account</option>
              <option value="Stocks">Stocks</option>
              <option value="Bonds">Bonds</option>
              <option value="Gold/Silver">Gold / Silver</option>
              <option value="Crypto">Crypto</option>
              <option value="Mutual Funds">Mutual Funds / ETFs</option>
            </select>
          </div>

          {/* DATE */}
          <div className="up-field">
            <label className="up-label">DATE</label>
            <input
              type="date"
              className="up-input"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>

          {/* BUTTONS */}
          <div className="up-actions">
            <button type="button" className="up-btn up-btn--cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="up-btn up-btn--submit">
              Update Goal
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
