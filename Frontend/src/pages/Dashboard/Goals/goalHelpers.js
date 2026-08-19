/**
 * Financial Goals pure calculation and formatting helpers.
 */

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
  if (val === null || val === undefined || isNaN(val) || !isFinite(val)) return "₹0";
  const num = Number(val);
  if (num <= 0) return "₹0";
  if (num > 9999999999999) return "₹99,99,999 Cr+";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Math.round(num));
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
    return ASSET_TYPES.map((name) => ({
      name,
      amount: 0,
      percentage: 0,
      color: ASSET_COLORS[name] || "#64748b",
    }));
  }

  return ASSET_TYPES.map((name) => {
    const amt = totals[name] || 0;
    const pct = Math.round((amt / totalSaved) * 100);
    return {
      name,
      amount: amt,
      percentage: pct,
      color: ASSET_COLORS[name] || "#64748b",
    };
  });
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
