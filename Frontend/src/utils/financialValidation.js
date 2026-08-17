/**
 * Financial Input Validation & Sanitization Utility for GlobalPulse.
 * Enforces strict limits:
 * - Max 13 integer digits (<= 9,999,999,999,999)
 * - Max 2 decimal places
 * - Positive numbers only
 * - No scientific notation, NaN, Infinity, or alphabetic characters
 * - Standard string limits: Name <= 100 chars, Notes <= 500 chars
 */

export const MAX_FINANCIAL_INT_DIGITS = 13;
export const MAX_FINANCIAL_DECIMALS = 2;
export const MAX_FINANCIAL_AMOUNT = 9999999999999.99;
export const MAX_NAME_LENGTH = 100;
export const MAX_NOTE_LENGTH = 500;

/**
 * Sanitizes user input string for monetary fields as they type or paste.
 * Restricts integer part to 13 digits and decimal part to 2 digits.
 * Strips all invalid characters ('e', 'E', '+', '-', alphabetic, symbols).
 *
 * @param {string} raw
 * @param {boolean} allowDecimals
 * @returns {string} Clean numeric string
 */
export function sanitizeFinancialInput(raw, allowDecimals = true) {
  if (raw === null || raw === undefined) return "";
  let clean = String(raw).replace(/[^0-9.]/g, "");

  // If no decimals allowed, strip all non-digits
  if (!allowDecimals) {
    clean = clean.replace(/[^0-9]/g, "");
    return clean.slice(0, MAX_FINANCIAL_INT_DIGITS);
  }

  // Handle at most one decimal point
  const parts = clean.split(".");
  let intPart = parts[0] ? parts[0].slice(0, MAX_FINANCIAL_INT_DIGITS) : "";
  if (parts.length > 1) {
    const decPart = parts.slice(1).join("").slice(0, MAX_FINANCIAL_DECIMALS);
    return `${intPart}.${decPart}`;
  }
  return intPart;
}

/**
 * Validates a monetary value.
 *
 * @param {string|number} value
 * @param {object} options
 * @returns {{ isValid: boolean, error: string | null, numValue: number }}
 */
export function validateFinancialAmount(value, options = {}) {
  const {
    fieldName = "Amount",
    min = 0.01,
    minError = null,
    max = MAX_FINANCIAL_AMOUNT,
    maxError = null,
    required = true,
  } = options;

  const strVal = String(value || "").trim();

  if (!strVal) {
    if (required) {
      return { isValid: false, error: `${fieldName} is required.`, numValue: 0 };
    }
    return { isValid: true, error: null, numValue: 0 };
  }

  // Check for forbidden characters
  if (/[eE+-]/.test(strVal) || !/^\d+(\.\d{1,2})?$/.test(strVal)) {
    return {
      isValid: false,
      error: `Please enter a valid numeric ${fieldName.toLowerCase()} (up to 2 decimal places).`,
      numValue: 0,
    };
  }

  const num = Number(strVal);

  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return { isValid: false, error: `Invalid ${fieldName.toLowerCase()}.`, numValue: 0 };
  }

  // Check integer digits length
  const [intPart] = strVal.split(".");
  if (intPart.length > MAX_FINANCIAL_INT_DIGITS || num > max) {
    return {
      isValid: false,
      error: maxError || `${fieldName} cannot exceed 13 digits (₹99,99,999 crore).`,
      numValue: num,
    };
  }

  if (num < min) {
    return {
      isValid: false,
      error: minError || `${fieldName} must be at least ₹${min.toLocaleString("en-IN")}.`,
      numValue: num,
    };
  }

  return { isValid: true, error: null, numValue: num };
}

/**
 * Validates string field length.
 *
 * @param {string} text
 * @param {number} maxLength
 * @param {string} fieldName
 * @param {boolean} required
 * @returns {{ isValid: boolean, error: string | null }}
 */
export function validateTextLength(text, maxLength = MAX_NOTE_LENGTH, fieldName = "Field", required = false) {
  const str = String(text || "").trim();
  if (!str) {
    if (required) {
      return { isValid: false, error: `${fieldName} is required.` };
    }
    return { isValid: true, error: null };
  }
  if (str.length > maxLength) {
    return {
      isValid: false,
      error: `${fieldName} cannot exceed ${maxLength} characters (currently ${str.length}).`,
    };
  }
  return { isValid: true, error: null };
}

/**
 * Safe currency formatter that does not render absurd unbounded numbers.
 */
export function formatSafeINR(val) {
  if (val === null || val === undefined || isNaN(val) || !isFinite(val)) return "₹0";
  const num = Number(val);
  if (num <= 0) return "₹0";
  if (num > MAX_FINANCIAL_AMOUNT) return "₹99,99,999 Cr+";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Math.round(num));
}
