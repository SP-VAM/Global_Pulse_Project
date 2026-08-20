import React, { useState } from "react";
import { ArrowLeft, Target, FileText, IndianRupee, Calendar, X } from "lucide-react";
import { formatINR } from "../../goalsContext.jsx";
import { getTodayISO, getMaxDateISO, formatDateDisplay } from "../../../../../utils/dateRules.js";
import {
  sanitizeFinancialInput,
  validateFinancialAmount,
  validateTextLength,
  MAX_GOAL_NAME_LENGTH,
  MAX_GOAL_NOTE_LENGTH,
  MAX_GOAL_TARGET_AMOUNT,
  formatSafeINR,
} from "../../../../../utils/financialValidation.js";
import "../UpdateGoalDrawer/UpdateGoalDrawer.css";
import "./GoalCreation.css";

const getTodayString = () => getTodayISO();

const getOneMonthLaterString = (baseDateStr) => {
  const d = baseDateStr ? new Date(baseDateStr) : new Date();
  d.setMonth(d.getMonth() + 1);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export default function GoalCreation({ onCancel, onCreateSuccess }) {
  const todayStr = getTodayString();
  const maxDateStr = getMaxDateISO();

  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [targetRaw, setTargetRaw] = useState(""); // empty by default
  const [startDate, setStartDate] = useState(todayStr);
  const [endDate, setEndDate] = useState(() => getOneMonthLaterString(todayStr));

  const [errors, setErrors] = useState({});

  const handleTargetChange = (e) => {
    const clean = sanitizeFinancialInput(e.target.value, false, 9);
    setTargetRaw(clean);
    if (errors.target) {
      setErrors((prev) => ({ ...prev, target: null }));
    }
  };

  const handleStartDateChange = (e) => {
    const selected = e.target.value;
    setStartDate(selected);
    const minEndDate = getOneMonthLaterString(selected);
    if (endDate < minEndDate) {
      setEndDate(minEndDate);
    }
    if (errors.startDate) {
      setErrors((prev) => ({ ...prev, startDate: null }));
    }
    if (errors.endDate) {
      setErrors((prev) => ({ ...prev, endDate: null }));
    }
  };

  const handleEndDateChange = (e) => {
    const selected = e.target.value;
    setEndDate(selected);
    if (errors.endDate) {
      setErrors((prev) => ({ ...prev, endDate: null }));
    }
  };

  const validate = () => {
    const newErrors = {};

    const nameVal = validateTextLength(
      name,
      MAX_GOAL_NAME_LENGTH,
      "Goal Name",
      true,
      "Goal Name cannot exceed 30 characters."
    );
    if (!nameVal.isValid) {
      newErrors.name = nameVal.error;
    }

    const noteVal = validateTextLength(
      note,
      MAX_GOAL_NOTE_LENGTH,
      "Note",
      false,
      "Note cannot exceed 30 characters."
    );
    if (!noteVal.isValid) {
      newErrors.note = noteVal.error;
    }

    const targetVal = validateFinancialAmount(targetRaw, {
      fieldName: "Target Amount",
      min: 10000,
      minError: "Target amount must be at least ₹10,000.",
      max: MAX_GOAL_TARGET_AMOUNT,
      maxError: "Target Amount cannot exceed ₹99,99,99,999.",
    });
    if (!targetVal.isValid) {
      newErrors.target = targetVal.error;
    }

    if (!startDate) {
      newErrors.startDate = "Start date is required.";
    } else if (startDate < todayStr) {
      newErrors.startDate = "Start date cannot be in the past.";
    } else if (startDate > maxDateStr) {
      newErrors.startDate = `Start date cannot be later than ${formatDateDisplay(maxDateStr)}.`;
    }

    const minAllowedEndDate = getOneMonthLaterString(startDate);
    if (!endDate) {
      newErrors.endDate = "End date is required.";
    } else if (endDate < minAllowedEndDate) {
      newErrors.endDate = "End date must be at least 1 month after Start date.";
    } else if (endDate < todayStr) {
      newErrors.endDate = "End date cannot be in the past.";
    } else if (endDate > maxDateStr) {
      newErrors.endDate = `End date cannot be later than ${formatDateDisplay(maxDateStr)}.`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    const payload = {
      name: name.trim(),
      note: note.trim(),
      target: Number(targetRaw),
      startDate,
      endDate,
    };

    onCreateSuccess(payload);
  };

  const formattedTargetDisplay = targetRaw ? formatSafeINR(Number(targetRaw)) : "₹0";

  return (
    <div className="goal-modal-overlay" onClick={onCancel}>
      <div className="goal-modal-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header (Title & Subtitle aligned at top) */}
        <div className="drawer-panel__head">
          <div className="drawer-panel__head-text">
            <h2 className="drawer-panel__title">Create Financial Goal</h2>
            <p className="drawer-panel__subtitle">
              Set your target savings amount and timeline to begin tracking.
            </p>
          </div>
          <button
            type="button"
            className="drawer-panel__close-btn"
            onClick={onCancel}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form className="drawer-panel__form" onSubmit={handleSubmit} noValidate>
          {/* Goal Name */}
          <div className="drawer-panel__field">
            <div className="drawer-panel__label-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label className="drawer-panel__label" htmlFor="create-goal-name">
                Goal Name <span className="goal-creation__req">*</span>
              </label>
              <span style={{ fontSize: "11px", color: "var(--text-3, #6b7385)", fontWeight: 600 }}>
                {name.length}/30
              </span>
            </div>
            <div className="drawer-panel__input-wrapper">
              <Target size={16} className="drawer-panel__icon" />
              <input
                id="create-goal-name"
                type="text"
                maxLength={MAX_GOAL_NAME_LENGTH}
                className={`drawer-panel__input ${errors.name ? "has-error" : ""}`}
                placeholder="e.g. Dream Vacation, House Downpayment..."
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (errors.name) setErrors((prev) => ({ ...prev, name: null }));
                }}
                autoFocus
                required
              />
            </div>
            {errors.name && <span className="drawer-panel__err-msg">{errors.name}</span>}
          </div>

          {/* Note */}
          <div className="drawer-panel__field">
            <div className="drawer-panel__label-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label className="drawer-panel__label" htmlFor="create-goal-note">
                Note <span className="goal-creation__opt">(Optional)</span>
              </label>
              <span style={{ fontSize: "11px", color: "var(--text-3, #6b7385)", fontWeight: 600 }}>
                {note.length}/30
              </span>
            </div>
            <div className="drawer-panel__input-wrapper">
              <FileText size={16} className="drawer-panel__icon" />
              <input
                id="create-goal-note"
                type="text"
                maxLength={MAX_GOAL_NOTE_LENGTH}
                className={`drawer-panel__input ${errors.note ? "has-error" : ""}`}
                placeholder="Add notes or specific strategy..."
                value={note}
                onChange={(e) => {
                  setNote(e.target.value);
                  if (errors.note) setErrors((prev) => ({ ...prev, note: null }));
                }}
              />
            </div>
            {errors.note && <span className="drawer-panel__err-msg">{errors.note}</span>}
          </div>

          {/* Target Amount */}
          <div className="drawer-panel__field">
            <div className="drawer-panel__label-row">
              <label className="drawer-panel__label" htmlFor="create-goal-target">
                Target Amount <span className="goal-creation__req">*</span>
              </label>
              {targetRaw ? (
                <span className="drawer-panel__preview-badge">
                  Target: <strong>{formattedTargetDisplay}</strong>
                </span>
              ) : null}
            </div>
            <div className="drawer-panel__input-wrapper">
              <IndianRupee size={16} className="drawer-panel__icon" />
              <input
                id="create-goal-target"
                type="text"
                inputMode="numeric"
                maxLength={14}
                className={`drawer-panel__input ${errors.target ? "has-error" : ""}`}
                placeholder="Minimum ₹10,000 (Max ₹99,99,99,999)"
                value={targetRaw ? formatINR(Number(targetRaw)) : ""}
                onChange={handleTargetChange}
                onFocus={(e) => e.target.select()}
                required
              />
            </div>
            {errors.target && <span className="drawer-panel__err-msg">{errors.target}</span>}
          </div>

          {/* Start Date & End Date Row */}
          <div className="goal-modal__dates-row">
            <div className="drawer-panel__field">
              <label className="drawer-panel__label" htmlFor="create-start-date">
                Start Date <span className="goal-creation__req">*</span>
              </label>
              <div className="drawer-panel__input-wrapper">
                <Calendar size={16} className="drawer-panel__icon drawer-panel__icon--white" />
                <input
                  id="create-start-date"
                  type="date"
                  min={todayStr}
                  max={maxDateStr}
                  className={`drawer-panel__input ${errors.startDate ? "has-error" : ""}`}
                  value={startDate}
                  onChange={handleStartDateChange}
                  required
                />
              </div>
              {errors.startDate && <span className="drawer-panel__err-msg">{errors.startDate}</span>}
            </div>

            <div className="drawer-panel__field">
              <label className="drawer-panel__label" htmlFor="create-end-date">
                End Date <span className="goal-creation__req">*</span>
              </label>
              <div className="drawer-panel__input-wrapper">
                <Calendar size={16} className="drawer-panel__icon drawer-panel__icon--white" />
                <input
                  id="create-end-date"
                  type="date"
                  min={getOneMonthLaterString(startDate || todayStr)}
                  max={maxDateStr}
                  className={`drawer-panel__input ${errors.endDate ? "has-error" : ""}`}
                  value={endDate}
                  onChange={handleEndDateChange}
                  required
                />
              </div>
              {errors.endDate && <span className="drawer-panel__err-msg">{errors.endDate}</span>}
            </div>
          </div>

          {/* Drawer Actions */}
          <div className="drawer-panel__actions">
            <button
              type="button"
              className="drawer-panel__btn-cancel"
              onClick={onCancel}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="drawer-panel__btn-submit"
            >
              Set Goal
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
