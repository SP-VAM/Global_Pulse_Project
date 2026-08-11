import React, { useState } from "react";
import { ArrowLeft, Target, FileText, IndianRupee, PieChart, Calendar, X } from "lucide-react";
import {
  ASSET_TYPES,
  getTodayString,
  formatINR,
  formatDateDisplay,
} from "../../goalsContext.jsx";
import "./UpdateProgressDrawer.css";

export default function UpdateProgressDrawer({
  goal,
  onClose,
  onAddProgress,
}) {
  const todayStr = getTodayString();

  const [amountRaw, setAmountRaw] = useState("");
  const [assetType, setAssetType] = useState("Gold");
  const [date, setDate] = useState(todayStr);

  const [errors, setErrors] = useState({});

  const handleAmountChange = (e) => {
    const clean = e.target.value.replace(/[^0-9]/g, "");
    setAmountRaw(clean);
    if (errors.amount) {
      setErrors((prev) => ({ ...prev, amount: null }));
    }
  };

  const validate = () => {
    const newErrors = {};
    const numAmt = Number(amountRaw) || 0;

    if (!amountRaw || numAmt <= 0) {
      newErrors.amount = "Contribution amount must be greater than zero.";
    }

    if (!date) {
      newErrors.date = "Date is required.";
    } else if (date < todayStr) {
      newErrors.date = "Past dates are disabled. Select today or a future date.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    onAddProgress({
      amount: Number(amountRaw),
      assetType,
      date,
    });
    onClose();
  };

  const formattedAmountDisplay = amountRaw ? formatINR(Number(amountRaw)) : "₹0";

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-panel__head">
          <div className="drawer-panel__head-text">
            <h2 className="drawer-panel__title">Update Progress</h2>
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
            <label className="drawer-panel__label">Goal Name</label>
            <div className="drawer-panel__input-wrapper drawer-panel__input-wrapper--disabled">
              <Target size={16} className="drawer-panel__icon" />
              <input
                type="text"
                className="drawer-panel__input"
                value={goal.name}
                disabled
              />
            </div>
          </div>

          {/* Note */}
          {goal.note && (
            <div className="drawer-panel__field">
              <label className="drawer-panel__label">Goal Note</label>
              <div className="drawer-panel__input-wrapper drawer-panel__input-wrapper--disabled">
                <FileText size={16} className="drawer-panel__icon" />
                <input
                  type="text"
                  className="drawer-panel__input"
                  value={goal.note}
                  disabled
                />
              </div>
            </div>
          )}

          {/* Add Amount */}
          <div className="drawer-panel__field">
            <div className="drawer-panel__label-row">
              <label className="drawer-panel__label" htmlFor="add-amount">
                Add Amount <span className="goal-creation__req">*</span>
              </label>
              {amountRaw ? (
                <span className="drawer-panel__preview-badge">
                  Deposit: <strong>{formattedAmountDisplay}</strong>
                </span>
              ) : null}
            </div>
            <div className="drawer-panel__input-wrapper">
              <IndianRupee size={16} className="drawer-panel__icon" />
              <input
                id="add-amount"
                type="text"
                inputMode="numeric"
                className={`drawer-panel__input ${errors.amount ? "has-error" : ""}`}
                placeholder="Enter deposit amount e.g. ₹5,000"
                value={amountRaw ? formatINR(Number(amountRaw)) : ""}
                onChange={handleAmountChange}
                onFocus={(e) => e.target.select()}
                required
              />
            </div>
            {errors.amount && <span className="drawer-panel__err-msg">{errors.amount}</span>}
          </div>

          {/* Asset Type Dropdown */}
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="asset-type">
              Asset Type <span className="goal-creation__req">*</span>
            </label>
            <div className="drawer-panel__input-wrapper">
              <PieChart size={16} className="drawer-panel__icon" />
              <select
                id="asset-type"
                className="drawer-panel__select"
                value={assetType}
                onChange={(e) => setAssetType(e.target.value)}
              >
                {ASSET_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Date */}
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="progress-date">
              Contribution Date <span className="goal-creation__req">*</span>
            </label>
            <div className="drawer-panel__input-wrapper">
              <Calendar size={16} className="drawer-panel__icon drawer-panel__icon--white" />
              <input
                id="progress-date"
                type="date"
                min={todayStr}
                className={`drawer-panel__input ${errors.date ? "has-error" : ""}`}
                value={date}
                onChange={(e) => {
                  setDate(e.target.value);
                  if (errors.date) setErrors((prev) => ({ ...prev, date: null }));
                }}
                required
              />
            </div>
            {errors.date && <span className="drawer-panel__err-msg">{errors.date}</span>}
          </div>

          {/* Actions */}
          <div className="drawer-panel__actions" style={{ marginTop: "auto", gridTemplateColumns: "1fr" }}>
            <button
              type="submit"
              className="drawer-panel__btn-submit"
            >
              Update Progress
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
