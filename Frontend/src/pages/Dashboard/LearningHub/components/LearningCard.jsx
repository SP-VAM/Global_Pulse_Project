import React from "react";
import { Clock, CheckCircle2 } from "lucide-react";
import "./LearningCard.css";

/**
 * LearningCard
 * @param {Object} props
 * @param {Object} props.course - Course metadata object
 * @param {Function} props.openCourse - Click handler function to launch video modal
 * @param {Object} [props.progress] - Watch progress data { progressPercentage, isCompleted }
 */
export default function LearningCard({ course, openCourse, progress }) {
  const totalSec = course?.durationSeconds || progress?.totalSeconds || 1800;
  const watchSec = progress?.progressSeconds || 0;
  const progressPct = totalSec > 0
    ? Math.min(100, Math.round((watchSec / totalSec) * 100))
    : Math.min(100, Math.max(0, progress?.progressPercentage || 0));
  const isCompleted = progress?.isCompleted || (progressPct >= 90);

  return (
    <div className="learning-card" onClick={() => openCourse(course)}>
      {/* Module Thumbnail Image Container */}
      <div className="learning-image-wrapper" style={{ position: "relative" }}>
        <img src={course.image} alt={course.title} className="learning-image" />
        
        {/* Top Badges overlay: Category & CC indicator */}
        <div className="learning-card__image-overlay">
          <span className="learning-category-tag">{course.category || "General"}</span>
          {course.ccAvailable !== false && (
            <span className="learning-cc-tag" title="Closed Captions Available">
              CC
            </span>
          )}
        </div>

        {/* Completion Ribbon/Badge if completed */}
        {isCompleted && (
          <div className="learning-completed-badge">
            <CheckCircle2 size={12} /> Completed
          </div>
        )}
      </div>

      {/* Module Content Info */}
      <div className="learning-content">
        {/* Top Header Row: Level + Duration */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
          <span className={`learning-level ${course.level.toLowerCase()}`}>
            {course.level}
          </span>
          <span className="learning-duration">
            <Clock size={11} style={{ marginRight: "3px" }} />
            {course.duration}
          </span>
        </div>

        {/* Module Title */}
        <h3>{course.title}</h3>

        {/* Short Description */}
        <p>{course.description}</p>

        {/* Progress Bar (if watched) */}
        {progressPct > 0 && (
          <div className="learning-progress-container">
            <div className="learning-progress-bar">
              <div
                className={`learning-progress-fill ${isCompleted ? "is-completed" : ""}`}
                style={{ width: `${progressPct}%` }}
              ></div>
            </div>
            <span className="learning-progress-text">
              {isCompleted ? "100% Completed" : `${progressPct}% watched`}
            </span>
          </div>
        )}

        {/* Card Action Footer */}
        <div className="learning-footer">
          <button
            className={`learning-btn ${isCompleted ? "btn-completed" : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              openCourse(course);
            }}
          >
            {isCompleted ? "Review Module ✓" : progressPct > 0 ? "Resume Module →" : "Start Module →"}
          </button>
        </div>
      </div>
    </div>
  );
}
