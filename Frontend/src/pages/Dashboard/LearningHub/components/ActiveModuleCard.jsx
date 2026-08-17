import React from "react";
import { Play, Clock, CheckCircle2 } from "lucide-react";

/**
 * ActiveModuleCard Component
 * @param {Object} props
 * @param {Object} props.course - Course metadata object
 * @param {Function} props.openCourse - Click handler function to launch video modal
 * @param {Object} [props.progress] - Watch progress data
 */
export default function ActiveModuleCard({ course, openCourse, progress }) {
  if (!course) return null;

  const totalSec = course?.durationSeconds || progress?.totalSeconds || 1800;
  const watchSec = progress?.progressSeconds || 0;
  const progressPct = totalSec > 0
    ? Math.min(100, Math.round((watchSec / totalSec) * 100))
    : Math.min(100, Math.max(0, progress?.progressPercentage || 0));
  const isCompleted = progress?.isCompleted || (progressPct >= 90);

  // Format position in MM:SS if seconds available
  const formatTime = (totalSec) => {
    if (!totalSec) return "";
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  const resumeTimeStr = progress?.progressSeconds ? formatTime(progress.progressSeconds) : null;

  return (
    <div className="lh-active-card" onClick={() => openCourse(course)}>
      <div className="lh-active-card__img-box">
        <img src={course.image} alt={course.title} className="lh-active-card__img" />
        <div className="lh-active-card__play">
          {isCompleted ? <CheckCircle2 size={13} color="#10b981" /> : <Play size={12} fill="currentColor" />}
        </div>
      </div>
      <div className="lh-active-card__content">
        <h4 className="lh-active-card__title">{course.title}</h4>
        <div className="lh-active-card__meta">
          <span className="lh-active-card__duration">
            <Clock size={10} /> {course.duration}
          </span>
          {isCompleted ? (
            <span style={{ fontSize: "10px", fontWeight: "700", color: "#10b981", marginLeft: "8px" }}>
              ✓ Completed
            </span>
          ) : progressPct > 0 ? (
            <span style={{ fontSize: "10px", fontWeight: "600", color: "#38bdf8", marginLeft: "8px" }}>
              {progressPct}% watched
            </span>
          ) : null}
        </div>
        {/* Progress Bar */}
        {progressPct > 0 && (
          <div style={{ width: "100%", height: "3px", background: "rgba(255,255,255,0.1)", borderRadius: "2px", marginTop: "4px", overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                width: `${progressPct}%`,
                background: isCompleted ? "#10b981" : "#38bdf8",
                transition: "width 0.3s ease"
              }}
            />
          </div>
        )}
      </div>
      <button
        type="button"
        className="lh-active-card__btn"
        style={{
          background: isCompleted ? "rgba(16, 185, 129, 0.15)" : undefined,
          color: isCompleted ? "#10b981" : undefined,
          borderColor: isCompleted ? "rgba(16, 185, 129, 0.4)" : undefined,
        }}
        onClick={(e) => {
          e.stopPropagation();
          openCourse(course);
        }}
      >
        {isCompleted ? "Review ✓" : resumeTimeStr ? `Resume (${resumeTimeStr}) →` : "Resume →"}
      </button>
    </div>
  );
}
