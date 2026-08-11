export function formatErrorMessage(detail, fallback = "An error occurred. Please try again.") {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((err) => err.msg || JSON.stringify(err)).join(", ");
  }
  if (typeof detail === "object" && detail.msg) {
    return detail.msg;
  }
  return fallback;
}
