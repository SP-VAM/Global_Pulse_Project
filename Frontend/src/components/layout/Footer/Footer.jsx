import React from "react";
import { Globe, Shield } from "lucide-react";
import "./Footer.css";

/**
 * Premium Fintech SaaS Footer for GlobalPulse Dashboard Shell.
 * Clean 3-section layout (Branding & Copyright | Visual Links | Status & Security).
 */
export default function Footer() {
  return (
    <footer className="gp-global-footer">
      <div className="gp-global-footer__content">
        {/* LEFT SECTION: Branding & Copyright */}
        <div className="gp-global-footer__left">
          <div className="gp-global-footer__brand-wrapper">
            <Globe size={16} className="gp-global-footer__icon" />
            <span className="gp-global-footer__brand">GlobalPulse</span>
          </div>
          <span className="gp-global-footer__copyright">
            © {new Date().getFullYear()} GlobalPulse Financial Intelligence
          </span>
        </div>

        {/* CENTER SECTION: Muted Legal & Contact Links */}
        <div className="gp-global-footer__center">
          <span className="gp-global-footer__link">Privacy</span>
          <span className="gp-global-footer__link-dot">•</span>
          <span className="gp-global-footer__link">Terms</span>
          <span className="gp-global-footer__link-dot">•</span>
          <span className="gp-global-footer__link">Disclaimer</span>
          <span className="gp-global-footer__link-dot">•</span>
          <span className="gp-global-footer__link">Contact</span>
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
  );
}
