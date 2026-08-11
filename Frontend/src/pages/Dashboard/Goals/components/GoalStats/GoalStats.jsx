import React from "react";
import "./GoalStats.css";

function StatCard({ title, value }) {
  return (
    <div className="gs-card">
      <div className="gs-title">{title}</div>
      <div className="gs-value">{value}</div>
    </div>
  );
}

function formatDeadline(endDate) {
  if (!endDate) return "—";

  const today = new Date();
  const target = new Date(endDate);

  const diffTime = target - today;

  const totalDays = Math.max(
    0,
    Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  );

  // Show days until one full year
  if (totalDays < 365) {
    return `${totalDays} Days`;
  }

  const years = Math.floor(totalDays / 365);

  const remainingDays = totalDays % 365;

  const months = Math.floor(remainingDays / 30);

  if (months === 0) {
    return years === 1
      ? "1 Year"
      : `${years} Years`;
  }

  return years === 1
    ? `1 Year ${months} Month${months > 1 ? "s" : ""}`
    : `${years} Years ${months} Month${months > 1 ? "s" : ""}`;
}

export default function GoalStats({ goal }) {
  const total = goal.target;
  const current = goal.progress;
  const remaining = Math.max(0, total - current);

  return (
    <div className="gs-root">
      <StatCard
        title="TOTAL"
        value={`${total} ${goal.unit}`}
      />

      <StatCard
        title="CURRENT"
        value={`${current} ${goal.unit}`}
      />

      <StatCard
        title="REMAINING"
        value={`${remaining} ${goal.unit}`}
      />

      <StatCard
        title="DEADLINE"
        value={formatDeadline(goal.endDate)}
      />
    </div>
  );
}