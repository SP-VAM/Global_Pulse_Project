import React, { useState } from "react";
import { createPortal } from "react-dom";
import { X, Calendar, Clock, Banknote, CheckCircle2, Trash2, Pencil, AlertTriangle } from "lucide-react";
import Modal from "./Modal.jsx";
import { CATEGORY_MAP, formatINR, prettyDate } from "./data.js";
 
/**
 * Transaction Detail Modal with exact Goals Delete Confirmation Dialog.
 */
export default function TransactionDetailModal({ open, tx, onClose, onEdit, onDelete }) {
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
 
  if (!tx) return null;
 
  const cat = tx.category ? CATEGORY_MAP[tx.category] : null;
  const accent = tx.type === "income" ? "#2ec27e" : cat?.color ?? "#38bdf8";
 
  const handleClose = () => {
    setShowConfirmDelete(false);
    onClose();
  };
 
  const handleDelete = () => {
    onDelete(tx.id);
    setShowConfirmDelete(false);
  };
 
  return (
    <>
      <Modal open={open && !showConfirmDelete} onClose={handleClose} labelledBy="et-detail-title" maxWidth="480px">
        <div className="drawer-panel__head">
          <div className="drawer-panel__head-text">
            <h2 id="et-detail-title" className="drawer-panel__title">
              Transaction Details
            </h2>
            <p className="drawer-panel__subtitle" style={{ color: accent, fontWeight: 700 }}>
              {tx.type === "income" ? "INCOME" : (cat?.label ?? "EXPENSE").toUpperCase()}
            </p>
          </div>
          <button type="button" className="drawer-panel__close-btn" onClick={handleClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
 
        <div className="drawer-panel__form">
          <div
            style={{
              textAlign: "center",
              padding: "16px",
              borderRadius: "10px",
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid var(--border-strong, rgba(255, 255, 255, 0.12))",
            }}
          >
            <div style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff" }}>
              {tx.notes || (cat ? cat.label : "Income")}
            </div>
            <div
              style={{
                fontSize: "26px",
                fontWeight: 800,
                color: tx.type === "income" ? "#2ec27e" : "#f4f6fb",
                marginTop: "4px",
              }}
            >
              {tx.type === "income" ? "+" : "-"}
              {formatINR(tx.amount)}
            </div>
          </div>
 
          <div className="goal-modal__dates-row">
            <div className="drawer-panel__field">
              <label className="drawer-panel__label">Date</label>
              <div className="drawer-panel__input-wrapper">
                <Calendar size={16} className="drawer-panel__icon" />
                <div className="drawer-panel__input" style={{ display: "flex", alignItems: "center" }}>
                  {prettyDate(tx.date)}
                </div>
              </div>
            </div>
 
            <div className="drawer-panel__field">
              <label className="drawer-panel__label">Time</label>
              <div className="drawer-panel__input-wrapper">
                <Clock size={16} className="drawer-panel__icon" />
                <div className="drawer-panel__input" style={{ display: "flex", alignItems: "center" }}>
                  {tx.time || "—"}
                </div>
              </div>
            </div>
          </div>
 
          <div className="goal-modal__dates-row">
            <div className="drawer-panel__field">
              <label className="drawer-panel__label">Payment Method</label>
              <div className="drawer-panel__input-wrapper">
                <Banknote size={16} className="drawer-panel__icon" />
                <div className="drawer-panel__input" style={{ display: "flex", alignItems: "center" }}>
                  {tx.method}
                </div>
              </div>
            </div>
 
            <div className="drawer-panel__field">
              <label className="drawer-panel__label">Status</label>
              <div className="drawer-panel__input-wrapper">
                <CheckCircle2 size={16} className="drawer-panel__icon" style={{ color: "#2ec27e" }} />
                <div className="drawer-panel__input gp-pos" style={{ display: "flex", alignItems: "center", fontWeight: 700 }}>
                  {tx.status || "Completed"}
                </div>
              </div>
            </div>
          </div>
 
          <div className="drawer-panel__actions">
            <button
              type="button"
              className="drawer-panel__danger-btn"
              onClick={() => setShowConfirmDelete(true)}
            >
              <Trash2 size={15} /> Delete
            </button>
            <button type="button" className="drawer-panel__btn-submit" onClick={() => onEdit(tx)}>
              <Pencil size={15} style={{ marginRight: "6px" }} /> Edit Transaction
            </button>
          </div>
        </div>
      </Modal>
 
      {/* Portaled Delete Confirmation Modal matching Goals master DeleteConfirmationModal */}
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
 
              <h3 className="delete-modal__title">Delete Transaction?</h3>
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
                  onClick={handleDelete}
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
