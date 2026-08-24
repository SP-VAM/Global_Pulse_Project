import { API_BASE_URL } from "../config/api.js";

const API_BASE = `${API_BASE_URL}/api/v1/auth`;

async function request(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  const token = localStorage.getItem('access_token')
  if (token && token !== 'demo_token') {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (response.status === 401 && !endpoint.includes('/login') && !endpoint.includes('/signup')) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('token')
    if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
      window.location.href = '/login'
    }
    throw new Error('Session expired. Please log in again.')
  }

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const errorMsg = data.error?.message || data.detail || data.message || `HTTP error ${response.status}`
    throw new Error(errorMsg)
  }

  return data
}

export async function sendOtp(payload) {
  // payload: { mobileNumber, email, target }
  return request('/send-otp', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function verifyOtp(payload) {
  // payload: { target, otpCode, mobileNumber }
  return request('/verify-otp', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function signup(payload) {
  // payload: { username, email, password, mobileNumber, verificationToken }
  const data = await request('/signup', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  const token = data.access_token || data.accessToken
  if (token && token !== 'demo_token') {
    localStorage.setItem('access_token', token)
    localStorage.setItem('token', token)
  }
  if (data.user) {
    localStorage.setItem('user', JSON.stringify(data.user))
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('user-updated'))
  }
  return data
}

export async function login(payload) {
  // payload: { identity, password }
  const data = await request('/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  const token = data.access_token || data.accessToken
  if (token && token !== 'demo_token') {
    localStorage.setItem('access_token', token)
    localStorage.setItem('token', token)
  }
  if (data.user) {
    localStorage.setItem('user', JSON.stringify(data.user))
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('user-updated'))
  }
  return data
}

export async function getMe() {
  const user = await request('/me', {
    method: 'GET',
  })
  if (user && typeof user === 'object') {
    localStorage.setItem('user', JSON.stringify(user))
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('user-updated'))
  }
  return user
}

export async function updateProfile(payload) {
  // payload: { username, email, mobileNumber, firstName, lastName }
  const updatedUser = await request('/me', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
  if (updatedUser && typeof updatedUser === 'object') {
    localStorage.setItem('user', JSON.stringify(updatedUser))
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('user-updated'))
  }
  return updatedUser
}

export async function getUserSettings() {
  return request('/settings', {
    method: 'GET',
  })
}

export async function updateUserSettings(payload) {
  // payload: { priceAlerts, darkMode, weeklyDigest, twoFactorAuth }
  return request('/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}
