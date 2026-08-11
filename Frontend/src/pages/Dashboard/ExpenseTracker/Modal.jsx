import { useEffect } from "react";
import { createPortal } from "react-dom";
 
/**
 * Base modal shell used by Expense Tracker popups.
 * Renders via React Portal directly into document.body to ensure:
 * - 100% full-viewport coverage regardless of parent scroll
 * - Perfect vertical & horizontal centering
 * - No clipping or transform interference from dashboard containers
 */
export default function Modal({ open, onClose, children, labelledBy, maxWidth = "480px" }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.classList.add("modal-open");
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("modal-open");
    };
  }, [open, onClose]);
 
  if (!open) return null;
 
  return createPortal(
    <div className="et-modal-overlay" onMouseDown={onClose}>
      <div
        className="et-modal-panel"
        style={{ maxWidth }}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>,
    document.body
  );
}
