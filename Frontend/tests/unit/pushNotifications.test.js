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
// Pure logic extractor for Push Notifications (FRD-048)
// ---------------------------------------------------------------------------

function buildPushPayload(notification, deviceToken) {
  if (!notification || !deviceToken) return null;

  return {
    to: deviceToken,
    notification: {
      title: notification.title || "GlobalPulse Alert",
      body: notification.message || "You have a new update.",
      icon: "/logo192.png",
      click_action: notification.action_url || "/dashboard",
    },
    data: {
      notificationId: String(notification.notification_id || notification.id || ""),
      type: String(notification.notification_type || notification.type || "GENERAL"),
      timestamp: notification.created_at || new Date().toISOString(),
      actionUrl: notification.action_url || "/dashboard",
    },
  };
}

function processIncomingPushMessage(pushPayload, activeNotifications = []) {
  if (!pushPayload) return activeNotifications;

  const newNotif = {
    id: pushPayload.data?.notificationId || Date.now(),
    title: pushPayload.notification?.title || "New Notification",
    message: pushPayload.notification?.body || "",
    notification_type: pushPayload.data?.type || "GENERAL",
    action_url: pushPayload.data?.actionUrl || "/dashboard",
    created_at: pushPayload.data?.timestamp || new Date().toISOString(),
    is_read: false,
  };

  return [newNotif, ...activeNotifications];
}

function validateDeviceTokenPayload(token, deviceType = "WEB") {
  if (!token || typeof token !== "string" || token.trim().length < 10) {
    return { isValid: false, error: "Invalid or empty FCM device token" };
  }
  const validDevices = ["WEB", "ANDROID", "IOS"];
  if (!validDevices.includes(deviceType.toUpperCase())) {
    return { isValid: false, error: "Unsupported device type" };
  }
  return { isValid: true, sanitizedToken: token.trim(), deviceType: deviceType.toUpperCase() };
}

function calculateNotificationBadgeVisibility(unreadCount) {
  const count = Math.max(0, Number(unreadCount) || 0);
  return {
    isVisible: count > 0,
    badgeText: count > 99 ? "99+" : String(count),
    numericCount: count,
  };
}

// ---------------------------------------------------------------------------
// FRD-048 Push Notifications - Unit Test Suite
// ---------------------------------------------------------------------------

describe("FRD-048 Push Notifications - Unit Test Suite", () => {
  beforeEach(() => {
    globalThis.localStorage.clear();
  });

  describe("AC-001 & AC-002: FCM Push Payload Assembly & Delivery Structure", () => {
    test("Constructs standard FCM push payload with notification and data envelopes", () => {
      const notif = {
        id: 101,
        title: "Budget Threshold Warning",
        message: "You have utilized 85% of your Food budget.",
        notification_type: "BUDGET_ALERT",
        action_url: "/dashboard/expense-tracker",
        created_at: "2026-08-21T10:00:00Z",
      };
      const token = "fcm_device_token_xyz987654321";

      const payload = buildPushPayload(notif, token);
      assert.notStrictEqual(payload, null);
      assert.strictEqual(payload.to, token);
      assert.strictEqual(payload.notification.title, "Budget Threshold Warning");
      assert.strictEqual(payload.notification.body, "You have utilized 85% of your Food budget.");
      assert.strictEqual(payload.data.type, "BUDGET_ALERT");
      assert.strictEqual(payload.data.actionUrl, "/dashboard/expense-tracker");
    });

    test("Returns null when device token or notification is missing", () => {
      assert.strictEqual(buildPushPayload(null, "token123"), null);
      assert.strictEqual(buildPushPayload({ title: "Test" }, null), null);
    });
  });

  describe("AC-003 & AC-004: Inbound Push Processing & State Synchronization", () => {
    test("Prepends incoming real-time push message to user notification feed with is_read = false", () => {
      const initial = [
        { id: 1, title: "Initial Notification", is_read: true },
      ];
      const incomingPush = {
        notification: {
          title: "Dividend Credited",
          body: "₹500 credited from TCS.",
        },
        data: {
          notificationId: "202",
          type: "FINANCIAL",
          actionUrl: "/dashboard",
          timestamp: "2026-08-21T10:15:00Z",
        },
      };

      const updated = processIncomingPushMessage(incomingPush, initial);
      assert.strictEqual(updated.length, 2);
      assert.strictEqual(updated[0].id, "202");
      assert.strictEqual(updated[0].title, "Dividend Credited");
      assert.strictEqual(updated[0].is_read, false);
      assert.strictEqual(updated[1].id, 1);
    });
  });

  describe("AC-005 & AC-006: Device Token Validation & Registration", () => {
    test("Validates and sanitizes authentic FCM token with supported device type", () => {
      const result = validateDeviceTokenPayload("  fcm_valid_token_string_123456  ", "web");
      assert.strictEqual(result.isValid, true);
      assert.strictEqual(result.sanitizedToken, "fcm_valid_token_string_123456");
      assert.strictEqual(result.deviceType, "WEB");
    });

    test("Rejects malformed or overly short device tokens", () => {
      const result = validateDeviceTokenPayload("short", "WEB");
      assert.strictEqual(result.isValid, false);
      assert.match(result.error, /Invalid or empty FCM device token/);
    });

    test("Rejects unsupported device types", () => {
      const result = validateDeviceTokenPayload("valid_token_string_123456", "SMART_TV");
      assert.strictEqual(result.isValid, false);
      assert.match(result.error, /Unsupported device type/);
    });
  });

  describe("AC-007 & AC-008: Real-Time Badge Display & 99+ Cap Rules", () => {
    test("Hides badge when unread count is 0", () => {
      const badge = calculateNotificationBadgeVisibility(0);
      assert.strictEqual(badge.isVisible, false);
      assert.strictEqual(badge.numericCount, 0);
    });

    test("Shows badge with exact count for values between 1 and 99", () => {
      const badge = calculateNotificationBadgeVisibility(5);
      assert.strictEqual(badge.isVisible, true);
      assert.strictEqual(badge.badgeText, "5");
      assert.strictEqual(badge.numericCount, 5);
    });

    test("Caps badge text at '99+' when unread count exceeds 99", () => {
      const badge = calculateNotificationBadgeVisibility(150);
      assert.strictEqual(badge.isVisible, true);
      assert.strictEqual(badge.badgeText, "99+");
      assert.strictEqual(badge.numericCount, 150);
    });
  });
});
