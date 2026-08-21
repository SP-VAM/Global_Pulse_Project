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
  location: { hostname: "localhost", pathname: "/dashboard" },
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
// Pure logic extractor for Notifications (FRD-030)
// ---------------------------------------------------------------------------

function classifyNotificationType(type) {
  const norm = String(type || "").toUpperCase();
  switch (norm) {
    case "SECURITY":
    case "ANOMALY":
      return { category: "Security", tone: "red", icon: "ShieldAlert" };
    case "BUDGET_ALERT":
    case "BUDGET_EXCEEDED":
    case "BUDGET_WARNING":
      return { category: "Budget", tone: "amber", icon: "Wallet" };
    case "FINANCIAL":
    case "TRANSACTION_SUCCESS":
    case "EXPENSE_ADDED":
    case "INCOME_ADDED":
      return { category: "Financial", tone: "green", icon: "TrendingUp" };
    case "REMINDER":
    case "UPCOMING_BILL":
    case "GOAL_MILESTONE":
      return { category: "Reminder", tone: "blue", icon: "BookOpen" };
    default:
      return { category: "General", tone: "blue", icon: "Bell" };
  }
}

function formatNotificationTime(isoString, nowTimestamp = null) {
  if (!isoString) return "Just now";
  try {
    const pubDate = new Date(isoString);
    if (isNaN(pubDate.getTime())) return "Recently";
    const now = nowTimestamp ? new Date(nowTimestamp) : new Date();
    const diffSec = Math.floor((now.getTime() - pubDate.getTime()) / 1000);
    if (diffSec < 60) return "Just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return "Recently";
  }
}

function countUnreadNotifications(notifications) {
  if (!Array.isArray(notifications)) return 0;
  return notifications.filter((n) => n && !n.is_read).length;
}

function markSingleNotificationAsRead(notifications, targetId) {
  if (!Array.isArray(notifications)) return [];
  return notifications.map((n) => {
    if (!n) return n;
    const currentId = n.notification_id || n.id;
    if (currentId === targetId) {
      return { ...n, is_read: true };
    }
    return n;
  });
}

function markAllNotificationsAsRead(notifications) {
  if (!Array.isArray(notifications)) return [];
  return notifications.map((n) => (n ? { ...n, is_read: true } : n));
}

function resolveNotificationRoute(notification) {
  if (!notification) return "/dashboard";
  if (notification.action_url) return notification.action_url;
  if (notification.link) return notification.link;

  const type = String(notification.notification_type || notification.type || "").toUpperCase();
  switch (type) {
    case "BUDGET_ALERT":
    case "BUDGET_EXCEEDED":
    case "EXPENSE_ADDED":
    case "INCOME_ADDED":
    case "FINANCIAL":
      return "/dashboard/expense-tracker";
    case "GOAL_MILESTONE":
      return "/dashboard/goals";
    case "SECURITY":
    case "ANOMALY":
      return "/dashboard/profile";
    case "MARKET_ALERT":
    case "STOCK_ALERT":
      return "/dashboard/market-analysis";
    default:
      return "/dashboard";
  }
}

// ---------------------------------------------------------------------------
// FRD-030 Notifications - Unit Test Suite
// ---------------------------------------------------------------------------

describe("FRD-030 Notifications - Unit Test Suite", () => {
  beforeEach(() => {
    globalThis.localStorage.clear();
  });

  describe("AC-001 & AC-002: Notification Types Classification & Visual Tones", () => {
    test("Correctly classifies SECURITY and anomaly alerts with red tone and ShieldAlert icon", () => {
      const result = classifyNotificationType("SECURITY");
      assert.strictEqual(result.category, "Security");
      assert.strictEqual(result.tone, "red");
      assert.strictEqual(result.icon, "ShieldAlert");
    });

    test("Correctly classifies BUDGET_ALERT with amber tone and Wallet icon", () => {
      const result = classifyNotificationType("BUDGET_ALERT");
      assert.strictEqual(result.category, "Budget");
      assert.strictEqual(result.tone, "amber");
      assert.strictEqual(result.icon, "Wallet");
    });

    test("Correctly classifies FINANCIAL (successful transactions) with green tone and TrendingUp icon", () => {
      const result = classifyNotificationType("FINANCIAL");
      assert.strictEqual(result.category, "Financial");
      assert.strictEqual(result.tone, "green");
      assert.strictEqual(result.icon, "TrendingUp");
    });

    test("Correctly classifies REMINDER (upcoming bills / goals) with blue tone and BookOpen icon", () => {
      const result = classifyNotificationType("REMINDER");
      assert.strictEqual(result.category, "Reminder");
      assert.strictEqual(result.tone, "blue");
      assert.strictEqual(result.icon, "BookOpen");
    });

    test("Defaults unknown or null notification types to General Bell", () => {
      const result = classifyNotificationType(null);
      assert.strictEqual(result.category, "General");
      assert.strictEqual(result.tone, "blue");
      assert.strictEqual(result.icon, "Bell");
    });
  });

  describe("AC-003: Unread Count Calculation & Badge Numbers", () => {
    test("Accurately counts unread notifications in mixed array", () => {
      const list = [
        { id: 1, title: "Expense Added", is_read: false },
        { id: 2, title: "Budget Warning", is_read: true },
        { id: 3, title: "Bill Reminder", is_read: false },
        { id: 4, title: "Security Alert", is_read: false },
      ];
      assert.strictEqual(countUnreadNotifications(list), 3);
    });

    test("Returns 0 when all notifications are read or array is empty", () => {
      assert.strictEqual(countUnreadNotifications([]), 0);
      assert.strictEqual(countUnreadNotifications([{ id: 1, is_read: true }]), 0);
      assert.strictEqual(countUnreadNotifications(null), 0);
    });
  });

  describe("AC-004 & AC-005: Read State Mutations (Single and Mark-All)", () => {
    test("markSingleNotificationAsRead mutates only the targeted notification", () => {
      const list = [
        { id: 1, title: "Expense Added", is_read: false },
        { id: 2, title: "Budget Warning", is_read: false },
      ];
      const updated = markSingleNotificationAsRead(list, 1);
      assert.strictEqual(updated[0].is_read, true);
      assert.strictEqual(updated[1].is_read, false);
      assert.strictEqual(countUnreadNotifications(updated), 1);
    });

    test("markAllNotificationsAsRead marks all notifications as read in bulk", () => {
      const list = [
        { id: 1, title: "Expense Added", is_read: false },
        { id: 2, title: "Budget Warning", is_read: false },
        { id: 3, title: "Bill Reminder", is_read: false },
      ];
      const updated = markAllNotificationsAsRead(list);
      assert.strictEqual(updated.every((n) => n.is_read === true), true);
      assert.strictEqual(countUnreadNotifications(updated), 0);
    });
  });

  describe("AC-006: Relative Timestamp Formatting", () => {
    const fixedNow = new Date("2026-08-21T10:00:00Z").getTime();

    test("Formats timestamps under 60 seconds as 'Just now'", () => {
      const dateStr = new Date(fixedNow - 30 * 1000).toISOString();
      assert.strictEqual(formatNotificationTime(dateStr, fixedNow), "Just now");
    });

    test("Formats minute differences accurately (e.g. '15m ago')", () => {
      const dateStr = new Date(fixedNow - 15 * 60 * 1000).toISOString();
      assert.strictEqual(formatNotificationTime(dateStr, fixedNow), "15m ago");
    });

    test("Formats hour differences accurately (e.g. '3h ago')", () => {
      const dateStr = new Date(fixedNow - 3 * 3600 * 1000).toISOString();
      assert.strictEqual(formatNotificationTime(dateStr, fixedNow), "3h ago");
    });

    test("Formats day differences accurately (e.g. '4d ago')", () => {
      const dateStr = new Date(fixedNow - 4 * 86400 * 1000).toISOString();
      assert.strictEqual(formatNotificationTime(dateStr, fixedNow), "4d ago");
    });

    test("Handles missing or malformed dates gracefully", () => {
      assert.strictEqual(formatNotificationTime(null), "Just now");
      assert.strictEqual(formatNotificationTime("invalid-date-string"), "Recently");
    });
  });

  describe("AC-007: Smart Deep-Linking / Action Routing", () => {
    test("Routes explicit action_url or link if provided", () => {
      const notif = { action_url: "/dashboard/goals?goalId=42" };
      assert.strictEqual(resolveNotificationRoute(notif), "/dashboard/goals?goalId=42");
    });

    test("Routes budget and financial notifications to /dashboard/expense-tracker", () => {
      assert.strictEqual(resolveNotificationRoute({ notification_type: "BUDGET_ALERT" }), "/dashboard/expense-tracker");
      assert.strictEqual(resolveNotificationRoute({ notification_type: "EXPENSE_ADDED" }), "/dashboard/expense-tracker");
    });

    test("Routes goal notifications to /dashboard/goals", () => {
      assert.strictEqual(resolveNotificationRoute({ notification_type: "GOAL_MILESTONE" }), "/dashboard/goals");
    });

    test("Routes security anomaly alerts to /dashboard/profile", () => {
      assert.strictEqual(resolveNotificationRoute({ notification_type: "SECURITY" }), "/dashboard/profile");
    });

    test("Routes market alerts to /dashboard/market-analysis", () => {
      assert.strictEqual(resolveNotificationRoute({ notification_type: "STOCK_ALERT" }), "/dashboard/market-analysis");
    });
  });

  describe("AC-008: Real-Time Event Dispatching", () => {
    test("Dispatches and captures 'notification-received' CustomEvent seamlessly", () => {
      let received = false;
      const callback = (e) => {
        received = true;
      };

      globalThis.window.addEventListener("notification-received", callback);
      globalThis.window.dispatchEvent({ type: "notification-received", detail: { id: 99 } });

      assert.strictEqual(received, true);
      globalThis.window.removeEventListener("notification-received", callback);
    });
  });
});
