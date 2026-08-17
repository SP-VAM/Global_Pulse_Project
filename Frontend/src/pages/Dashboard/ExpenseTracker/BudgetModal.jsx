import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X, Tag, IndianRupee, FileText, Trash2, AlertTriangle, Shapes } from "lucide-react";
import Modal from "./Modal.jsx";
import { CATEGORIES, formatINR } from "./data.js";
import {
  sanitizeFinancialInput,
  validateFinancialAmount,
  validateTextLength,
  MAX_NAME_LENGTH,
  MAX_NOTE_LENGTH,
  MAX_FINANCIAL_INT_DIGITS,
  formatSafeINR,
} from "../../../utils/financialValidation.js";
 
const BLANK = { category: "food", label: "Food", limit: "", notes: "" };
 
/**
 * Add / Edit Budget Bucket Modal.
 * Uses exact Goals DeleteConfirmationModal system portaled to document.body.
 */
export default function BudgetModal({ open, mode, initial, onClose, onSave, onDelete, onDeleteBudget }) {
  const isEdit = mode === "edit";
  const [form, setForm] = useState(BLANK);
  const [error, setError] = useState("");
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
 
  const initialLimit = isEdit ? Number(initial?.limit || 0) : 0;
 
  useEffect(() => {
    if (!open) return;
    if (initial) {
      setForm({
        category: initial.category ?? "food",
        label: initial.label ?? "",
        limit: String(initial.limit ?? ""),
        notes: initial.notes ?? "",
      });
    } else {
      setForm(BLANK);
    }
    setError("");
    setShowConfirmDelete(false);
  }, [open, initial]);
 
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleLimitChange = (e) => {
    const clean = sanitizeFinancialInput(e.target.value, false);
    setForm((f) => ({ ...f, limit: clean }));
    if (error) setError("");
  };
 
  const handleCategoryChange = (e) => {
    const catId = e.target.value;
    const catObj = CATEGORIES.find((c) => c.id === catId);
    setForm((f) => ({
      ...f,
      category: catId,
      label: catId === "other" ? (f.category === "other" ? f.label : "") : (f.label && isEdit ? f.label : catObj ? catObj.label : f.label),
    }));
  };
 
  const submit = (e) => {
    e.preventDefault();

    const labelVal = validateTextLength(form.label, MAX_NAME_LENGTH, "Category label", true);
    if (!labelVal.isValid) {
      setError(labelVal.error);
      return;
    }

    const noteVal = validateTextLength(form.notes, MAX_NOTE_LENGTH, "Note", false);
    if (!noteVal.isValid) {
      setError(noteVal.error);
      return;
    }

    const minAllowed = isEdit ? initialLimit : 1;
    const limitVal = validateFinancialAmount(form.limit, {
      fieldName: "Monthly limit",
      min: minAllowed,
      minError: isEdit
        ? `Monthly limit can only be increased (minimum ${formatINR(initialLimit)}).`
        : "Enter a monthly limit greater than 0.",
    });

    if (!limitVal.isValid) {
      setError(limitVal.error);
      return;
    }
 
    onSave({
      category: form.category,
      label: form.label.trim(),
      limit: limitVal.numValue,
      notes: form.notes.trim(),
    });
  };
 
  const handleDeleteConfirm = () => {
    const deleteFn = onDelete || onDeleteBudget;
    if (deleteFn && (initial?.rawId || initial?.id)) {
      deleteFn(initial.rawId || initial.id);
    }
    setShowConfirmDelete(false);
    onClose();
  };
 
  return (
    <>
      <Modal open={open && !showConfirmDelete} onClose={onClose} labelledBy="et-budget-title" maxWidth="480px">
        <div className="drawer-panel__head">
          <div className="drawer-panel__head-text">
            <h2 id="et-budget-title" className="drawer-panel__title">
              {isEdit ? "Edit Budget Bucket" : "Add Budget Bucket"}
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
          {/* CATEGORY SELECTOR */}
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="budget-category">
              Budget Category <span className="goal-creation__req">*</span>
            </label>
            <div className="drawer-panel__input-wrapper">
              <Shapes size={16} className="drawer-panel__icon" />
              <select
                id="budget-category"
                className="drawer-panel__select"
                value={form.category}
                onChange={handleCategoryChange}
                disabled={isEdit}
              >
                {CATEGORIES.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
 
          {/* NAME */}
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="budget-label">
              Category Label <span className="goal-creation__req">*</span>
            </label>
            <div className="drawer-panel__input-wrapper">
              <Tag size={16} className="drawer-panel__icon" />
              <input
                id="budget-label"
                type="text"
                maxLength={MAX_NAME_LENGTH}
                className={`drawer-panel__input ${error && !form.label ? "has-error" : ""}`}
                placeholder="e.g. Food, Subscriptions"
                value={form.label}
                onChange={set("label")}
                required
              />
            </div>
          </div>
 
          {/* MONTHLY LIMIT */}
          <div className="drawer-panel__field">
            <div className="drawer-panel__label-row">
              <label className="drawer-panel__label" htmlFor="budget-limit">
                Monthly Limit (₹) <span className="goal-creation__req">*</span>
              </label>
              {isEdit && (
                <span className="drawer-panel__preview-badge" style={{ color: "#38bdf8" }}>
                  Min Limit: <strong>{formatSafeINR(initialLimit)}</strong>
                </span>
              )}
            </div>
            <div className="drawer-panel__input-wrapper">
              <IndianRupee size={16} className="drawer-panel__icon" />
              <input
                id="budget-limit"
                type="text"
                inputMode="numeric"
                maxLength={MAX_FINANCIAL_INT_DIGITS}
                className={`drawer-panel__input ${error && (!form.limit || Number(form.limit) < (isEdit ? initialLimit : 1)) ? "has-error" : ""}`}
                placeholder="Enter monthly limit e.g. ₹10,000 (Max 13 digits)"
                value={form.limit}
                onChange={handleLimitChange}
                required
              />
            </div>
            {isEdit && (
              <span style={{ fontSize: "11px", color: "var(--text-3, #6b7385)", marginTop: "4px" }}>
                Limit can only be increased (cannot decrease below starting {formatINR(initialLimit)}).
              </span>
            )}
          </div>
 
          {/* NOTE */}
          <div className="drawer-panel__field">
            <label className="drawer-panel__label" htmlFor="budget-notes">
              Note <span className="goal-creation__opt">(Optional)</span>
            </label>
            <div className="drawer-panel__input-wrapper">
              <FileText size={16} className="drawer-panel__icon" />
              <input
                id="budget-notes"
                type="text"
                maxLength={MAX_NOTE_LENGTH}
                className="drawer-panel__input"
                placeholder="Additional details about this category..."
                value={form.notes}
                onChange={set("notes")}
              />
            </div>
          </div>
 
          {error && <span className="drawer-panel__err-msg">{error}</span>}
 
          <div
            className="drawer-panel__actions"
            style={{
              marginTop: "auto",
              gridTemplateColumns: isEdit ? "1fr 1fr" : "1fr",
            }}
          >
            {isEdit && (
              <button
                type="button"
                className="drawer-panel__danger-btn"
                onClick={() => setShowConfirmDelete(true)}
              >
                <Trash2 size={15} /> Delete Budget
              </button>
            )}
            <button
              type="submit"
              className="drawer-panel__btn-submit"
              style={{ height: "44px", borderRadius: "10px", fontWeight: 700, fontSize: "14px" }}
            >
              {isEdit ? "Update Budget" : "Create Budget"}
            </button>
          </div>
        </form>
      </Modal>
 
      {/* Portaled Delete Confirmation Modal matching Goals DeleteConfirmationModal */}
      {showConfirmDelete &&
        createPortal(
          <div className="delete-modal-overlay" onMouseDown={() => setShowConfirmDelete(false)}>
            <div className="delete-modal" onMouseDown={(e) => e.stopPropagation()}>
              <div className="delete-modal__icon-wrap">
                <AlertTriangle size={28} className="delete-modal__icon" />
              </div>
 
              <button
                type="button"
                className="delete-modal__close-btn"
                onClick={() => setShowConfirmDelete(false)}
                aria-label="Close"
              >
                <X size={16} />
              </button>
 
              <h3 className="delete-modal__title">Delete Budget Bucket?</h3>
              <p className="delete-modal__desc">This action cannot be undone.</p>
 
              <div className="delete-modal__actions">
                <button
                  type="button"
                  className="delete-modal__btn-cancel"
                  onClick={() => setShowConfirmDelete(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="delete-modal__btn-confirm"
                  onClick={handleDeleteConfirm}
                >
                  Confirm Delete
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  );
}
