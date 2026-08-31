/**
 * Single Authoritative Initial Generation Utility for GlobalPulse
 *
 * Rules:
 * 1. Reads the user object's current name fields in priority order:
 *    first_name -> firstName -> full_name -> fullName -> display_name -> name -> username -> email
 * 2. Trims leading/trailing whitespace.
 * 3. Extracts the first character.
 * 4. Converts to uppercase.
 * 5. Returns safe fallback "U" if no valid user/name is provided.
 *
 * @param {Object} user - Authenticated user/profile object
 * @returns {string} Single uppercase initial character
 */
export function getUserInitial(user) {
  if (!user || typeof user !== "object") return "U"

  const candidateNames = [
    user.first_name,
    user.firstName,
    user.full_name,
    user.fullName,
    user.display_name,
    user.name,
    user.username,
    user.email,
  ]

  for (const name of candidateNames) {
    if (typeof name === "string") {
      const trimmed = name.trim()
      if (trimmed.length > 0) {
        return trimmed[0].toUpperCase()
      }
    }
  }

  return "U"
}
