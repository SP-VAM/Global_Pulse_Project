import React from "react";
import { AlertTriangle, X } from "lucide-react";
import "./DeleteConfirmationModal.css";

export default function DeleteConfirmationModal({
  onClose,
  onConfirmDelete,
}) {
  return (
    <div className="delete-modal-overlay" onClick={onClose}>
      <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
        <div className="delete-modal__icon-wrap">
          <AlertTriangle size={28} className="delete-modal__icon" />
        </div>

        <button
          type="button"
          className="delete-modal__close-btn"
          onClick={onClose}
          aria-label="Close"
        >
          <X size={16} />
        </button>

        <h3 className="delete-modal__title">Delete this goal?</h3>
        <p className="delete-modal__desc">This action cannot be undone.</p>

        <div className="delete-modal__actions">
          <button
            type="button"
            className="delete-modal__btn-cancel"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="delete-modal__btn-confirm"
            onClick={onConfirmDelete}
          >
            Confirm Delete
          </button>
        </div>
      </div>
    </div>
  );
}
