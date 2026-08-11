import React, { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { v4 as uuidv4 } from "uuid";

export const GoalsContext = createContext(null);

const STORAGE_KEY = "gp_goals_v2_redesign";

export const ASSET_TYPES = [
  "Gold",
  "Silver",
  "Crypto",
  "Stocks",
  "Bonds",
  "Mutual Funds",
  "Others",
];

export const ASSET_COLORS = {
  Gold: "#f5a524",
  Silver: "#94a3b8",
  Crypto: "#a855f7",
  Stocks: "#38bdf8",
  Bonds: "#2ec27e",
  "Mutual Funds": "#ec4899",
  Others: "#64748b",
};

export function formatINR(val) {
  if (val === null || val === undefined || isNaN(val)) return "₹0";
  const num = Math.round(Number(val));
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(num);
}

export function getTodayString() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatDateDisplay(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function calculateDaysLeft(endDateStr) {
  if (!endDateStr) return 0;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const end = new Date(endDateStr);
  end.setHours(0, 0, 0, 0);
  const diffTime = end.getTime() - today.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays > 0 ? diffDays : 0;
}

export function getAssetAllocation(goal) {
  if (!goal) return [];
  const history = goal.history || [];
  const totals = {};
  ASSET_TYPES.forEach((type) => {
    totals[type] = 0;
  });

  let totalSaved = 0;
  history.forEach((item) => {
    const amt = Number(item.amount) || 0;
    const type = ASSET_TYPES.includes(item.assetType) ? item.assetType : "Others";
    totals[type] += amt;
    totalSaved += amt;
  });

  if (totalSaved === 0) {
    // Return zero allocations
    return ASSET_TYPES.map((name) => ({
      name,
      amount: 0,
      percentage: 0,
      color: ASSET_COLORS[name] || "#64748b",
    }));
  }

  let rawSegments = ASSET_TYPES.map((name) => {
    const amt = totals[name] || 0;
    const pct = (amt / totalSaved) * 100;
    return {
      name,
      amount: amt,
      rawPct: pct,
      percentage: Math.round(pct),
      color: ASSET_COLORS[name] || "#64748b",
    };
  });

  // Adjust rounding so sum is exactly 100 if totalSaved > 0
  const sumPct = rawSegments.reduce((acc, s) => acc + s.percentage, 0);
  if (sumPct !== 100 && sumPct > 0) {
    const diff = 100 - sumPct;
    // Add diff to segment with largest amount
    let maxIdx = 0;
    for (let i = 1; i < rawSegments.length; i++) {
      if (rawSegments[i].amount > rawSegments[maxIdx].amount) {
        maxIdx = i;
      }
    }
    rawSegments[maxIdx].percentage += diff;
  }

  return rawSegments.map(({ rawPct, ...rest }) => rest);
}

export function calculateGoalHealth(goal) {
  if (!goal) return { status: "On Track", badge: "🟢 On Track", color: "#2ec27e", advice: "On track!" };
  const saved = goal.progress || 0;
  const target = goal.target || 10000;
  const actualPct = (saved / target) * 100;

  if (actualPct >= 100) {
    return {
      status: "Completed",
      badge: "🎉 Goal Completed",
      color: "#2ec27e",
      advice: "Congratulations! You have fully achieved this financial goal.",
    };
  }

  const start = goal.startDate ? new Date(goal.startDate).getTime() : goal.createdAt || Date.now();
  const end = goal.endDate ? new Date(goal.endDate).getTime() : Date.now() + 86400000;
  const now = Date.now();

  const totalDuration = Math.max(1, end - start);
  const elapsed = Math.max(0, now - start);
  const timeElapsedPct = Math.min(100, (elapsed / totalDuration) * 100);

  if (actualPct >= timeElapsedPct - 5) {
    return {
      status: "On Track",
      badge: "🟢 On Track",
      color: "#2ec27e",
      advice: "Great job! You are consistently on pace to reach your goal on time.",
    };
  } else if (actualPct >= timeElapsedPct - 20) {
    return {
      status: "Slightly Behind",
      badge: "🟠 Slightly Behind",
      color: "#f5a524",
      advice: "You are slightly behind schedule. Consider making an extra deposit to get back on track.",
    };
  } else {
    return {
      status: "High Risk",
      badge: "🔴 High Risk",
      color: "#ef4b5b",
      advice: "Savings pace is significantly behind schedule to reach your target by the deadline.",
    };
  }
}

export function calculateSavingsForecast(goal) {
  if (!goal) return { daily: 0, weekly: 0, monthly: 0, remaining: 0, daysLeft: 0 };
  const saved = goal.progress || 0;
  const target = goal.target || 10000;
  const remaining = Math.max(0, target - saved);
  const daysLeft = calculateDaysLeft(goal.endDate);
  const days = Math.max(1, daysLeft);

  const daily = Math.ceil(remaining / days);
  const weekly = Math.ceil(remaining / Math.max(1, days / 7));
  const monthly = Math.ceil(remaining / Math.max(1, days / 30));

  return { daily, weekly, monthly, remaining, daysLeft };
}

export function getMilestones(goal) {
  if (!goal) return [];
  const milestones = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
  const saved = goal.progress || 0;
  const target = goal.target || 10000;
  const pct = Math.min(100, Math.round((saved / target) * 100));

  let foundCurrent = false;
  return milestones.map((m) => {
    const isCompleted = pct >= m;
    let isCurrent = false;
    if (!isCompleted && !foundCurrent) {
      isCurrent = true;
      foundCurrent = true;
    }
    return {
      targetPct: m,
      targetAmount: Math.round((m / 100) * target),
      isCompleted,
      isCurrent,
      isFuture: !isCompleted && !isCurrent,
    };
  });
}

export function getMotivationalMessage(goal) {
  if (!goal) return "";
  const saved = goal.progress || 0;
  const target = goal.target || 10000;
  const pct = Math.min(100, Math.round((saved / target) * 100));

  if (pct >= 100) {
    return "🎉 Incredible milestone achieved! You've completed 100% of your financial goal!";
  }

  const milestones = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
  const nextMilestone = milestones.find((m) => m > pct) || 100;
  const amtNeededForNext = Math.ceil((nextMilestone / 100) * target - saved);

  if (pct === 0) {
    return "🚀 Take the first step! Log an investment deposit to kickstart your savings journey.";
  }

  return `🎉 Great consistency! You've completed ${pct}% of your goal. Only ${formatINR(amtNeededForNext)} left to reach ${nextMilestone}%!`;
}

export function GoalsProvider({ children }) {
  const [goals, setGoals] = useState([]);
  const [activeGoalId, setActiveGoalId] = useState(null);

  // Load state on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setGoals(parsed);
          setActiveGoalId(parsed[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to load goals from localStorage", e);
    }
  }, []);

  // Save state to localStorage on updates
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(goals));
    } catch (e) {
      console.error("Failed to save goals to localStorage", e);
    }
  }, [goals]);

  const activeGoal = useMemo(() => {
    return goals.find((g) => g.id === activeGoalId) || goals[0] || null;
  }, [goals, activeGoalId]);

  // Create Goal
  const createGoal = useCallback((payload) => {
    const id = uuidv4();
    const targetAmt = Number(payload.target) || 10000;
    const newGoal = {
      id,
      name: payload.name.trim(),
      note: payload.note ? payload.note.trim() : "",
      target: targetAmt,
      startDate: payload.startDate || getTodayString(),
      endDate: payload.endDate || getTodayString(),
      progress: 0,
      history: [],
      createdAt: Date.now(),
    };

    setGoals((prev) => [newGoal, ...prev]);
    setActiveGoalId(id);
    return newGoal;
  }, []);

  // Update Goal Details (Name, Note, Target [only increase!], EndDate)
  const updateGoal = useCallback((id, fields) => {
    setGoals((prev) =>
      prev.map((g) => {
        if (g.id !== id) return g;

        const newTarget = fields.target !== undefined ? Number(fields.target) : g.target;
        // Never allow decreasing target amount
        const finalTarget = Math.max(newTarget, g.target);

        return {
          ...g,
          name: fields.name !== undefined ? fields.name.trim() : g.name,
          note: fields.note !== undefined ? fields.note.trim() : g.note,
          target: finalTarget,
          endDate: fields.endDate || g.endDate,
        };
      })
    );
  }, []);

  // Update Progress (Add investment amount)
  const addProgress = useCallback((id, { amount, assetType, date }) => {
    const addedAmt = Number(amount) || 0;
    if (addedAmt <= 0) return;

    setGoals((prev) =>
      prev.map((g) => {
        if (g.id !== id) return g;

        const newProgress = (g.progress || 0) + addedAmt;
        const newRunningTotal = newProgress;
        const progressPercent = Math.round((newRunningTotal / g.target) * 100);

        const newEntry = {
          id: uuidv4(),
          date: date || getTodayString(),
          amount: addedAmt,
          assetType: assetType || "Gold",
          runningTotal: newRunningTotal,
          progressPercent: progressPercent,
          timestamp: Date.now(),
        };

        const updatedHistory = [newEntry, ...(g.history || [])];

        return {
          ...g,
          progress: newProgress,
          history: updatedHistory,
        };
      })
    );
  }, []);

  // Delete Goal
  const deleteGoal = useCallback((id) => {
    setGoals((prev) => {
      const filtered = prev.filter((g) => g.id !== id);
      return filtered;
    });
    setActiveGoalId((curr) => (curr === id ? null : curr));
  }, []);

  return (
    <GoalsContext.Provider
      value={{
        goals,
        activeGoal,
        setActiveGoalId,
        createGoal,
        updateGoal,
        addProgress,
        deleteGoal,
      }}
    >
      {children}
    </GoalsContext.Provider>
  );
}
