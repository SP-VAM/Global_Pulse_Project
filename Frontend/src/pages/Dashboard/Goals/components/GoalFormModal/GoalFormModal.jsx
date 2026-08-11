import React, { useContext, useEffect, useRef, useState } from "react"
import "./GoalFormModal.css"
import { GoalsContext } from "../../goalsContext.jsx"

export default function GoalFormModal({ onClose, onCreate, goalToEdit, onDeleteRequest }) {
  const { createGoal, updateGoal, deleteGoal } = useContext(GoalsContext)
  const modalRef = useRef(null)

  const [name, setName] = useState(goalToEdit?.name || "")
  const [notes, setNotes] = useState(goalToEdit?.notes || "")
  const [target, setTarget] = useState(goalToEdit?.target ? String(goalToEdit.target) : "")
  const [startDate, setStartDate] = useState(goalToEdit?.startDate || "")
  const [endDate, setEndDate] = useState(goalToEdit?.endDate || "")
  const [errors, setErrors] = useState({})

  useEffect(() => {
    document.body.classList.add("modal-open")
    return () => {
      document.body.classList.remove("modal-open")
    }
  }, [])

  function handleTargetChange(e) {
    let value = e.target.value.replace(/[^\d]/g, "")
    setTarget(value)
    if (errors.target) {
      setErrors((prev) => ({ ...prev, target: null }))
    }
  }

  function validate() {
    const e = {}

    if (!name.trim()) {
      e.name = "Goal name is required."
    }

    const numTarget = Number(target)
    if (!target || isNaN(numTarget) || numTarget < 10000) {
      e.target = "Minimum target amount is ₹10,000."
    }

    if (!startDate) {
      e.startDate = "Start date is required."
    }

    if (!endDate) {
      e.endDate = "End date is required."
    } else if (startDate) {
      const start = new Date(startDate)
      const minEnd = new Date(start)
      minEnd.setMonth(minEnd.getMonth() + 1)

      const end = new Date(endDate)
      if (end < minEnd) {
        e.endDate = "End date must be at least 1 month after start date."
      }
    }

    setErrors(e)
    return Object.keys(e).length === 0
  }

  function handleDelete() {
    if (onDeleteRequest) {
      onDeleteRequest()
    } else if (goalToEdit?.id) {
      deleteGoal(goalToEdit.id)
      if (onClose) onClose()
    }
  }

  function handleSubmit(event) {
    event.preventDefault()

    if (!validate()) return

    if (goalToEdit) {
      updateGoal(goalToEdit.id, {
        name,
        notes,
        target: Number(target),
        startDate,
        endDate,
      })
      if (onClose) onClose()
    } else {
      const payload = {
        id: `goal-${Date.now()}`,
        name,
        notes,
        asset: "finance",
        unit: "₹",
        target: Number(target),
        progress: 0,
        startDate,
        endDate,
      }

      const created = createGoal(payload)
      if (onCreate) {
        onCreate(created)
      }
      if (onClose) {
        onClose()
      }
    }
  }

  return (
    <div className="gf-modal-overlay">
      <div
        className="gf-modal"
        role="dialog"
        aria-modal="true"
        ref={modalRef}
      >
        <div className="gf-modal-head">
          <h2 className="gf-modal-title">{goalToEdit ? "Update Goal" : "Set your Goal"}</h2>
        </div>

        <form className="gf-form" onSubmit={handleSubmit} noValidate>
          {/* GOAL NAME */}
          <div className="gf-field">
            <label className="gf-label">GOAL NAME</label>
            <input
              type="text"
              className={`gf-input ${errors.name ? "gf-input--error" : ""}`}
              placeholder="Goal name"
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                if (errors.name) setErrors((prev) => ({ ...prev, name: null }))
              }}
            />
            {errors.name && <div className="gf-error">{errors.name}</div>}
          </div>

          {/* NOTE */}
          <div className="gf-field">
            <label className="gf-label">NOTE</label>
            <input
              type="text"
              className="gf-input"
              placeholder="Note"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {/* UPDATE AMOUNT / TARGET AMOUNT */}
          <div className="gf-field">
            <label className="gf-label">{goalToEdit ? "UPDATE AMOUNT" : "TARGET AMOUNT"}</label>
            <input
              type="text"
              className={`gf-input ${errors.target ? "gf-input--error" : ""}`}
              placeholder="Amount"
              value={target}
              onChange={handleTargetChange}
            />
            {errors.target && <div className="gf-error">{errors.target}</div>}
          </div>

          {/* START DATE & END DATE */}
          <div className="gf-dates">
            <div className="gf-field">
              <label className="gf-label">START DATE</label>
              <input
                type="date"
                className={`gf-input ${errors.startDate ? "gf-input--error" : ""}`}
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value)
                  if (errors.startDate || errors.endDate) {
                    setErrors((prev) => ({ ...prev, startDate: null, endDate: null }))
                  }
                }}
              />
              {errors.startDate && <div className="gf-error">{errors.startDate}</div>}
            </div>

            <div className="gf-field">
              <label className="gf-label">END DATE</label>
              <input
                type="date"
                className={`gf-input ${errors.endDate ? "gf-input--error" : ""}`}
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value)
                  if (errors.endDate) {
                    setErrors((prev) => ({ ...prev, endDate: null }))
                  }
                }}
              />
            </div>
          </div>
          {errors.endDate && <div className="gf-error">{errors.endDate}</div>}

          {/* BUTTONS */}
          <div className="gf-actions">
            {goalToEdit ? (
              <button
                type="button"
                className="gf-btn gf-btn--delete"
                onClick={handleDelete}
              >
                Delete Goal
              </button>
            ) : (
              <button
                type="button"
                className="gf-btn gf-btn--cancel"
                onClick={onClose}
              >
                Cancel
              </button>
            )}
            <button type="submit" className="gf-btn gf-btn--submit">
              {goalToEdit ? "Update Goal" : "Set Goal"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
