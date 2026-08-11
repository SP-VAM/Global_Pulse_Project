import React, { useState, useMemo } from "react";
import {
  Edit3,
  PlusCircle,
  Wallet,
  Clock,
  Target,
  ArrowUpRight,
  History,
  TrendingUp,
  Sparkles,
  CheckCircle2,
  Calendar,
  Zap,
  Award,
  Filter,
  Trash2,
  MoreVertical,
  CircleDot,
  PieChart,
  ShieldCheck,
  Check,
} from "lucide-react";
import {
  formatINR,
  formatDateDisplay,
  calculateDaysLeft,
  getAssetAllocation,
  calculateGoalHealth,
  calculateSavingsForecast,
  getMilestones,
  getMotivationalMessage,
  ASSET_COLORS,
  ASSET_TYPES,
} from "../../goalsContext.jsx";
import "./GoalDashboard.css";

function getArcPath(cx, cy, rOuter, rInner, startAngleDeg, endAngleDeg) {
  const angleDiff = endAngleDeg - startAngleDeg;
  if (angleDiff <= 0) return "";
  
  const gap = angleDiff > 6 ? 1.5 : 0;
  const sDeg = startAngleDeg + gap;
  const eDeg = endAngleDeg - gap;

  if (eDeg <= sDeg) return "";

  const startRad = ((sDeg - 90) * Math.PI) / 180;
  const endRad = ((eDeg - 90) * Math.PI) / 180;

  const x1 = cx + rOuter * Math.cos(startRad);
  const y1 = cy + rOuter * Math.sin(startRad);
  const x2 = cx + rOuter * Math.cos(endRad);
  const y2 = cy + rOuter * Math.sin(endRad);

  const x3 = cx + rInner * Math.cos(endRad);
  const y3 = cy + rInner * Math.sin(endRad);
  const x4 = cx + rInner * Math.cos(startRad);
  const y4 = cy + rInner * Math.sin(startRad);

  const largeArc = eDeg - sDeg > 180 ? 1 : 0;

  return `M ${x1} ${y1} A ${rOuter} ${rOuter} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${rInner} ${rInner} 0 ${largeArc} 0 ${x4} ${y4} Z`;
}

export default function GoalDashboard({
  goal,
  onOpenUpdateGoal,
  onOpenUpdateProgress,
  onDeleteGoal,
}) {
  const [hoveredSegment, setHoveredSegment] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [activeAssetFilter, setActiveAssetFilter] = useState("ALL");
  const [sortOrder, setSortOrder] = useState("newest");
  const [showMenu, setShowMenu] = useState(false);

  if (!goal) return null;

  const saved = goal.progress || 0;
  const target = goal.target || 10000;
  const remaining = Math.max(0, target - saved);
  const progressPercent = Math.min(100, Math.round((saved / target) * 100));
  const daysLeft = calculateDaysLeft(goal.endDate);
  const isCompleted = progressPercent >= 100;

  const allocations = getAssetAllocation(goal);
  const health = calculateGoalHealth(goal);
  const forecast = calculateSavingsForecast(goal);
  const milestones = getMilestones(goal);
  const motivationalMessage = getMotivationalMessage(goal);

  // Outer segmented donut ring angles
  let currentAngle = 0;
  const segmentsWithAngles = allocations.map((alloc) => {
    const angleSize = (alloc.percentage / 100) * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + angleSize;
    currentAngle = endAngle;

    return {
      ...alloc,
      startAngle,
      endAngle,
    };
  });

  const handleMouseMove = (e) => {
    const bounds = e.currentTarget.getBoundingClientRect();
    setTooltipPos({
      x: e.clientX - bounds.left,
      y: e.clientY - bounds.top,
    });
  };

  // Filtered & Sorted History Entries
  const filteredHistory = useMemo(() => {
    let list = goal.history || [];
    if (activeAssetFilter !== "ALL") {
      list = list.filter((item) => item.assetType === activeAssetFilter);
    }

    return [...list].sort((a, b) => {
      const timeA = new Date(a.date).getTime() || a.timestamp || 0;
      const timeB = new Date(b.date).getTime() || b.timestamp || 0;
      return sortOrder === "newest" ? timeB - timeA : timeA - timeB;
    });
  }, [goal.history, activeAssetFilter, sortOrder]);

  return (
    <div className="goal-dash card-appear">
      {/* ------------------- SECTION 1: HERO SUMMARY ------------------- */}
      <div className="goal-hero">
        <div className="goal-hero__head">
          <div className="goal-hero__identity">
            <div className="goal-hero__icon-badge">
              <Target size={22} className="goal-hero__icon" />
            </div>
            <div>
              <div className="goal-hero__title-row">
                <h1 className="goal-hero__name">{goal.name}</h1>
              </div>
              <p className="goal-hero__note">
                {goal.note || "Target date: " + formatDateDisplay(goal.endDate)} • {daysLeft} Days Left
              </p>
            </div>
          </div>

          {/* Action CTAs */}
          <div className="goal-hero__actions">
            {!isCompleted ? (
              <button
                type="button"
                className="goal-hero__btn-primary"
                onClick={onOpenUpdateProgress}
                aria-label="Update Progress"
              >
                <PlusCircle size={16} />
                <span>Update Progress</span>
              </button>
            ) : (
              <button
                type="button"
                className="goal-hero__btn-completed"
                onClick={onOpenUpdateGoal}
              >
                <Award size={16} />
                <span>Goal Completed</span>
              </button>
            )}

            <button
              type="button"
              className="goal-hero__btn-secondary"
              onClick={onOpenUpdateGoal}
              aria-label="Edit Goal"
            >
              <Edit3 size={15} />
              <span>Edit Goal</span>
            </button>
          </div>
        </div>

        {/* Large Visual Horizontal Progress Bar */}
        <div className="goal-hero__progress-block">
          <div className="goal-hero__progress-info">
            <span className="goal-hero__pct">{progressPercent}% Completed</span>
            <span className="goal-hero__amounts">
              <strong className="gp-pos">{formatINR(saved)}</strong> saved of{" "}
              <strong>{formatINR(target)}</strong>
            </span>
          </div>
          <div className="goal-hero__track">
            <div
              className="goal-hero__bar"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="goal-hero__progress-sub">
            <span>Remaining: <strong style={{ color: "#f5a524" }}>{formatINR(remaining)}</strong></span>
            <span>Target Date: <strong>{formatDateDisplay(goal.endDate)}</strong></span>
          </div>
        </div>
      </div>

      {/* ------------------- SECTION 2: 6 KPI CARDS ------------------- */}
      <div className="goal-kpi-grid">
        {/* KPI 1: Current Saved */}
        <div className="kpi-card kpi-card--green">
          <div className="kpi-card__icon">
            <Wallet size={16} />
          </div>
          <span className="kpi-card__label">Current Saved</span>
          <div className="kpi-card__val">{formatINR(saved)}</div>
          <span className="kpi-card__sub gp-pos">
            <TrendingUp size={12} />
            <span>{progressPercent}% of target</span>
          </span>
        </div>

        {/* KPI 2: Remaining */}
        <div className="kpi-card kpi-card--amber">
          <div className="kpi-card__icon">
            <Target size={16} />
          </div>
          <span className="kpi-card__label">Remaining Amount</span>
          <div className="kpi-card__val">{formatINR(remaining)}</div>
          <span className="kpi-card__sub" style={{ color: "#f5a524" }}>
            <span>To reach goal</span>
          </span>
        </div>

        {/* KPI 3: Target Amount */}
        <div className="kpi-card">
          <div className="kpi-card__icon">
            <ArrowUpRight size={16} />
          </div>
          <span className="kpi-card__label">Target Amount</span>
          <div className="kpi-card__val">{formatINR(target)}</div>
          <span className="kpi-card__sub" style={{ color: "#38bdf8" }}>
            <span>Total Goal</span>
          </span>
        </div>

        {/* KPI 4: Progress % */}
        <div className="kpi-card">
          <div className="kpi-card__icon">
            <Zap size={16} />
          </div>
          <span className="kpi-card__label">Progress</span>
          <div className="kpi-card__val">{progressPercent}%</div>
          <span className="kpi-card__sub" style={{ color: "#38bdf8" }}>
            <span>Completion Rate</span>
          </span>
        </div>

        {/* KPI 5: Days Left */}
        <div className="kpi-card">
          <div className="kpi-card__icon">
            <Clock size={16} />
          </div>
          <span className="kpi-card__label">Days Left</span>
          <div className="kpi-card__val">{daysLeft > 0 ? `${daysLeft} Days` : "Goal Ended"}</div>
          <span className="kpi-card__sub" style={{ color: "#aeb6c7" }}>
            <span>{formatDateDisplay(goal.endDate)}</span>
          </span>
        </div>
      </div>

      {/* ------------------- SECTION 3: MILESTONES ------------------- */}
      <div className="goal-mid-grid">
        {/* Milestone Tracker Cards */}
        <div className="goal-panel">
          <div className="goal-panel__head">
            <Award size={16} className="goal-panel__head-icon" />
            <h3 className="goal-panel__title">Milestone Badges</h3>
          </div>
          <div className="milestones-row">
            {milestones.map((m) => (
              <div
                key={m.targetPct}
                className={`milestone-badge ${m.isCompleted ? "is-completed" : ""} ${
                  m.isCurrent ? "is-current" : ""
                }`}
              >
                <div className="milestone-badge__icon">
                  {m.isCompleted ? (
                    <CheckCircle2 size={16} />
                  ) : (
                    <span>{m.targetPct}%</span>
                  )}
                </div>
                <span className="milestone-badge__pct">{m.targetPct}% Goal</span>
                <span className="milestone-badge__amt">{formatINR(m.targetAmount)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ------------------- SECTION 4: MAIN 2-COLUMN LAYOUT ------------------- */}
      <div className="goal-main-grid">
        {/* LEFT COLUMN: Portfolio Allocation & Full Legend */}
        <div className="goal-panel goal-panel--left">
          <div className="goal-panel__head">
            <PieChart size={16} className="goal-panel__head-icon" />
            <h3 className="goal-panel__title">Asset Allocation</h3>
          </div>

          {/* Supporting Compact Donut Graph */}
          <div
            className="goal-dash__vis-container"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoveredSegment(null)}
          >
            <svg
              className="goal-dash__svg"
              viewBox="0 0 340 340"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Donut background */}
              <circle
                cx="170"
                cy="170"
                r="140"
                fill="none"
                stroke="rgba(255,255,255,0.05)"
                strokeWidth="24"
              />

              {/* Segmented asset allocation ring */}
              {saved > 0 ? (
                segmentsWithAngles.map((seg) => {
                  if (seg.percentage <= 0) return null;
                  const pathD = getArcPath(170, 170, 154, 126, seg.startAngle, seg.endAngle);
                  if (!pathD) return null;
                  const isHovered = hoveredSegment?.name === seg.name;

                  return (
                    <path
                      key={seg.name}
                      d={pathD}
                      fill={seg.color}
                      className={`goal-dash__segment ${isHovered ? "is-hovered" : ""}`}
                      onMouseEnter={() => setHoveredSegment(seg)}
                    />
                  );
                })
              ) : (
                <circle
                  cx="170"
                  cy="170"
                  r="140"
                  fill="none"
                  stroke="rgba(56, 189, 248, 0.15)"
                  strokeWidth="24"
                  strokeDasharray="6 6"
                />
              )}

              {/* Center Circle Progress Background */}
              <circle
                cx="170"
                cy="170"
                r="105"
                fill="rgba(11, 15, 25, 0.95)"
                stroke={hoveredSegment?.isInner ? "#38bdf8" : "rgba(255, 255, 255, 0.1)"}
                strokeWidth={hoveredSegment?.isInner ? "3" : "2"}
                style={{ cursor: "pointer", transition: "all 200ms ease" }}
                onMouseEnter={() => setHoveredSegment({
                  isInner: true,
                  name: "Goal Progress",
                  saved,
                  target,
                  remaining,
                  percentage: progressPercent,
                  color: "#38bdf8"
                })}
              />

              {/* Inner Inner Accent Progress Ring */}
              <circle
                cx="170"
                cy="170"
                r="105"
                fill="none"
                stroke="url(#progressGradient)"
                strokeWidth={hoveredSegment?.isInner ? "6" : "3"}
                strokeDasharray="660"
                strokeDashoffset={660 - (660 * progressPercent) / 100}
                strokeLinecap="round"
                transform="rotate(-90 170 170)"
                style={{ cursor: "pointer", transition: "all 200ms cubic-bezier(0.22, 1, 0.36, 1)", filter: hoveredSegment?.isInner ? "drop-shadow(0 0 8px rgba(56, 189, 248, 0.6))" : "none" }}
                onMouseEnter={() => setHoveredSegment({
                  isInner: true,
                  name: "Goal Progress",
                  saved,
                  target,
                  remaining,
                  percentage: progressPercent,
                  color: "#38bdf8"
                })}
              />

              <defs>
                <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#38bdf8" />
                  <stop offset="100%" stopColor="#2ec27e" />
                </linearGradient>
              </defs>

              {/* Center Circle Content */}
              <foreignObject
                x="65"
                y="70"
                width="210"
                height="170"
                style={{ cursor: "pointer" }}
                onMouseEnter={() => setHoveredSegment({
                  isInner: true,
                  name: "Goal Progress",
                  saved,
                  target,
                  remaining,
                  percentage: progressPercent,
                  color: "#38bdf8"
                })}
              >
                <div className="goal-dash__center-content">
                  <span className="goal-dash__center-label">Goal Progress</span>
                  <span className="goal-dash__center-pct">{progressPercent}%</span>
                  <div className="goal-dash__center-divider" />
                  <span className="goal-dash__center-sublabel">Saved / Target</span>
                  <span className="goal-dash__center-amounts">
                    <strong>{formatINR(saved)}</strong>
                    <span className="goal-dash__center-of"> of </span>
                    <span className="goal-dash__center-target">{formatINR(target)}</span>
                  </span>
                </div>
              </foreignObject>
            </svg>

            {/* Hover Tooltip */}
            {hoveredSegment && (
              <div
                className="goal-dash__tooltip"
                style={{
                  left: tooltipPos.x > 150 ? `${tooltipPos.x - 155}px` : `${tooltipPos.x + 12}px`,
                  top: `${Math.max(10, Math.min(200, tooltipPos.y - 15))}px`,
                }}
              >
                <div className="goal-dash__tooltip-head">
                  <span
                    className="goal-dash__tooltip-dot"
                    style={{ background: hoveredSegment.color || "#38bdf8" }}
                  />
                  <span className="goal-dash__tooltip-name">{hoveredSegment.name}</span>
                </div>
                {hoveredSegment.isInner ? (
                  <>
                    <div className="goal-dash__tooltip-row">
                      <span>Total Saved:</span>
                      <strong style={{ color: "#2ec27e" }}>{formatINR(hoveredSegment.saved)}</strong>
                    </div>
                    <div className="goal-dash__tooltip-row">
                      <span>Target Goal:</span>
                      <strong>{formatINR(hoveredSegment.target)}</strong>
                    </div>
                    <div className="goal-dash__tooltip-row">
                      <span>Remaining:</span>
                      <strong style={{ color: "#f5a524" }}>{formatINR(hoveredSegment.remaining)}</strong>
                    </div>
                    <div className="goal-dash__tooltip-row">
                      <span>Progress:</span>
                      <strong style={{ color: "#38bdf8" }}>{hoveredSegment.percentage}%</strong>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="goal-dash__tooltip-row">
                      <span>Amount Invested:</span>
                      <strong>{formatINR(hoveredSegment.amount)}</strong>
                    </div>
                    <div className="goal-dash__tooltip-row">
                      <span>Allocation:</span>
                      <strong style={{ color: hoveredSegment.color }}>
                        {hoveredSegment.percentage}%
                      </strong>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Filterable Progress History */}
        <div className="goal-panel goal-panel--right">
          <div className="goal-panel__head">
            <div className="goal-panel__head-left">
              <History size={16} className="goal-panel__head-icon" />
              <h3 className="goal-panel__title">Progress History</h3>
              <span className="history-count-badge">
                {filteredHistory.length} Entries
              </span>
            </div>

            {/* Sort Selector */}
            <div className="history-sort">
              <span className="history-sort__label">Sort:</span>
              <select
                className="history-sort__select"
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
              </select>
            </div>
          </div>

          {/* Category Filter Chips */}
          <div className="history-filters">
            <button
              type="button"
              className={`filter-chip ${activeAssetFilter === "ALL" ? "is-active" : ""}`}
              onClick={() => setActiveAssetFilter("ALL")}
            >
              All
            </button>
            {ASSET_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                className={`filter-chip ${activeAssetFilter === type ? "is-active" : ""}`}
                onClick={() => setActiveAssetFilter(type)}
              >
                <span
                  className="filter-chip__dot"
                  style={{ background: ASSET_COLORS[type] || "#64748b" }}
                />
                <span>{type}</span>
              </button>
            ))}
          </div>

          {/* History Transactions Scroll List */}
          <div className="history-scroll">
            {filteredHistory.length > 0 ? (
              <div className="history-list">
                {filteredHistory.map((item) => (
                  <div key={item.id} className="history-row">
                    <div className="history-row__left">
                      <span className="history-row__date">
                        {formatDateDisplay(item.date)}
                      </span>
                      <span
                        className="asset-pill"
                        style={{
                          borderColor: ASSET_COLORS[item.assetType] || "#64748b",
                          color: ASSET_COLORS[item.assetType] || "#64748b",
                          background: `${ASSET_COLORS[item.assetType] || "#64748b"}18`,
                        }}
                      >
                        {item.assetType}
                      </span>
                    </div>

                    <div className="history-row__right">
                      <span className="history-row__amt gp-pos">
                        +{formatINR(item.amount)}
                      </span>
                      <span className="history-row__meta">
                        Total: {formatINR(item.runningTotal)} ({item.progressPercent}% Completed)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="history-empty">
                <p>No progress updates found for this filter.</p>
                {!isCompleted && (
                  <button
                    type="button"
                    className="history-add-link"
                    onClick={onOpenUpdateProgress}
                  >
                    + Add an investment deposit
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
