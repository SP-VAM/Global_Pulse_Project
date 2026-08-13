import React, { useEffect, useState } from "react";
import {
  X,
  IndianRupee,
  Calendar,
  Banknote,
  Shapes,
  FileText,
} from "lucide-react";
 
import Modal from "./Modal.jsx";
import { CATEGORIES, PAYMENT_METHODS } from "./data.js";
import { getTransactionDateBounds, formatDateDisplay } from "../../../utils/dateRules.js";
 
const BLANK = { amount: "", category: "food", date: "", source: "Individual", method: "Salary", notes: "", otherSpecify: "" };
 
/**
 * Add Income / Add Expense / Edit Transaction Modal.
 * Defaults transaction date to the currently active calendar date (e.g. selected month date).
 */
export default function TransactionModal({ open, mode, type, initial, selectedDate, selectedMonthView, onClose, onSave }) {
  const isEdit = mode === "edit";
  const isExpense = type === "expense";
  const isIncome = type === "income" || (!isExpense && initial?.type === "income");

  const monthBounds = getTransactionDateBounds(
    selectedMonthView?.year ?? new Date().getFullYear(),
    selectedMonthView?.month ?? new Date().getMonth()
  );
 
  const [form, setForm] = useState(BLANK);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
 
  useEffect(() => {
    if (!open) return;
    setIsSubmitting(false);

    let defaultDate = selectedDate;
    if (!defaultDate || defaultDate < monthBounds.min || defaultDate > monthBounds.max) {
      const todayISO = new Date().toISOString().slice(0, 10);
      if (todayISO >= monthBounds.min && todayISO <= monthBounds.max) {
        defaultDate = todayISO;
      } else {
        defaultDate = monthBounds.min;
      }
    }
 
    if (initial) {
      const initSource = initial.source || (initial.method === "Salary" ? "Individual" : "Business");
      const initMethod = initSource === "Individual" ? "Salary" : (initial.method && initial.method !== "Salary" ? initial.method : "Cash");
      const initDate = initial.date && initial.date >= monthBounds.min && initial.date <= monthBounds.max ? initial.date : defaultDate;
      setForm({
        amount: String(initial.amount ?? ""),
        category: initial.category ?? "food",
        date: initDate,
        source: initSource,
        method: initMethod,
        notes: initial.notes ?? "",
        otherSpecify: initial.category === "other" ? (initial.notes ?? "") : "",
      });
    } else {
      setForm({
        ...BLANK,
        otherSpecify: "",
        date: defaultDate,
        source: isIncome ? "Individual" : "Business",
        method: isIncome ? "Salary" : "Cash",
      });
    }
    setError("");
  }, [open, initial, isIncome, selectedDate, monthBounds.min, monthBounds.max]);
 
  const handleSourceChange = (newSource) => {
    if (newSource === "Individual") {
      setForm((f) => ({ ...f, source: "Individual", method: "Salary" }));
    } else {
      setForm((f) => ({ ...f, source: "Business", method: f.method === "Salary" ? "Cash" : f.method }));
    }
  };
 
  const handleCategoryChange = (e) => {
    const val = e.target.value;
    setForm((f) => ({
      ...f,
      category: val,
      otherSpecify: val === "other" ? f.otherSpecify : "",
    }));
    if (error) setError("");
  };
 
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
 
  const handleAmountKeyDown = (e) => {
    if (["e", "E", "+", "-"].includes(e.key)) {
      e.preventDefault();
      return;
    }
    // If typing a digit, enforce 13-digit integer limit
    if (/^\d$/.test(e.key)) {
      const target = e.target;
      const selectionLength = Math.abs((target.selectionEnd || 0) - (target.selectionStart || 0));
      const currentVal = String(form.amount || "");
      const [intPart] = currentVal.split(".");
      if (selectionLength === 0 && intPart.length >= 13) {
        const cursorPosition = target.selectionStart || 0;
        const dotIndex = currentVal.indexOf(".");
        if (dotIndex === -1 || cursorPosition <= dotIndex) {
          e.preventDefault();
        }
      }
    }
  };

  const handleAmountChange = (e) => {
    let val = e.target.value;
    if (val === "") {
      setForm((f) => ({ ...f, amount: "" }));
      if (error) setError("");
      return;
    }
    if (/^\d*\.?\d*$/.test(val)) {
      const parts = val.split(".");
      let intPart = parts[0];
      const decPart = parts[1];
      if (intPart.length > 13) {
        intPart = intPart.slice(0, 13);
        val = decPart !== undefined ? `${intPart}.${decPart}` : intPart;
      }
      setForm((f) => ({ ...f, amount: val }));
      if (error) setError("");
    }
  };

  const handleAmountPaste = (e) => {
    const pasteData = (e.clipboardData || window.clipboardData)?.getData("text");
    if (!pasteData) return;
    const cleaned = pasteData.replace(/[^0-9.]/g, "");
    const parts = cleaned.split(".");
    let intPart = parts[0] || "";
    const decPart = parts.length > 1 ? parts.slice(1).join("") : undefined;
    if (intPart.length > 13) {
      intPart = intPart.slice(0, 13);
    }
    const finalVal = decPart !== undefined ? `${intPart}.${decPart}` : intPart;
    e.preventDefault();
    setForm((f) => ({ ...f, amount: finalVal }));
    if (error) setError("");
  };
 
  const submit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;
 
    const rawAmt = String(form.amount || "").trim();
    const amount = Number(rawAmt);
    const [intPart] = rawAmt.split(".");
    if (!rawAmt || Number.isNaN(amount) || amount <= 0 || /[eE+-]/.test(rawAmt)) {
      setError("Enter a valid numeric amount greater than 0.");
      return;
    }
    if (intPart.length > 13 || amount >= 1e13) {
      setError("Amount cannot exceed 13 digits.");
      return;
    }
    if (!form.date) {
      setError("Please choose a date.");
      return;
    }
    if (form.date < monthBounds.min || form.date > monthBounds.max) {
      setError(`Transaction date must be between ${formatDateDisplay(monthBounds.min)} and ${formatDateDisplay(monthBounds.max)}.`);
      return;
    }
    if (isExpense && form.category === "other" && (!form.otherSpecify || !form.otherSpecify.trim())) {
      setError("Specify Expense is required when category is Other.");
      return;
    }
    try {
      setIsSubmitting(true);
      await onSave({
        amount,
        category: isExpense ? form.category : null,
        date: form.date,
        source: isIncome ? form.source : null,
        method: isIncome && form.source === "Individual" ? "Salary" : form.method,
        notes: isExpense && form.category === "other" ? form.otherSpecify.trim() : form.notes.trim(),
      });
    } catch (err) {
      setError(err.message || "Failed to save transaction.");
    } finally {
      setIsSubmitting(false);
    }
  };
 
  const title = isEdit ? "Edit Transaction" : isExpense ? "Add Expense" : "Add Income";
  const cta = isEdit ? "Update Transaction" : isExpense ? "Add Expense" : "Add Income";
 
  return (
    <Modal open={open} onClose={onClose} labelledBy="et-tx-title" maxWidth="480px">
      <div className="drawer-panel__head">
        <div className="drawer-panel__head-text">
          <h2 id="et-tx-title" className="drawer-panel__title">
            {title}
          </h2>
          <p className="drawer-panel__subtitle">
            {isExpense ? "Record a personal or business expense" : "Record an individual or business income"}
          </p>
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
 
      <form className="drawer-panel__form" onSubmit={submit} noValidate>
        {/* AMOUNT */}
        <div className="drawer-panel__field">
          <label className="drawer-panel__label" htmlFor="tx-amount">
            Amount <span className="goal-creation__req">*</span>
          </label>
          <div className="drawer-panel__input-wrapper">
            <IndianRupee size={16} className="drawer-panel__icon" />
            <input
              id="tx-amount"
              type="number"
              step="0.01"
              min="0"
              max="9999999999999.99"
              inputMode="decimal"
              className={`drawer-panel__input ${error && !form.amount ? "has-error" : ""}`}
              placeholder="Enter amount e.g. 1500"
              value={form.amount}
              onChange={handleAmountChange}
              onKeyDown={handleAmountKeyDown}
              onPaste={handleAmountPaste}
              autoFocus
              required
            />
          </div>
        </div>
 
        {/* CATEGORY (for Expenses) */}
        {isExpense && (
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="tx-category">
              Category <span className="goal-creation__req">*</span>
            </label>
            <div className="drawer-panel__input-wrapper">
              <Shapes size={16} className="drawer-panel__icon" />
              <select
                id="tx-category"
                className="drawer-panel__select"
                value={form.category}
                onChange={handleCategoryChange}
              >
                {CATEGORIES.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
 
        {/* SPECIFY EXPENSE (When Category = Other) */}
        {isExpense && form.category === "other" && (
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="tx-other-specify">
              Specify Expense <span className="goal-creation__req">*</span>
            </label>
            <div className="drawer-panel__input-wrapper">
              <FileText size={16} className="drawer-panel__icon" />
              <input
                id="tx-other-specify"
                type="text"
                className={`drawer-panel__input ${error && (!form.otherSpecify || !form.otherSpecify.trim()) ? "has-error" : ""}`}
                placeholder="Enter the type of expense..."
                value={form.otherSpecify}
                onChange={(e) => {
                  setForm((f) => ({ ...f, otherSpecify: e.target.value }));
                  if (error) setError("");
                }}
                required
              />
            </div>
          </div>
        )}
 
        {/* SOURCE BAR (for Income: Individual vs Business) */}
        {isIncome && (
          <div className="drawer-panel__field">
            <label className="drawer-panel__label">
              Source <span className="goal-creation__req">*</span>
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <button
                type="button"
                className={`filter-chip ${form.source === "Individual" ? "is-active" : ""}`}
                style={{
                  height: "40px",
                  borderRadius: "8px",
                  justifyContent: "center",
                  fontSize: "13px",
                  fontWeight: 700,
                }}
                onClick={() => handleSourceChange("Individual")}
              >
                Individual
              </button>
              <button
                type="button"
                className={`filter-chip ${form.source === "Business" ? "is-active" : ""}`}
                style={{
                  height: "40px",
                  borderRadius: "8px",
                  justifyContent: "center",
                  fontSize: "13px",
                  fontWeight: 700,
                }}
                onClick={() => handleSourceChange("Business")}
              >
                Business
              </button>
            </div>
          </div>
        )}
 
        {/* PAYMENT METHOD */}
        <div className="drawer-panel__field">
          <label className="drawer-panel__label" htmlFor="tx-method">
            Payment Method <span className="goal-creation__req">*</span>
          </label>
          <div
            className={`drawer-panel__input-wrapper ${
              isIncome && form.source === "Individual" ? "drawer-panel__input-wrapper--disabled" : ""
            }`}
          >
            <Banknote size={16} className="drawer-panel__icon" />
            {isIncome && form.source === "Individual" ? (
              <input
                id="tx-method"
                className="drawer-panel__input"
                value="Salary"
                disabled
              />
            ) : (
              <select
                id="tx-method"
                className="drawer-panel__select"
                value={form.method}
                onChange={set("method")}
              >
                {PAYMENT_METHODS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>
 
        {/* DATE */}
        <div className="drawer-panel__field">
          <label className="drawer-panel__label" htmlFor="tx-date">
            Transaction Date <span className="goal-creation__req">*</span>
          </label>
          <div className="drawer-panel__input-wrapper">
            <Calendar size={16} className="drawer-panel__icon drawer-panel__icon--white" />
            <input
              id="tx-date"
              type="date"
              min={monthBounds.min}
              max={monthBounds.max}
              className={`drawer-panel__input ${error && !form.date ? "has-error" : ""}`}
              value={form.date}
              onChange={set("date")}
              required
            />
          </div>
        </div>
 
        {/* NOTE */}
        <div className="drawer-panel__field">
          <label className="drawer-panel__label" htmlFor="tx-notes">
            Note <span className="goal-creation__opt">(Optional)</span>
          </label>
          <div className="drawer-panel__input-wrapper">
            <FileText size={16} className="drawer-panel__icon" />
            <input
              id="tx-notes"
              type="text"
              className="drawer-panel__input"
              placeholder="Add description or notes..."
              value={form.notes}
              onChange={set("notes")}
            />
          </div>
        </div>
 
        {error && <span className="drawer-panel__err-msg">{error}</span>}
 
        {/* ACTION BUTTONS WITH CANCEL AND SUBMIT */}
        <div
          className="drawer-panel__actions"
          style={{ marginTop: "auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}
        >
          <button
            type="button"
            className="drawer-panel__btn-cancel"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="drawer-panel__btn-submit"
            disabled={isSubmitting}
            style={{ opacity: isSubmitting ? 0.6 : 1, cursor: isSubmitting ? "not-allowed" : "pointer" }}
          >
            {isSubmitting ? "Saving..." : cta}
          </button>
        </div>
      </form>
    </Modal>
  );
}
