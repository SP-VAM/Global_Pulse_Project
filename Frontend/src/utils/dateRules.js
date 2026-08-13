/**
 * GlobalPulse Centralized Date Rules & Boundary Utility
 * 
 * Rules:
 * TODAY = Current system date
 * MIN_DATE = TODAY - 13 years (inclusive)
 * MAX_DATE = TODAY + 25 years (inclusive)
 * 
 * Range: MIN_DATE <= selectedDate <= MAX_DATE
 */

/**
 * Returns today's Date object normalized to start of day.
 */
export function getToday() {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now;
}

/**
 * Formats a Date object to YYYY-MM-DD string.
 */
export function formatDateISO(d) {
  if (!d || isNaN(new Date(d).getTime())) return "";
  const dateObj = new Date(d);
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, "0");
  const day = String(dateObj.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Returns today's ISO date string (YYYY-MM-DD).
 */
export function getTodayISO() {
  return formatDateISO(getToday());
}

/**
 * MIN_DATE: TODAY - 13 years (exact calendar year arithmetic)
 */
export function getMinDate(refDate = getToday()) {
  const d = new Date(refDate);
  d.setFullYear(d.getFullYear() - 13);
  return d;
}

export function getMinDateISO() {
  return formatDateISO(getMinDate());
}

/**
 * MAX_DATE: TODAY + 25 years (exact calendar year arithmetic)
 */
export function getMaxDate(refDate = getToday()) {
  const d = new Date(refDate);
  d.setFullYear(d.getFullYear() + 25);
  return d;
}

export function getMaxDateISO() {
  return formatDateISO(getMaxDate());
}

export const MIN_YEAR = getMinDate().getFullYear(); // e.g. 2013 if today is 2026
export const MAX_YEAR = getMaxDate().getFullYear(); // e.g. 2051 if today is 2026

/**
 * Returns an array of allowed years between startYear and endYear (inclusive).
 * Clamped strictly to [MIN_YEAR, MAX_YEAR].
 */
export function getAllowedYears(startYear = MIN_YEAR, endYear = MAX_YEAR) {
  const min = Math.max(MIN_YEAR, Math.min(startYear, endYear));
  const max = Math.min(MAX_YEAR, Math.max(startYear, endYear));
  const years = [];
  for (let y = min; y <= max; y++) {
    years.push(y);
  }
  return years;
}

/**
 * Returns array of months (0..11) allowed for a given year.
 */
export function getAllowedMonthsForYear(year) {
  const minDate = getMinDate();
  const maxDate = getMaxDate();
  const minYr = minDate.getFullYear();
  const maxYr = maxDate.getFullYear();

  let startMonth = 0;
  let endMonth = 11;

  if (year === minYr) {
    startMonth = minDate.getMonth();
  }
  if (year === maxYr) {
    endMonth = maxDate.getMonth();
  }

  const months = [];
  for (let m = startMonth; m <= endMonth; m++) {
    months.push(m);
  }
  return months;
}

/**
 * Checks if a date string or Date object falls within MIN_DATE and MAX_DATE inclusive.
 */
export function isDateWithinGlobalBounds(dateStr) {
  if (!dateStr) return false;
  const targetStr = typeof dateStr === "string" ? dateStr : formatDateISO(dateStr);
  const minStr = getMinDateISO();
  const maxStr = getMaxDateISO();
  return targetStr >= minStr && targetStr <= maxStr;
}

/**
 * Main Calendar (Expense Tracker) Previous Month Navigation Guard.
 * Returns true if moving backward from (year, month) would violate MIN_DATE.
 */
export function isPrevMonthDisabled(year, month) {
  const minDate = getMinDate();
  const minYr = minDate.getFullYear();
  const minMo = minDate.getMonth();
  if (year < minYr) return true;
  if (year === minYr && month <= minMo) return true;
  return false;
}

/**
 * Main Calendar (Expense Tracker) Next Month Navigation Guard.
 * Returns true if moving forward from (year, month) would violate MAX_DATE.
 */
export function isNextMonthDisabled(year, month) {
  const maxDate = getMaxDate();
  const maxYr = maxDate.getFullYear();
  const maxMo = maxDate.getMonth();
  if (year > maxYr) return true;
  if (year === maxYr && month >= maxMo) return true;
  return false;
}

/**
 * Given a selected Main Calendar year & (0-indexed) month, returns the exact
 * min and max ISO date strings for transactions (Add Income / Add Expense).
 * Restricts dates strictly to that selected month, clamped by global MIN_DATE and MAX_DATE.
 */
export function getTransactionDateBounds(year, month) {
  const minGlobal = getMinDateISO();
  const maxGlobal = getMaxDateISO();

  const monthStart = `${year}-${String(month + 1).padStart(2, "0")}-01`;
  const lastDayNum = new Date(year, month + 1, 0).getDate();
  const monthEnd = `${year}-${String(month + 1).padStart(2, "0")}-${String(lastDayNum).padStart(2, "0")}`;

  const min = monthStart < minGlobal ? minGlobal : monthStart;
  const max = monthEnd > maxGlobal ? maxGlobal : monthEnd;

  return { min, max, monthStart, monthEnd };
}

/**
 * Returns min and max date bounds for Goal End Date:
 * Min: startDateISO or 1 month after startDateISO
 * Max: MAX_DATE_ISO (exact TODAY + 25 years date)
 */
export function getGoalEndDateBounds(startDateISO) {
  const minGlobal = getMinDateISO();
  const maxGlobal = getMaxDateISO();

  let minEnd = startDateISO || getTodayISO();
  if (startDateISO) {
    const s = new Date(startDateISO);
    s.setMonth(s.getMonth() + 1);
    const sIso = formatDateISO(s);
    if (sIso > minEnd) minEnd = sIso;
  }

  const min = minEnd < minGlobal ? minGlobal : minEnd;
  const max = maxGlobal;

  return { min, max };
}

/**
 * Returns min and max bounds for Goal Contribution Date (Update Progress):
 * Min: MAX(MIN_DATE_ISO, goalStartDateISO)
 * Max: MIN(MAX_DATE_ISO, goalEndDateISO)
 */
export function getContributionDateBounds(goalStartDateISO, goalEndDateISO) {
  const minGlobal = getMinDateISO();
  const maxGlobal = getMaxDateISO();

  let min = minGlobal;
  if (goalStartDateISO && goalStartDateISO > minGlobal) {
    min = goalStartDateISO;
  }

  let max = maxGlobal;
  if (goalEndDateISO && goalEndDateISO < maxGlobal) {
    max = goalEndDateISO;
  }

  return { min, max };
}

/**
 * Format date for friendly UI display, e.g. "13 August 2026"
 */
export function formatDateDisplay(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
