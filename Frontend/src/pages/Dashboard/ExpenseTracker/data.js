import { Utensils, Car, ShoppingBag, Home, Film, HeartPulse, Landmark, Sparkles } from "lucide-react";

/** Expense categories with their icon + accent colour. */
export const CATEGORIES = [
  { id: "food", label: "Food", icon: Utensils, color: "#2f6bff" },
  { id: "transport", label: "Transport", icon: Car, color: "#2ec27e" },
  { id: "shopping", label: "Shopping", icon: ShoppingBag, color: "#8a94a6" },
  { id: "rent", label: "Rent", icon: Home, color: "#4f83ff" },
  { id: "entertainment", label: "Entertainment", icon: Film, color: "#f5a524" },
  { id: "health", label: "Health", icon: HeartPulse, color: "#ef4b5b" },
  { id: "bills", label: "Bills", icon: Landmark, color: "#22b8cf" },
  { id: "other", label: "Other", icon: Sparkles, color: "#a78bfa" },
];

export const CATEGORY_MAP = Object.fromEntries(CATEGORIES.map((c) => [c.id, c]));

export const PAYMENT_METHODS = ["Cash", "Card", "UPI", "Net Banking", "Wallet"];

/** Format a number as Indian-locale rupees. */
export function formatINR(n) {
  const value = Number(n) || 0;
  return "₹" + value.toLocaleString("en-IN");
}

/** Build a YYYY-MM-DD key for a given year/month(0-based)/day. */
export function dateKey(year, month, day) {
  return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

/** Human date, e.g. "26 July 2026". */
export function prettyDate(key) {
  if (!key) return "";
  const [y, m, d] = key.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
export const monthLabel = (year, month) => `${MONTHS[month]} ${year}`;

let seq = 1000;
export const nextId = () => ++seq;
