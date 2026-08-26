/**
 * API client service for FRD-048 Push Notifications.
 * Strictly uses application access_token and relative API path.
 */
import { API_BASE_URL } from "../config/api.js";

function getAuthHeader() {
  const token = localStorage.getItem("access_token") || localStorage.getItem("token")
  if (token && token !== "demo_token" && token !== "null" && token !== "undefined") {
    return { Authorization: `Bearer ${token}` }
  }
  return {}
}

export async function fetchNotifications({ limit = 50, offset = 0, unreadOnly = false } = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const url = `${API_BASE_URL}/api/v1/notifications?limit=${limit}&offset=${offset}&unread_only=${unreadOnly}`
  const res = await fetch(url, { headers })
  if (!res.ok) {
    throw new Error(`Failed to fetch notifications: ${res.statusText}`)
  }
  return res.json()
}

export async function fetchUnreadCount() {
  const authHeader = getAuthHeader()
  if (!authHeader.Authorization) {
    return { count: 0, unread_count: 0 }
  }
  const headers = {
    "Content-Type": "application/json",
    ...authHeader,
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/unread-count`, { headers })
  if (!res.ok) {
    throw new Error(`Failed to fetch unread count: ${res.statusText}`)
  }
  return res.json()
}

export async function markNotificationRead(notificationId) {
  if (!notificationId) return { success: false }
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/${notificationId}/read`, {
    method: "PATCH",
    headers,
  })
  if (!res.ok) {
    throw new Error(`Failed to mark notification read: ${res.statusText}`)
  }
  return res.json()
}

export async function markAllNotificationsRead() {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/read-all`, {
    method: "PATCH",
    headers,
  })
  if (!res.ok) {
    throw new Error(`Failed to mark all notifications read: ${res.statusText}`)
  }
  return res.json()
}

export async function registerDeviceToken(fcmToken, deviceType = "WEB") {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/device-token`, {
    method: "POST",
    headers,
    body: JSON.stringify({ fcm_token: fcmToken, device_type: deviceType }),
  })
  if (!res.ok) {
    throw new Error(`Failed to register device token: ${res.statusText}`)
  }
  return res.json()
}

export async function deregisterDeviceToken(fcmToken) {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/device-token`, {
    method: "DELETE",
    headers,
    body: JSON.stringify({ fcm_token: fcmToken }),
  })
  if (!res.ok) {
    throw new Error(`Failed to deregister device token: ${res.statusText}`)
  }
  return res.json()
}

export async function fetchNotificationPreferences() {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/preferences`, { headers })
  if (!res.ok) {
    throw new Error(`Failed to fetch notification preferences: ${res.statusText}`)
  }
  return res.json()
}

export async function updateNotificationPreferences(preferences) {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/preferences`, {
    method: "PUT",
    headers,
    body: JSON.stringify(preferences),
  })
  if (!res.ok) {
    throw new Error(`Failed to update notification preferences: ${res.statusText}`)
  }
  return res.json()
}

export async function fetchUserWatchlists() {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/watchlists`, { headers })
  if (!res.ok) {
    throw new Error(`Failed to fetch watchlists: ${res.statusText}`)
  }
  return res.json()
}

export async function addUserWatchlist({ symbol, target_high_price, target_low_price }) {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/watchlists`, {
    method: "POST",
    headers,
    body: JSON.stringify({ symbol, target_high_price, target_low_price }),
  })
  if (!res.ok) {
    throw new Error(`Failed to add watchlist item: ${res.statusText}`)
  }
  return res.json()
}

export async function deleteUserWatchlist(watchlistId) {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/notifications/watchlists/${watchlistId}`, {
    method: "DELETE",
    headers,
  })
  if (!res.ok) {
    throw new Error(`Failed to delete watchlist item: ${res.statusText}`)
  }
  return res.json()
}
