import React from "react";
import { Play, Clock } from "lucide-react";

/**
 * ActiveModuleCard Component
 * @param {Object} props
 * @param {Object} props.course - Course metadata object
 * @param {Function} props.openCourse - Click handler function to launch video modal
 */
export default function ActiveModuleCard({ course, openCourse }) {
  if (!course) return null;

  return (
    <div className="lh-active-card" onClick={() => openCourse(course)}>
      <div className="lh-active-card__img-box">
        <img src={course.image} alt={course.title} className="lh-active-card__img" />
        <div className="lh-active-card__play">
          <Play size={12} fill="currentColor" />
        </div>
      </div>
      <div className="lh-active-card__content">
        <h4 className="lh-active-card__title">{course.title}</h4>
        <div className="lh-active-card__meta">
          <span className="lh-active-card__duration">
            <Clock size={10} /> {course.duration}
          </span>
        </div>
      </div>
      <button
        type="button"
        className="lh-active-card__btn"
        onClick={(e) => {
          e.stopPropagation();
          openCourse(course);
        }}
      >
        Resume →
      </button>
    </div>
  );
}
