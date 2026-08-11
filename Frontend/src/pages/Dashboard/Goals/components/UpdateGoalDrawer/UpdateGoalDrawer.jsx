import React, { useState } from "react";
import { ArrowLeft, Target, FileText, IndianRupee, Calendar, Trash2, X, AlertTriangle } from "lucide-react";
import { formatINR, getTodayString, formatDateDisplay } from "../../goalsContext.jsx";
import "./UpdateGoalDrawer.css";

export default function UpdateGoalDrawer({
  goal,
  onClose,
  onUpdateGoal,
  onOpenDeleteConfirm,
}) {
  const todayStr = getTodayString();
  const currentTarget = goal.target || 10000;

  const [name, setName] = useState(goal.name || "");
  const [note, setNote] = useState(goal.note || "");
  const [targetRaw, setTargetRaw] = useState(String(currentTarget));
  const [endDate, setEndDate] = useState(goal.endDate || todayStr);

  const [errors, setErrors] = useState({});

  const handleTargetChange = (e) => {
    const clean = e.target.value.replace(/[^0-9]/g, "");
    setTargetRaw(clean);
    if (errors.target) {
      setErrors((prev) => ({ ...prev, target: null }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!name.trim()) {
      newErrors.name = "Goal name is required.";
    }

    const numTarget = Number(targetRaw) || 0;
    if (!targetRaw || numTarget < currentTarget) {
      newErrors.target = `New target must be greater than or equal to current target (${formatINR(
        currentTarget
      )}). Decreasing target is not allowed.`;
    }

    if (!endDate) {
      newErrors.endDate = "End date is required.";
    } else if (endDate < goal.startDate) {
      newErrors.endDate = `End date cannot be before Start date (${formatDateDisplay(
        goal.startDate
      )}).`;
    } else if (endDate < todayStr) {
      newErrors.endDate = "End date cannot be in the past.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    onUpdateGoal({
      name: name.trim(),
      note: note.trim(),
      target: Number(targetRaw),
      endDate,
    });
    onClose();
  };

  const formattedTargetDisplay = targetRaw ? formatINR(Number(targetRaw)) : "₹0";

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="drawer-panel__head">
          <div className="drawer-panel__head-text">
            <h2 className="drawer-panel__title">Update Goal Settings</h2>
          </div>
          <button
            type="button"
            className="drawer-panel__close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form className="drawer-panel__form" onSubmit={handleSubmit} noValidate>
          {/* Goal Name */}
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="edit-goal-name">
              Goal Name
            </label>
            <div className="drawer-panel__input-wrapper">
              <Target size={16} className="drawer-panel__icon" />
              <input
                id="edit-goal-name"
                type="text"
                className={`drawer-panel__input ${errors.name ? "has-error" : ""}`}
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (errors.name) setErrors((prev) => ({ ...prev, name: null }));
                }}
                required
              />
            </div>
            {errors.name && <span className="drawer-panel__err-msg">{errors.name}</span>}
          </div>

          {/* Note */}
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="edit-goal-note">
              Note
            </label>
            <div className="drawer-panel__input-wrapper">
              <FileText size={16} className="drawer-panel__icon" />
              <input
                id="edit-goal-note"
                type="text"
                className="drawer-panel__input"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>
          </div>

          {/* Target Amount */}
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="edit-goal-target">
              Target Amount
            </label>
            <div className="drawer-panel__input-wrapper">
              <IndianRupee size={16} className="drawer-panel__icon" />
              <input
                id="edit-goal-target"
                type="text"
                inputMode="numeric"
                className={`drawer-panel__input ${errors.target ? "has-error" : ""}`}
                value={targetRaw ? formatINR(Number(targetRaw)) : ""}
                onChange={handleTargetChange}
                onFocus={(e) => e.target.select()}
                required
              />
            </div>
            {errors.target ? (
              <span className="drawer-panel__err-msg">{errors.target}</span>
            ) : (
              <span className="drawer-panel__hint">
                Current: {formatINR(currentTarget)}. Target can only be increased or kept same.
              </span>
            )}
          </div>

          {/* Start Date & End Date Row (Left & Right) */}
          <div className="goal-modal__dates-row">
            {/* Start Date (Read-only) */}
            <div className="drawer-panel__field">
              <label className="drawer-panel__label">Start Date</label>
              <div className="drawer-panel__input-wrapper drawer-panel__input-wrapper--disabled">
                <Calendar size={16} className="drawer-panel__icon drawer-panel__icon--white" />
                <input
                  type="text"
                  className="drawer-panel__input"
                  value={formatDateDisplay(goal.startDate)}
                  disabled
                />
              </div>
            </div>

            {/* End Date (Editable) */}
            <div className="drawer-panel__field">
              <label className="drawer-panel__label" htmlFor="edit-goal-end-date">
                End Date
              </label>
              <div className="drawer-panel__input-wrapper">
                <Calendar size={16} className="drawer-panel__icon drawer-panel__icon--white" />
                <input
                  id="edit-goal-end-date"
                  type="date"
                  min={goal.startDate || todayStr}
                  className={`drawer-panel__input ${errors.endDate ? "has-error" : ""}`}
                  value={endDate}
                  onChange={(e) => {
                    setEndDate(e.target.value);
                    if (errors.endDate) setErrors((prev) => ({ ...prev, endDate: null }));
                  }}
                  required
                />
              </div>
              {errors.endDate && <span className="drawer-panel__err-msg">{errors.endDate}</span>}
            </div>
          </div>

          {/* Drawer Actions: Delete Goal (Left) & Update Goal (Right) */}
          <div className="drawer-panel__actions">
            <button
              type="button"
              className="drawer-panel__danger-btn"
              onClick={onOpenDeleteConfirm}
            >
              <Trash2 size={16} />
              <span>Delete Goal</span>
            </button>
            <button
              type="submit"
              className="drawer-panel__btn-submit"
            >
              Update Goal
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
