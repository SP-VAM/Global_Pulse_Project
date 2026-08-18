/**
 * Market & Stock Analysis API Client
 *
 * Communicates with the FastAPI backend:
 *   /api/v1/stocks
 *   /api/v1/quotes
 *   /api/v1/india-impact
 *   /api/v1/news
 *
 * Production backend:
 *   VITE_API_BASE_URL
 *
 * Local development fallback:
 *   http://localhost:8000
 */

// ---------------------------------------------------------
// API BASE URL
// ---------------------------------------------------------

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

const API_BASE = `${API_BASE_URL}/api/v1`;

// ---------------------------------------------------------
// Generic API Request Helper
// ---------------------------------------------------------

async function request(endpoint, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  // Get authentication token
  const token = localStorage.getItem("access_token");

  if (token && token !== "demo_token") {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Safely read response
  const contentType = (
    response.headers.get("content-type") || ""
  ).toLowerCase();

  let data = null;

  if (contentType.includes("application/json")) {
    const text = await response.text();

    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
  } else {
    const text = await response.text();

    if (text) {
      data = { detail: text };
    }
  }

  // Handle errors
  if (!response.ok) {
    const errorMessage =
      data?.detail ||
      data?.message ||
      `HTTP error ${response.status}`;

    throw new Error(errorMessage);
  }

  return data;
}

// ---------------------------------------------------------
// Supported Nifty 50 Companies
// ---------------------------------------------------------

/**
 * Get list of supported Nifty 50 companies.
 */
export async function getSupportedCompanies() {
  return request("/stocks/companies");
}

// ---------------------------------------------------------
// Market Snapshot
// ---------------------------------------------------------

/**
 * Get bulk market snapshot for top movers and summary cards.
 *
 * @param {string} symbols
 */
export async function getMarketSnapshot(symbols) {
  const query = symbols
    ? `?symbols=${encodeURIComponent(symbols)}`
    : "";

  return request(`/stocks/market-snapshot${query}`);
}

// ---------------------------------------------------------
// Stock Analysis
// ---------------------------------------------------------

/**
 * Get complete stock analysis.
 *
 * Includes:
 * - Current price
 * - Previous close
 * - Open / High / Low
 * - Technical indicators
 * - ML prediction
 * - Feature importance
 *
 * @param {string} symbol
 * @param {string} period
 */
export async function getStockAnalysis(symbol, period = "1y", fetchOptions = {}) {
  const cleanSymbol = String(symbol || "")
    .replace(".NS", "")
    .trim()
    .toUpperCase();

  if (!cleanSymbol) {
    throw new Error("Stock symbol is required.");
  }

  return request(
    `/stocks/${encodeURIComponent(cleanSymbol)}/analysis?period=${encodeURIComponent(period)}`,
    fetchOptions
  );
}

// ---------------------------------------------------------
// Technical Indicators
// ---------------------------------------------------------

/**
 * Get technical indicators for a stock.
 *
 * Includes:
 * - RSI
 * - MACD
 * - Bollinger Bands
 * - Moving Averages
 *
 * @param {string} symbol
 * @param {string} period
 */
export async function getStockIndicators(symbol, period = "1y") {
  const cleanSymbol = String(symbol || "")
    .replace(".NS", "")
    .trim()
    .toUpperCase();

  if (!cleanSymbol) {
    throw new Error("Stock symbol is required.");
  }

  return request(
    `/stocks/${encodeURIComponent(
      cleanSymbol
    )}/indicators?period=${encodeURIComponent(period)}`
  );
}

// ---------------------------------------------------------
// ML Stock Prediction
// ---------------------------------------------------------

/**
 * Get ML next-day price movement prediction.
 *
 * @param {string} symbol
 */
export async function getStockPrediction(symbol) {
  const cleanSymbol = String(symbol || "")
    .replace(".NS", "")
    .trim()
    .toUpperCase();

  if (!cleanSymbol) {
    throw new Error("Stock symbol is required.");
  }

  return request(
    `/stocks/${encodeURIComponent(cleanSymbol)}/prediction`
  );
}

// ---------------------------------------------------------
// Stock News Sentiment
// ---------------------------------------------------------

/**
 * Get real dynamic news sentiment for a stock symbol.
 *
 * @param {string} symbol
 */
export async function getStockSentiment(symbol) {
  const cleanSymbol = String(symbol || "")
    .replace(".NS", "")
    .trim()
    .toUpperCase();

  if (!cleanSymbol) {
    throw new Error("Stock symbol is required.");
  }

  return request(
    `/stocks/${encodeURIComponent(cleanSymbol)}/sentiment`
  );
}


// ---------------------------------------------------------
// Live Quote
// ---------------------------------------------------------

/**
 * Get live real-time market quote.
 *
 * @param {string} symbol
 */
export async function getQuote(symbol) {
  const cleanSymbol = String(symbol || "")
    .replace(".NS", "")
    .trim()
    .toUpperCase();

  if (!cleanSymbol) {
    throw new Error("Stock symbol is required.");
  }

  return request(
    `/quotes/${encodeURIComponent(cleanSymbol)}`
  );
}

// ---------------------------------------------------------
// India Impact
// ---------------------------------------------------------

/**
 * Get India Impact sector assessment.
 */
export async function getIndiaImpactSectorEffects() {
  return request("/india-impact/sector-effects");
}

// ---------------------------------------------------------
// Latest News
// ---------------------------------------------------------

/**
 * Get latest news items for the live market feed.
 *
 * @param {number} pageSize
 */
export async function getLatestNews(pageSize = 5) {
  const size = Math.max(1, Number(pageSize) || 5);

  return request(
    `/news?pageSize=${encodeURIComponent(size)}`
  );
}

// ---------------------------------------------------------
// Export API configuration for debugging
// ---------------------------------------------------------

export { API_BASE_URL, API_BASE };