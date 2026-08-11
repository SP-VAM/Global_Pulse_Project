/**
 * ============================================================================
 * LEARNING CARD COMPONENT
 * ============================================================================
 * Reusable vertical card component for rendering individual course modules.
 */

import React from "react";
import "./LearningCard.css";

/**
 * LearningCard
 * @param {Object} props
 * @param {Object} props.course - Course metadata object
 * @param {Function} props.openCourse - Click handler function to launch video modal
 */
export default function LearningCard({ course, openCourse }) {
  return (
    <div
      className="learning-card"
      onClick={() => openCourse(course)}
    >
      {/* Module Thumbnail Image */}
      <img
        src={course.image}
        alt={course.title}
        className="learning-image"
      />

      {/* Module Content Info */}
      <div className="learning-content">
        {/* Difficulty Level Badge */}
        <span className={`learning-level ${course.level.toLowerCase()}`}>
          {course.level}
        </span>

        {/* Module Title */}
        <h3>{course.title}</h3>

        {/* Short Description */}
        <p>{course.description}</p>

        {/* Card Action Footer */}
        <div className="learning-footer">
          <button
            className="learning-btn"
            onClick={(e) => {
              e.stopPropagation();
              openCourse(course);
            }}
          >
            Start Module →
          </button>
        </div>
      </div>
    </div>
  );
}
