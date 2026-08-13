/**
 * Market & Stock Analysis API Client
 * Interacts with FastAPI /api/v1/stocks, /api/v1/quotes, and /api/v1/india-impact endpoints
 */

const API_BASE = '/api/v1'

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

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const errorMsg = data.detail || data.message || `HTTP error ${response.status}`
    throw new Error(errorMsg)
  }

  return data
}

/**
 * Get list of supported Nifty 50 companies from backend
 */
export async function getSupportedCompanies() {
  return request('/stocks/companies')
}

/**
 * Get bulk market snapshot for top movers & summary cards
 */
export async function getMarketSnapshot(symbols) {
  const query = symbols ? `?symbols=${encodeURIComponent(symbols)}` : ''
  return request(`/stocks/market-snapshot${query}`)
}

/**
 * Get composite full analysis for a stock (Real prices, indicators, ML prediction, and feature importances)
 */
export async function getStockAnalysis(symbol, period = '1y') {
  const cleanSymbol = symbol.replace('.NS', '').trim()
  return request(`/stocks/${cleanSymbol}/analysis?period=${encodeURIComponent(period)}`)
}

/**
 * Get technical indicators for a stock (RSI, MACD, Bollinger Bands, Moving Averages)
 */
export async function getStockIndicators(symbol, period = '1y') {
  const cleanSymbol = symbol.replace('.NS', '').trim()
  return request(`/stocks/${cleanSymbol}/indicators?period=${period}`)
}

/**
 * Get ML next-day price movement prediction
 */
export async function getStockPrediction(symbol) {
  const cleanSymbol = symbol.replace('.NS', '').trim()
  return request(`/stocks/${cleanSymbol}/prediction`)
}

/**
 * Get live real-time market quote
 */
export async function getQuote(symbol) {
  return request(`/quotes/${encodeURIComponent(symbol)}`)
}

/**
 * Get India Impact sector assessment
 */
export async function getIndiaImpactSectorEffects() {
  return request('/india-impact/sector-effects')
}

/**
 * Get latest news items for live market feed
 */
export async function getLatestNews(pageSize = 5) {
  return request(`/news?pageSize=${pageSize}`)
}
