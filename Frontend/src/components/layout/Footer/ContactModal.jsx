import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";
import "./ContactModal.css";

export default function ContactModal({ isOpen, onClose }) {
  const modalRef = useRef(null);

  // Focus trap and escape key handler
  useEffect(() => {
    if (!isOpen) return;

    document.body.classList.add("modal-open");

    const focusableElements = modalRef.current?.querySelectorAll(
      'button, a, [tabindex="0"]'
    );
    const firstElement = focusableElements?.[0];
    const lastElement = focusableElements?.[focusableElements.length - 1];

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose();
      }

      if (e.key === "Tab") {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement?.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement?.focus();
          }
        }
      }
    };

    firstElement?.focus();
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.classList.remove("modal-open");
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="contact-modal-overlay" onClick={onClose}>
      <div
        className="contact-modal-card"
        ref={modalRef}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="contact-modal-title"
      >
        {/* Modal Header */}
        <header className="contact-modal-header">
          <h2 id="contact-modal-title" className="contact-modal-title">
            Contact Us
          </h2>
          <button
            className="contact-modal-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </header>

        {/* Modal Body */}
        <div className="contact-modal-body">
          <div className="contact-info-container">
            <p className="contact-info-intro">
              Need help or have questions about GlobalPulse?<br />
              You can reach our support team using the details below.
            </p>

            <div className="contact-info-section">
              <span className="contact-info-label">Email</span>
              <a href="mailto:support@globalpulse.com" className="contact-info-value">
                support@globalpulse.com
              </a>
            </div>

            <p className="contact-info-desc">
              For technical assistance, account-related queries,<br />
              or general enquiries, contact our support team.
            </p>

            <button className="contact-close-action-btn" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

