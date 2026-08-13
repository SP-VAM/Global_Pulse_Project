import React, { useEffect } from "react";
import ReactDOM from "react-dom";
import { X, ExternalLink } from "lucide-react";

/**
 * LearningModal Component
 * Centered 16:9 YouTube video player modal portaled directly to document.body
 * @param {Object} props
 * @param {Object} props.course - Currently selected course object
 * @param {Function} props.onClose - Close modal handler
 */
export default function LearningModal({ course, onClose }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };

    if (course) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [course, onClose]);

  if (!course) return null;

  const embedSrc =
    course.embedUrl ||
    (course.videoId
      ? `https://www.youtube.com/embed/${course.videoId}?autoplay=1`
      : "");

  return ReactDOM.createPortal(
    <div
      className="modal-overlay"
      onClick={onClose}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: "100vw",
        height: "100vh",
        backgroundColor: "rgba(4, 6, 12, 0.85)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 99999,
        padding: "20px",
        boxSizing: "border-box",
      }}
    >
      <div
        className="lh-video-modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "relative",
          width: "100%",
          maxWidth: "920px",
          maxHeight: "90vh",
          background: "rgba(13, 17, 27, 0.96)",
          border: "1px solid rgba(255, 255, 255, 0.14)",
          borderRadius: "16px",
          boxShadow: "0 25px 60px -15px rgba(0, 0, 0, 0.95), 0 0 35px -5px rgba(56, 189, 248, 0.25)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 20px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            background: "rgba(13, 17, 27, 0.95)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                color: "#38bdf8",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                padding: "3px 9px",
                borderRadius: "4px",
                background: "rgba(56, 189, 248, 0.12)",
                flexShrink: 0,
              }}
            >
              {course.level}
            </span>
            <h3
              style={{
                margin: 0,
                fontSize: "15px",
                fontWeight: "700",
                color: "#ffffff",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {course.title}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "rgba(255, 255, 255, 0.06)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "8px",
              color: "#94a3b8",
              cursor: "pointer",
              padding: "6px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#ffffff";
              e.currentTarget.style.background = "rgba(255, 255, 255, 0.12)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#94a3b8";
              e.currentTarget.style.background = "rgba(255, 255, 255, 0.06)";
            }}
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* 16:9 Video Wrapper */}
        <div className="lh-video-wrapper">
          <iframe
            src={embedSrc}
            title={course.title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          ></iframe>
        </div>

        {/* Modal Footer */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "12px 20px",
            background: "rgba(13, 17, 27, 0.95)",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
            gap: "12px",
          }}
        >
          <span
            style={{
              fontSize: "12.5px",
              color: "#94a3b8",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {course.description}
          </span>
          {course.video && (
            <a
              href={course.video}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "12px",
                fontWeight: "600",
                color: "#38bdf8",
                textDecoration: "none",
                flexShrink: 0,
              }}
            >
              Watch on YouTube <ExternalLink size={13} />
            </a>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
