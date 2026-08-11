import React, { useState, useMemo } from "react";
import { GraduationCap, BookOpen, History, Search } from "lucide-react";

import learningData from "./learningData.js";
import LearningCard from "./components/LearningCard.jsx";
import ActiveModuleCard from "./components/ActiveModuleCard.jsx";
import LearningModal from "./components/LearningModal.jsx";
import "./LearningHub.css";

/**
 * LearningHub Component
 * Configured with 3-card single row layout for Active Modules bar.
 */
export default function LearningHub() {
  // Recently watched learning modules stored in localStorage (max 3 for 1 clean row)
  const [activeModules, setActiveModules] = useState(() => {
    try {
      const saved = localStorage.getItem("recent_learning_modules_v3");
      if (saved) return JSON.parse(saved);
      // Default to top 3 seeded courses for clean initial UX
      return learningData.slice(0, 3);
    } catch (e) {
      return learningData.slice(0, 3);
    }
  });

  // Currently open course for embedded YouTube video modal
  const [selectedCourse, setSelectedCourse] = useState(null);

  // Active level filter ('All', 'Beginner', 'Intermediate', 'Advanced')
  const [activeFilter, setActiveFilter] = useState("All");

  // Search query filter
  const [searchQuery, setSearchQuery] = useState("");

  const openCourse = (course) => {
    setSelectedCourse(course);

    setActiveModules((prev) => {
      const filtered = prev.filter((item) => String(item.id) !== String(course.id));
      const updated = [course, ...filtered].slice(0, 3); // Max 3 cards for 1 perfect row!
      try {
        localStorage.setItem("recent_learning_modules_v3", JSON.stringify(updated));
      } catch (e) {
        console.error("LocalStorage write error:", e);
      }
      return updated;
    });
  };

  const closeModal = () => {
    setSelectedCourse(null);
  };

  // Filtered courses by active level and search query
  const filteredCourses = useMemo(() => {
    return learningData.filter((c) => {
      const matchesLevel = activeFilter === "All" || c.level === activeFilter;
      const matchesSearch =
        !searchQuery ||
        c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesLevel && matchesSearch;
    });
  }, [activeFilter, searchQuery]);

  return (
    <div className="goal-dash card-appear et-page lh-page">
      {/* ------------------- PAGE HEADER ------------------- */}
      <div className="goal-hero__head" style={{ marginBottom: "8px" }}>
        <div className="goal-hero__identity">
          <div className="goal-hero__icon-badge">
            <GraduationCap size={22} className="goal-hero__icon" />
          </div>
          <div>
            <div className="goal-hero__title-row">
              <h1 className="goal-hero__name">Learning Hub</h1>
            </div>
            <p className="goal-hero__note">
              Master global economics, market strategies, and personal finance through high-density video modules
            </p>
          </div>
        </div>

        {/* Action Controls: Search & Level Filters */}
        <div className="goal-hero__actions" style={{ flexWrap: "wrap", gap: "10px" }}>
          {/* Search Bar */}
          <div className="drawer-panel__input-wrapper" style={{ width: "210px", height: "36px" }}>
            <Search size={14} className="drawer-panel__icon" />
            <input
              type="text"
              className="drawer-panel__input"
              style={{ fontSize: "12px", height: "36px" }}
              placeholder="Search modules..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Level Filter Chips */}
          <div style={{ display: "flex", gap: "6px" }}>
            {["All", "Beginner", "Intermediate", "Advanced"].map((filter) => (
              <button
                key={filter}
                type="button"
                className={`filter-chip ${activeFilter === filter ? "is-active" : ""}`}
                style={{ padding: "6px 12px", fontSize: "12px", height: "36px" }}
                onClick={() => setActiveFilter(filter)}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ------------------- SECTION 1: ACTIVE MODULES (Exact 3-Card Single Row Bar) ------------------- */}
      <div className="goal-panel">
        <div className="goal-panel__head">
          <div className="goal-panel__head-left">
            <History size={16} className="goal-panel__head-icon" />
            <h3 className="goal-panel__title">Active Modules</h3>
            <span className="history-count-badge">{activeModules.length} Modules</span>
          </div>
        </div>

        {activeModules.length > 0 ? (
          <div className="lh-active-list">
            {activeModules.map((course) => (
              <ActiveModuleCard key={`active-${course.id}`} course={course} openCourse={openCourse} />
            ))}
          </div>
        ) : (
          <div className="history-empty" style={{ padding: "16px", textAlign: "center" }}>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--text-2, #aeb6c7)" }}>
              No active modules yet. Click any video course below to launch your learning session!
            </p>
          </div>
        )}
      </div>

      {/* ------------------- SECTION 2: EXPLORE LEARNING (4x4 Matrix Grid) ------------------- */}
      <div className="goal-panel">
        <div className="goal-panel__head">
          <div className="goal-panel__head-left">
            <BookOpen size={16} className="goal-panel__head-icon" />
            <h3 className="goal-panel__title">Explore Learning</h3>
            <span className="history-count-badge">{filteredCourses.length} Courses</span>
          </div>
        </div>

        {filteredCourses.length > 0 ? (
          <div className="lh-grid">
            {filteredCourses.map((course) => (
              <LearningCard key={course.id} course={course} openCourse={openCourse} />
            ))}
          </div>
        ) : (
          <div className="history-empty" style={{ padding: "28px", textAlign: "center" }}>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--text-2, #aeb6c7)" }}>
              No learning modules found matching "{searchQuery}".
            </p>
          </div>
        )}
      </div>

      {/* ------------------- PORTALED VIDEO MODAL ------------------- */}
      <LearningModal course={selectedCourse} onClose={closeModal} />
    </div>
  );
}