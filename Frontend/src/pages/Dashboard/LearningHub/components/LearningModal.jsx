import React from "react";
import { X, ExternalLink } from "lucide-react";

/**
 * LearningModal Component
 * Embedded 16:9 YouTube video player modal
 * @param {Object} props
 * @param {Object} props.course - Currently selected course object
 * @param {Function} props.onClose - Close modal handler
 */
export default function LearningModal({ course, onClose }) {
  if (!course) return null;

  const embedSrc =
    course.embedUrl ||
    (course.videoId
      ? `https://www.youtube.com/embed/${course.videoId}?autoplay=1`
      : "");

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.82)",
        backdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "16px",
      }}
    >
      <div
        className="lh-video-modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "relative",
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
            background: "rgba(13, 17, 27, 0.9)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                color: "#38bdf8",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                padding: "2px 8px",
                borderRadius: "4px",
                background: "rgba(56, 189, 248, 0.12)",
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
              }}
            >
              {course.title}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              padding: "4px",
              display: "flex",
              alignItems: "center",
            }}
            aria-label="Close modal"
          >
            <X size={20} />
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
            background: "rgba(13, 17, 27, 0.9)",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <span style={{ fontSize: "12.5px", color: "#94a3b8" }}>
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
    </div>
  );
}
