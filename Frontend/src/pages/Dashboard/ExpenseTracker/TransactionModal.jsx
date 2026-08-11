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
 
const BLANK = { amount: "", category: "food", date: "", source: "Individual", method: "Salary", notes: "" };
 
/**
 * Add Income / Add Expense / Edit Transaction Modal.
 * Defaults transaction date to the currently active calendar date (e.g. selected month date).
 */
export default function TransactionModal({ open, mode, type, initial, selectedDate, onClose, onSave }) {
  const isEdit = mode === "edit";
  const isExpense = type === "expense";
  const isIncome = type === "income" || (!isExpense && initial?.type === "income");
 
  const [form, setForm] = useState(BLANK);
  const [error, setError] = useState("");
 
  useEffect(() => {
    if (!open) return;
    const today = new Date().toISOString().slice(0, 10);
    const defaultDate = selectedDate || today;
 
    if (initial) {
      const initSource = initial.source || (initial.method === "Salary" ? "Individual" : "Business");
      const initMethod = initSource === "Individual" ? "Salary" : (initial.method && initial.method !== "Salary" ? initial.method : "Cash");
      setForm({
        amount: String(initial.amount ?? ""),
        category: initial.category ?? "food",
        date: initial.date ?? defaultDate,
        source: initSource,
        method: initMethod,
        notes: initial.notes ?? "",
      });
    } else {
      setForm({
        ...BLANK,
        date: defaultDate,
        source: isIncome ? "Individual" : "Business",
        method: isIncome ? "Salary" : "Cash",
      });
    }
    setError("");
  }, [open, initial, isIncome, selectedDate]);
 
  const handleSourceChange = (newSource) => {
    if (newSource === "Individual") {
      setForm((f) => ({ ...f, source: "Individual", method: "Salary" }));
    } else {
      setForm((f) => ({ ...f, source: "Business", method: f.method === "Salary" ? "Cash" : f.method }));
    }
  };
 
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
 
  const submit = (e) => {
    e.preventDefault();
    const amount = Number(form.amount);
    if (!form.amount || Number.isNaN(amount) || amount <= 0) {
      setError("Enter a valid amount greater than 0.");
      return;
    }
    if (!form.date) {
      setError("Please choose a date.");
      return;
    }
    onSave({
      amount,
      category: isExpense ? form.category : null,
      date: form.date,
      source: isIncome ? form.source : null,
      method: isIncome && form.source === "Individual" ? "Salary" : form.method,
      notes: form.notes.trim(),
    });
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
              inputMode="decimal"
              className={`drawer-panel__input ${error && !form.amount ? "has-error" : ""}`}
              placeholder="Enter amount e.g. ₹1,500"
              value={form.amount}
              onChange={set("amount")}
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
                onChange={set("category")}
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
          >
            {cta}
          </button>
        </div>
      </form>
    </Modal>
  );
}
