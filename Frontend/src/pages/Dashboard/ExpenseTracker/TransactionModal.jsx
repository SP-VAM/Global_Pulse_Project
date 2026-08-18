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
import { CATEGORIES, PAYMENT_METHODS, getCategoryKey } from "./data.js";
import {
  MIN_YEAR,
  MAX_YEAR,
  getTransactionDateBounds,
  formatDateDisplay,
} from "../../../utils/dateRules.js";
import {
  MAX_NAME_LENGTH,
  MAX_NOTE_LENGTH,
  MAX_FINANCIAL_INT_DIGITS,
  validateTextLength,
  validateFinancialAmount,
  sanitizeFinancialInput,
} from "../../../utils/financialValidation.js";

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
      const initCat = getCategoryKey(initial.category || initial.categoryName);
      setForm({
        amount: String(initial.amount ?? ""),
        category: initCat,
        date: initDate,
        source: initSource,
        method: initMethod,
        notes: (initial.notes ?? "").slice(0, 30),
        otherSpecify: initCat === "other" ? (initial.notes ?? "").slice(0, 30) : "",
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

  const handleDateChange = (e) => {
    const val = e.target.value;
    if (!val) {
      setForm((f) => ({ ...f, date: "" }));
      return;
    }
    const yearNum = Number(val.slice(0, 4));
    if (yearNum && (yearNum < MIN_YEAR || yearNum > MAX_YEAR)) {
      setError(`Year must be between ${MIN_YEAR} and ${MAX_YEAR}.`);
      return;
    }
    if (val < monthBounds.min || val > monthBounds.max) {
      setError(`Transaction date must be between ${formatDateDisplay(monthBounds.min)} and ${formatDateDisplay(monthBounds.max)}.`);
    } else {
      setError("");
    }
    setForm((f) => ({ ...f, date: val }));
  };

  const handleNotesChange = (e) => {
    const val = e.target.value.slice(0, 30);
    setForm((f) => ({ ...f, notes: val }));
    if (error) setError("");
  };

  const handleNotesPaste = (e) => {
    e.preventDefault();
    const paste = (e.clipboardData || window.clipboardData)?.getData("text") || "";
    const combined = paste.slice(0, 30);
    setForm((f) => ({ ...f, notes: combined }));
    if (error) setError("");
  };

  const handleOtherSpecifyChange = (e) => {
    const val = e.target.value.slice(0, 30);
    setForm((f) => ({ ...f, otherSpecify: val }));
    if (error) setError("");
  };

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
    const clean = sanitizeFinancialInput(e.target.value, true);
    setForm((f) => ({ ...f, amount: clean }));
    if (error) setError("");
  };

  const handleAmountPaste = (e) => {
    const pasteData = (e.clipboardData || window.clipboardData)?.getData("text");
    if (!pasteData) return;
    const cleaned = sanitizeFinancialInput(pasteData, true);
    e.preventDefault();
    setForm((f) => ({ ...f, amount: cleaned }));
    if (error) setError("");
  };

  const submit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;

    const amtVal = validateFinancialAmount(form.amount, {
      fieldName: "Amount",
      min: 0.01,
      minError: "Enter a valid numeric amount greater than 0.",
    });
    if (!amtVal.isValid) {
      setError(amtVal.error);
      return;
    }

    if (!form.date) {
      setError("Please choose a date.");
      return;
    }
    const yearNum = Number(form.date.slice(0, 4));
    if (yearNum < MIN_YEAR || yearNum > MAX_YEAR || form.date < monthBounds.min || form.date > monthBounds.max) {
      setError(`Transaction date must be between ${formatDateDisplay(monthBounds.min)} and ${formatDateDisplay(monthBounds.max)} (Year ${MIN_YEAR}–${MAX_YEAR}).`);
      return;
    }
    if (isExpense && form.category === "other") {
      const otherVal = validateTextLength(form.otherSpecify, 30, "Note", true);
      if (!otherVal.isValid) {
        setError(otherVal.error);
        return;
      }
    }
    const noteVal = validateTextLength(form.notes, 30, "Note", isIncome);
    if (!noteVal.isValid) {
      setError(noteVal.error);
      return;
    }
    try {
      setIsSubmitting(true);
      await onSave({
        amount: amtVal.numValue,
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

        {/* NOTE (When Category = Other) */}
        {isExpense && form.category === "other" && (
          <div className="drawer-panel__field">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label className="drawer-panel__label" htmlFor="tx-other-specify">
                Note <span className="goal-creation__req">*</span>
              </label>
              <span style={{ fontSize: "11px", color: form.otherSpecify.length >= 30 ? "#ef4444" : "#94a3b8" }}>
                {form.otherSpecify.length}/30
              </span>
            </div>
            <div className="drawer-panel__input-wrapper">
              <FileText size={16} className="drawer-panel__icon" />
              <input
                id="tx-other-specify"
                type="text"
                maxLength={30}
                className={`drawer-panel__input ${error && (!form.otherSpecify || !form.otherSpecify.trim()) ? "has-error" : ""}`}
                placeholder="Enter description or note (max 30 chars)..."
                value={form.otherSpecify}
                onChange={handleOtherSpecifyChange}
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
          <div
            className="drawer-panel__input-wrapper"
            style={{ cursor: "pointer", position: "relative" }}
            onClick={() => {
              const el = document.getElementById("tx-date");
              if (el && el.showPicker) el.showPicker();
            }}
          >
            <Calendar size={16} className="drawer-panel__icon drawer-panel__icon--white" />
            <input
              id="tx-date"
              type="date"
              min={monthBounds.min}
              max={monthBounds.max}
              value={form.date}
              onChange={handleDateChange}
              onKeyDown={(e) => e.preventDefault()}
              style={{
                position: "absolute",
                inset: 0,
                opacity: 0,
                cursor: "pointer",
                width: "100%",
                height: "100%",
                zIndex: 2,
              }}
              required
            />
            <div
              className={`drawer-panel__input ${error && !form.date ? "has-error" : ""}`}
              style={{
                display: "flex",
                alignItems: "center",
                userSelect: "none",
                cursor: "pointer",
                color: form.date ? "var(--text, #f4f6fb)" : "var(--text-3, #6b7385)",
                fontWeight: 600,
                letterSpacing: "0.5px",
              }}
            >
              {form.date ? (
                (() => {
                  const [y, m, d] = form.date.split("-");
                  return y && m && d ? `${d}-${m}-${y}` : form.date;
                })()
              ) : (
                "DD-MM-YYYY"
              )}
            </div>
          </div>
        </div>

        {/* NOTE */}
        {!(isExpense && form.category === "other") && (
          <div className="drawer-panel__field">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label className="drawer-panel__label" htmlFor="tx-notes">
                Note{" "}
                {isIncome ? (
                  <span className="goal-creation__req">*</span>
                ) : (
                  <span className="goal-creation__opt">(Optional)</span>
                )}
              </label>
              <span style={{ fontSize: "11px", color: form.notes.length >= 30 ? "#ef4444" : "#94a3b8" }}>
                {form.notes.length}/30
              </span>
            </div>
            <div className="drawer-panel__input-wrapper">
              <FileText size={16} className="drawer-panel__icon" />
              <input
                id="tx-notes"
                type="text"
                maxLength={30}
                className={`drawer-panel__input ${error && isIncome && (!form.notes || !form.notes.trim()) ? "has-error" : ""}`}
                placeholder={
                  isIncome
                    ? "Enter income description or note..."
                    : "Add description or note (max 30 chars)..."
                }
                value={form.notes}
                onChange={handleNotesChange}
                onPaste={handleNotesPaste}
                required={isIncome}
              />
            </div>
          </div>
        )}

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
