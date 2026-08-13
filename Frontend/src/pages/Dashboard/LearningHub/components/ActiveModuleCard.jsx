import React from "react";
import { Play, Clock } from "lucide-react";

/**
 * ActiveModuleCard Component
 * @param {Object} props
 * @param {Object} props.course - Course metadata object
 * @param {Function} props.openCourse - Click handler function to launch video modal
 */
export default function ActiveModuleCard({ course, openCourse, isPlaying }) {
  if (!course) return null;

  return (
    <div className={`lh-active-card ${isPlaying ? "lh-active-card--playing" : ""}`} onClick={() => openCourse(course)}>
      <div className="lh-active-card__img-box">
        <img src={course.image} alt={course.title} className="lh-active-card__img" />
        <div className="lh-active-card__play" style={{ background: isPlaying ? "#2ec27e" : "rgba(0, 0, 0, 0.7)" }}>
          <Play size={12} fill="currentColor" />
        </div>
      </div>
      <div className="lh-active-card__content">
        {isPlaying && (
          <span style={{ fontSize: "10px", fontWeight: "700", color: "#2ec27e", letterSpacing: "0.5px", display: "inline-flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#2ec27e", boxShadow: "0 0 6px #2ec27e" }}></span> NOW PLAYING
          </span>
        )}
        <h4 className="lh-active-card__title" style={{ marginTop: isPlaying ? "2px" : "0" }}>{course.title}</h4>
        <div className="lh-active-card__meta">
          <span className="lh-active-card__duration">
            <Clock size={10} /> {course.duration}
          </span>
        </div>
      </div>
      <button
        type="button"
        className="lh-active-card__btn"
        style={{ background: isPlaying ? "rgba(46, 194, 126, 0.15)" : "", color: isPlaying ? "#2ec27e" : "", borderColor: isPlaying ? "rgba(46, 194, 126, 0.3)" : "" }}
        onClick={(e) => {
          e.stopPropagation();
          openCourse(course);
        }}
      >
        {isPlaying ? "Playing ▶" : "Resume →"}
      </button>
    </div>
  );
}
