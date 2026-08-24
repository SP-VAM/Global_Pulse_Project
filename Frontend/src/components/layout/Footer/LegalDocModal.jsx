import React, { useEffect, useRef } from "react";
import { X, Download, Shield } from "lucide-react";
import jsPDF from "jspdf";
import "./LegalDocModal.css";

export default function LegalDocModal({ doc, isOpen, onClose }) {
  const modalRef = useRef(null);

  // Focus trap and escape key handler
  useEffect(() => {
    if (!isOpen) return;

    // Prevent body scrolling
    document.body.classList.add("modal-open");

    const focusableElements = modalRef.current?.querySelectorAll(
      'button, [tabindex="0"]'
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

  // Format today's date in "24 August 2026" format (day month year)
  const todayFormatted = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const handleDownloadPDF = () => {
    try {
      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "pt",
        format: "a4",
      });

      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 40;
      const contentWidth = pageWidth - margin * 2;
      const bottomMargin = 50;
      let currentY = 60;

      const drawPageFooter = () => {
        const pageCount = pdf.internal.getNumberOfPages();
        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(8.5);
        pdf.setTextColor(148, 163, 184);

        // Line above footer
        pdf.setDrawColor(226, 232, 240);
        pdf.setLineWidth(0.5);
        pdf.line(margin, pageHeight - 30, pageWidth - margin, pageHeight - 30);

        pdf.text("GlobalPulse • Legal Information", margin, pageHeight - 15);
        pdf.text(`Page ${pageCount}`, pageWidth - margin, pageHeight - 15, {
          align: "right",
        });
      };

      const checkPageSpace = (heightNeeded) => {
        if (currentY + heightNeeded > pageHeight - bottomMargin) {
          drawPageFooter();
          pdf.addPage();
          currentY = 60; // Top padding on next pages
        }
      };

      // --- PAGE 1 HEADER ---
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(10);
      pdf.setTextColor(30, 41, 59); // Slate-800
      pdf.text("GlobalPulse", pageWidth / 2, currentY, { align: "center" });
      currentY += 25;

      // Title
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(22);
      pdf.text(doc.title, pageWidth / 2, currentY, { align: "center" });
      currentY += 20;

      // Effective Date
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(10);
      pdf.setTextColor(100, 116, 139); // Slate-500
      pdf.text(
        `${doc.effectiveDatePrefix}${todayFormatted}`,
        pageWidth / 2,
        currentY,
        { align: "center" }
      );
      currentY += 30;

      // Intro Paragraphs
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(10.5);
      pdf.setTextColor(30, 41, 59);

      for (const introText of doc.intro) {
        const isImportant =
          introText.startsWith("Important:") ||
          introText.startsWith("Project note:");
        const lines = pdf.splitTextToSize(
          introText,
          isImportant ? contentWidth - 20 : contentWidth
        );
        const textHeight = lines.length * 15;

        if (isImportant) {
          const boxHeight = textHeight + 16;
          checkPageSpace(boxHeight + 15);

          // Draw callout box
          pdf.setFillColor(240, 246, 255); // Blue-50
          pdf.setDrawColor(219, 234, 254); // Blue-100
          pdf.setLineWidth(1);
          pdf.roundedRect(margin, currentY, contentWidth, boxHeight, 3, 3, "FD");

          pdf.setFont("helvetica", "normal");
          pdf.setFontSize(10);
          pdf.setTextColor(23, 37, 84); // Blue-950

          pdf.text(lines, margin + 10, currentY + 14, { lineHeightFactor: 1.5 });
          currentY += boxHeight + 15;
        } else {
          checkPageSpace(textHeight + 15);
          pdf.setFont("helvetica", "normal");
          pdf.setFontSize(10.5);
          pdf.setTextColor(30, 41, 59);
          pdf.text(lines, margin, currentY, { lineHeightFactor: 1.5 });
          currentY += textHeight + 15;
        }
      }

      // Sections
      for (const sec of doc.sections) {
        checkPageSpace(35);
        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(13);
        pdf.setTextColor(30, 41, 59);
        pdf.text(sec.title, margin, currentY);
        currentY += 18;

        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(10);
        pdf.setTextColor(51, 65, 85); // Slate-700

        for (const para of sec.paragraphs) {
          const lines = pdf.splitTextToSize(para, contentWidth);
          const textHeight = lines.length * 14;
          checkPageSpace(textHeight + 12);
          pdf.text(lines, margin, currentY, { lineHeightFactor: 1.4 });
          currentY += textHeight + 12;
        }
        currentY += 8;
      }

      // About this document
      if (doc.aboutDoc) {
        const lines = pdf.splitTextToSize(doc.aboutDoc.text, contentWidth);
        const textHeight = lines.length * 14;
        checkPageSpace(textHeight + 35);

        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(11);
        pdf.setTextColor(30, 41, 59);
        pdf.text(doc.aboutDoc.title, margin, currentY);
        currentY += 16;

        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(9.5);
        pdf.setTextColor(100, 116, 139);
        pdf.text(lines, margin, currentY, { lineHeightFactor: 1.4 });
        currentY += textHeight + 10;
      }

      drawPageFooter();

      const filename = `GlobalPulse_${doc.title.replace(/[^a-zA-Z0-9_-]/g, "_")}.pdf`;
      pdf.save(filename);
    } catch (error) {
      console.error("PDF generation failed:", error);
    }
  };

  return (
    <div className="legal-modal-overlay" onClick={onClose}>
      <div
        className="legal-modal-card"
        ref={modalRef}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="legal-modal-title"
      >
        {/* Modal Header */}
        <header className="legal-modal-header">
          <div className="legal-modal-header__title-wrap">
            <h2 id="legal-modal-title" className="legal-modal-title">
              {doc.title}
            </h2>
            <span className="legal-modal-effective-date">
              {doc.effectiveDatePrefix}
              {todayFormatted}
            </span>
          </div>
          <div className="legal-modal-actions">
            <button
              className="legal-modal-download-btn"
              onClick={handleDownloadPDF}
              aria-label="Download PDF Document"
            >
              <Download size={15} />
              <span>Download PDF</span>
            </button>
            <button
              className="legal-modal-close-btn"
              onClick={onClose}
              aria-label="Close dialog"
            >
              <X size={18} />
            </button>
          </div>
        </header>

        {/* Modal Scrollable Content */}
        <div className="legal-modal-content">
          <div className="legal-modal-intro">
            {doc.intro.map((introText, index) => {
              const isImportant =
                introText.startsWith("Important:") ||
                introText.startsWith("Project note:");
              return (
                <p
                  key={index}
                  className={`legal-modal-paragraph ${
                    isImportant ? "legal-modal-callout" : ""
                  }`}
                >
                  {introText}
                </p>
              );
            })}
          </div>

          <div className="legal-modal-sections">
            {doc.sections.map((sec, index) => (
              <section key={index} className="legal-modal-section">
                <h3 className="legal-modal-section-title">{sec.title}</h3>
                {sec.paragraphs.map((para, pIndex) => (
                  <p key={pIndex} className="legal-modal-paragraph">
                    {para}
                  </p>
                ))}
              </section>
            ))}
          </div>

          {doc.aboutDoc && (
            <div className="legal-modal-about">
              <h4 className="legal-modal-about-title">{doc.aboutDoc.title}</h4>
              <p className="legal-modal-about-text">{doc.aboutDoc.text}</p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <footer className="legal-modal-footer">
          <span className="legal-modal-footer-brand">GlobalPulse</span>
          <span className="legal-modal-footer-security">
            <Shield size={12} /> 256-bit SSL Secure Viewer
          </span>
        </footer>
      </div>
    </div>
  );
}
