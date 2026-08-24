import React, { useState } from "react";
import { Globe, Shield } from "lucide-react";
import LegalDocModal from "./LegalDocModal";
import ContactModal from "./ContactModal";
import { privacyPolicy } from "../../../data/privacyPolicy";
import { termsConditions } from "../../../data/termsConditions";
import { disclaimer } from "../../../data/disclaimer";
import "./Footer.css";

/**
 * Premium Fintech SaaS Footer for GlobalPulse Dashboard Shell.
 * Clean 3-section layout (Branding & Copyright | Visual Links | Status & Security).
 */
export default function Footer() {
  const [activeModal, setActiveModal] = useState(null);

  return (
    <>
      <footer className="gp-global-footer">
        <div className="gp-global-footer__content">
          {/* LEFT SECTION: Branding & Copyright */}
          <div className="gp-global-footer__left">
            <Globe size={16} className="gp-global-footer__icon" />
            <span className="gp-global-footer__brand">GlobalPulse</span>
            <span className="gp-global-footer__copyright">
              © {new Date().getFullYear()} GlobalPulse Financial Intelligence
            </span>
          </div>

          {/* CENTER SECTION: Muted Legal & Contact Links */}
          <div className="gp-global-footer__center">
            <button
              className="gp-global-footer__link"
              onClick={() => setActiveModal("privacy")}
              aria-haspopup="dialog"
            >
              Privacy
            </button>
            <span className="gp-global-footer__link-dot">•</span>
            <button
              className="gp-global-footer__link"
              onClick={() => setActiveModal("terms")}
              aria-haspopup="dialog"
            >
              Terms
            </button>
            <span className="gp-global-footer__link-dot">•</span>
            <button
              className="gp-global-footer__link"
              onClick={() => setActiveModal("disclaimer")}
              aria-haspopup="dialog"
            >
              Disclaimer
            </button>
            <span className="gp-global-footer__link-dot">•</span>
            <button
              className="gp-global-footer__link"
              onClick={() => setActiveModal("contact")}
              aria-haspopup="dialog"
            >
              Contact
            </button>
          </div>

          {/* RIGHT SECTION: Operational Status & SSL Encryption */}
          <div className="gp-global-footer__right">
            <span className="gp-global-footer__status">
              <span className="gp-global-footer__dot" /> Systems Operational
            </span>
            <span className="gp-global-footer__divider">•</span>
            <span className="gp-global-footer__sec">
              <Shield size={13} className="gp-global-footer__sec-icon" /> 256-bit SSL Encrypted
            </span>
          </div>
        </div>
      </footer>

      {/* Legal & Document Modals */}
      <LegalDocModal
        isOpen={activeModal === "privacy"}
        doc={privacyPolicy}
        onClose={() => setActiveModal(null)}
      />
      <LegalDocModal
        isOpen={activeModal === "terms"}
        doc={termsConditions}
        onClose={() => setActiveModal(null)}
      />
      <LegalDocModal
        isOpen={activeModal === "disclaimer"}
        doc={disclaimer}
        onClose={() => setActiveModal(null)}
      />
      <ContactModal
        isOpen={activeModal === "contact"}
        onClose={() => setActiveModal(null)}
      />
    </>
  );
}

