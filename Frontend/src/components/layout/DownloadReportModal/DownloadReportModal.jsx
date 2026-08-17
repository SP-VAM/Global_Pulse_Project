import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Download, X } from "lucide-react";
import "./DownloadReportModal.css";

export default function DownloadReportModal({ open, onClose, onConfirm, periodLabel }) {
  const overlayRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    document.body.classList.add("modal-open");
    function handleKeyDown(e) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.classList.remove("modal-open");
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  if (!open || typeof document === "undefined") return null;

  const handleBackdropClick = (e) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  const modalNode = (
    <div
      className="download-modal-overlay"
      ref={overlayRef}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="download-modal-title"
    >
      <div className="download-modal-box">
        <div className="download-modal-head">
          <div className="download-modal-icon">
            <Download size={22} />
          </div>
          <h2 id="download-modal-title" className="download-modal-title">
            Download Report
          </h2>
          <button
            type="button"
            className="download-modal-close"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        <div className="download-modal-body">
          <p>
            Are you sure you want to download the Income & Expense PDF report for{" "}
            <strong style={{ color: "#f8fafc" }}>{periodLabel || "this period"}</strong>?
          </p>
        </div>

        <div className="download-modal-actions">
          <button
            type="button"
            className="download-btn download-btn--cancel"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="download-btn download-btn--confirm"
            onClick={() => {
              onConfirm();
              onClose();
            }}
          >
            <Download size={15} />
            <span>Download PDF</span>
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalNode, document.body);
}
