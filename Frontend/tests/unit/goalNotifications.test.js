import { test, describe, beforeEach } from "node:test";
import assert from "node:assert/strict";

// Mock localStorage and window environment for Node environment
globalThis.localStorage = {
  _store: {},
  getItem(key) {
    return this._store[key] || null;
  },
  setItem(key, val) {
    this._store[key] = String(val);
  },
  removeItem(key) {
    delete this._store[key];
  },
  clear() {
    this._store = {};
  },
};

globalThis.window = {
  location: { hostname: "localhost", pathname: "/dashboard/goals" },
  _listeners: {},
  addEventListener(event, callback) {
    this._listeners[event] = this._listeners[event] || [];
    this._listeners[event].push(callback);
  },
  removeEventListener(event, callback) {
    if (!this._listeners[event]) return;
    this._listeners[event] = this._listeners[event].filter((cb) => cb !== callback);
  },
  dispatchEvent(event) {
    const type = event.type || event;
    const handlers = this._listeners[type] || [];
    for (const handler of handlers) {
      handler(event);
    }
    return true;
  },
};

// ---------------------------------------------------------------------------
// Pure logic extractor for Goal Notifications & Reminders (FRD-041)
// ---------------------------------------------------------------------------

const MILESTONE_THRESHOLDS = [25, 50, 75];

function computeMilestoneTransition(previousProgress, newProgress, target) {
  if (!target || target <= 0) return null;

  const prevPct = Math.min(100, Math.floor((previousProgress / target) * 100));
  const newPct = Math.min(100, Math.floor((newProgress / target) * 100));

  if (newPct >= 100 && prevPct < 100) {
    return {
      type: "GOAL_COMPLETED",
      milestone: 100,
      title: "Goal Achieved! 🎉",
      message: `Congratulations! You have reached 100% of your goal.`,
    };
  }

  for (const threshold of MILESTONE_THRESHOLDS) {
    if (prevPct < threshold && newPct >= threshold) {
      return {
        type: "GOAL_MILESTONE",
        milestone: threshold,
        title: `${threshold}% Milestone Reached! 🚀`,
        message: `Great progress! You've achieved ${threshold}% of your goal.`,
      };
    }
  }

  return null;
}

function evaluateGoalDeadlineAlert(goal, currentDate = new Date()) {
  if (!goal || !goal.end_date) return null;

  const targetDate = new Date(goal.end_date);
  const diffTime = targetDate.getTime() - currentDate.getTime();
  const daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  const progress = Number(goal.current_quantity || goal.current || 0);
  const target = Number(goal.target_quantity || goal.target || 0);
  const isCompleted = target > 0 && progress >= target;

  if (isCompleted) return null;

  // Past deadline missed target
  if (daysLeft < 0) {
    return {
      type: "GOAL_MISSED_DEADLINE",
      daysLeft,
      urgency: "HIGH",
      title: "Goal Deadline Passed",
      message: `The deadline for "${goal.goal_name || goal.name}" has passed. Review your target or extend the deadline.`,
      actionUrl: `/dashboard/goals?goalId=${goal.goal_id || goal.id}`,
    };
  }

  // 1-day urgent reminder
  if (daysLeft === 1) {
    return {
      type: "GOAL_DEADLINE_1DAY",
      daysLeft: 1,
      urgency: "CRITICAL",
      title: "Goal Due Tomorrow! ⏰",
      message: `Your goal "${goal.goal_name || goal.name}" is due tomorrow! Make a final contribution to reach your target.`,
      actionUrl: `/dashboard/goals?goalId=${goal.goal_id || goal.id}`,
    };
  }

  // 3-day reminder
  if (daysLeft <= 3 && daysLeft > 1) {
    return {
      type: "GOAL_DEADLINE_3DAY",
      daysLeft,
      urgency: "HIGH",
      title: "Goal Deadline Approaching (3 Days Left)",
      message: `Only ${daysLeft} days remaining for "${goal.goal_name || goal.name}". Stay on track to reach your objective.`,
      actionUrl: `/dashboard/goals?goalId=${goal.goal_id || goal.id}`,
    };
  }

  // 7-day reminder
  if (daysLeft <= 7 && daysLeft > 3) {
    return {
      type: "GOAL_DEADLINE_7DAY",
      daysLeft,
      urgency: "MEDIUM",
      title: "1 Week Remaining for Your Goal",
      message: `You have 1 week left to achieve "${goal.goal_name || goal.name}".`,
      actionUrl: `/dashboard/goals?goalId=${goal.goal_id || goal.id}`,
    };
  }

  return null;
}

function deduplicateNotifications(existingNotifications, newNotification) {
  if (!Array.isArray(existingNotifications) || !newNotification) return false;

  return existingNotifications.some((n) => {
    if (!n) return false;
    const sameType = (n.notification_type || n.type) === newNotification.type;
    const sameGoal = (n.goal_id || n.goalId) === newNotification.goalId;
    const sameMilestone = (n.milestone || null) === (newNotification.milestone || null);
    return sameType && sameGoal && sameMilestone;
  });
}

function buildGoalNotificationPayload(goal, eventType, details = {}) {
  const goalId = goal.goal_id || goal.id || 0;
  const goalName = goal.goal_name || goal.name || "Financial Goal";

  return {
    goalId,
    type: eventType,
    title: details.title || `Goal Update: ${goalName}`,
    message: details.message || `An update is available for your goal: ${goalName}`,
    actionUrl: `/dashboard/goals?goalId=${goalId}`,
    createdAt: new Date().toISOString(),
    isRead: false,
  };
}

// ---------------------------------------------------------------------------
// FRD-041 Goal Notifications & Reminders - Unit Test Suite
// ---------------------------------------------------------------------------

describe("FRD-041 Goal Notifications & Reminders - Unit Test Suite", () => {
  beforeEach(() => {
    globalThis.localStorage.clear();
  });

  describe("AC-001: Milestone Threshold Crossings (25%, 50%, 75%)", () => {
    test("Triggers 25% milestone notification when progress moves from 20% to 30%", () => {
      const result = computeMilestoneTransition(20000, 30000, 100000);
      assert.notStrictEqual(result, null);
      assert.strictEqual(result.type, "GOAL_MILESTONE");
      assert.strictEqual(result.milestone, 25);
      assert.match(result.title, /25% Milestone Reached/);
    });

    test("Triggers 50% milestone notification when progress moves from 40% to 55%", () => {
      const result = computeMilestoneTransition(40000, 55000, 100000);
      assert.notStrictEqual(result, null);
      assert.strictEqual(result.type, "GOAL_MILESTONE");
      assert.strictEqual(result.milestone, 50);
      assert.match(result.title, /50% Milestone Reached/);
    });

    test("Triggers 75% milestone notification when progress moves from 65% to 80%", () => {
      const result = computeMilestoneTransition(65000, 80000, 100000);
      assert.notStrictEqual(result, null);
      assert.strictEqual(result.type, "GOAL_MILESTONE");
      assert.strictEqual(result.milestone, 75);
      assert.match(result.title, /75% Milestone Reached/);
    });

    test("Does NOT trigger notification when progress remains within the same milestone tier", () => {
      // 30% -> 35% (already crossed 25%, has not reached 50%)
      const result = computeMilestoneTransition(30000, 35000, 100000);
      assert.strictEqual(result, null);
    });
  });

  describe("AC-002: Goal Completion Celebration (100%)", () => {
    test("Triggers GOAL_COMPLETED celebration notification when progress reaches 100%", () => {
      const result = computeMilestoneTransition(90000, 100000, 100000);
      assert.notStrictEqual(result, null);
      assert.strictEqual(result.type, "GOAL_COMPLETED");
      assert.strictEqual(result.milestone, 100);
      assert.match(result.title, /Goal Achieved/);
    });

    test("Triggers GOAL_COMPLETED when contribution exceeds 100%", () => {
      const result = computeMilestoneTransition(80000, 120000, 100000);
      assert.notStrictEqual(result, null);
      assert.strictEqual(result.type, "GOAL_COMPLETED");
      assert.strictEqual(result.milestone, 100);
    });

    test("Does NOT trigger completion if goal was already completed prior to addition", () => {
      const result = computeMilestoneTransition(100000, 110000, 100000);
      assert.strictEqual(result, null);
    });
  });

  describe("AC-003: Upcoming Deadline Reminders (7-Day, 3-Day, 1-Day)", () => {
    const fixedNow = new Date("2026-08-21T10:00:00Z");

    test("Generates 1-Day critical reminder when deadline is tomorrow", () => {
      const goal = {
        id: 101,
        name: "Emergency Fund",
        current: 50000,
        target: 100000,
        end_date: "2026-08-22T10:00:00Z",
      };
      const alert = evaluateGoalDeadlineAlert(goal, fixedNow);
      assert.notStrictEqual(alert, null);
      assert.strictEqual(alert.type, "GOAL_DEADLINE_1DAY");
      assert.strictEqual(alert.urgency, "CRITICAL");
      assert.match(alert.title, /Due Tomorrow/);
    });

    test("Generates 3-Day reminder when deadline is 3 days away", () => {
      const goal = {
        id: 102,
        name: "Vacation Savings",
        current: 20000,
        target: 60000,
        end_date: "2026-08-24T10:00:00Z",
      };
      const alert = evaluateGoalDeadlineAlert(goal, fixedNow);
      assert.notStrictEqual(alert, null);
      assert.strictEqual(alert.type, "GOAL_DEADLINE_3DAY");
      assert.strictEqual(alert.urgency, "HIGH");
    });

    test("Generates 7-Day reminder when deadline is 7 days away", () => {
      const goal = {
        id: 103,
        name: "New Laptop",
        current: 40000,
        target: 80000,
        end_date: "2026-08-28T10:00:00Z",
      };
      const alert = evaluateGoalDeadlineAlert(goal, fixedNow);
      assert.notStrictEqual(alert, null);
      assert.strictEqual(alert.type, "GOAL_DEADLINE_7DAY");
      assert.strictEqual(alert.urgency, "MEDIUM");
    });

    test("Does NOT generate deadline alert if goal is already completed", () => {
      const goal = {
        id: 104,
        name: "Completed Goal",
        current: 100000,
        target: 100000,
        end_date: "2026-08-22T10:00:00Z",
      };
      const alert = evaluateGoalDeadlineAlert(goal, fixedNow);
      assert.strictEqual(alert, null);
    });
  });

  describe("AC-004: Missed Target / Expired Goal Notification", () => {
    const fixedNow = new Date("2026-08-21T10:00:00Z");

    test("Detects expired goal and generates GOAL_MISSED_DEADLINE notification", () => {
      const goal = {
        id: 105,
        name: "Q2 Car Fund",
        current: 30000,
        target: 100000,
        end_date: "2026-08-15T10:00:00Z", // In the past
      };
      const alert = evaluateGoalDeadlineAlert(goal, fixedNow);
      assert.notStrictEqual(alert, null);
      assert.strictEqual(alert.type, "GOAL_MISSED_DEADLINE");
      assert.match(alert.message, /deadline for "Q2 Car Fund" has passed/);
    });
  });

  describe("AC-005 & AC-006: Deduplication & Action Routing", () => {
    test("Deduplicates identical milestone notifications to prevent notification spam", () => {
      const existing = [
        { type: "GOAL_MILESTONE", goalId: 10, milestone: 25 },
      ];
      const duplicate = { type: "GOAL_MILESTONE", goalId: 10, milestone: 25 };
      const nonDuplicate = { type: "GOAL_MILESTONE", goalId: 10, milestone: 50 };

      assert.strictEqual(deduplicateNotifications(existing, duplicate), true);
      assert.strictEqual(deduplicateNotifications(existing, nonDuplicate), false);
    });

    test("Constructs actionUrl targeting specific goal drawer (/dashboard/goals?goalId=ID)", () => {
      const payload = buildGoalNotificationPayload(
        { id: 42, name: "Gold Investment" },
        "GOAL_MILESTONE",
        { title: "25% Reached" }
      );
      assert.strictEqual(payload.actionUrl, "/dashboard/goals?goalId=42");
      assert.strictEqual(payload.goalId, 42);
      assert.strictEqual(payload.isRead, false);
    });
  });
});
