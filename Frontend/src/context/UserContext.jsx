import React, { createContext, useContext, useState, useEffect } from "react"

const UserContext = createContext(null)

export function UserProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem("user")
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })

  useEffect(() => {
    const handleUserUpdate = () => {
      try {
        const saved = localStorage.getItem("user")
        setUser(saved ? JSON.parse(saved) : null)
      } catch (e) {
        console.error("Error reading updated user from storage:", e)
      }
    }

    window.addEventListener("user-updated", handleUserUpdate)
    window.addEventListener("storage", handleUserUpdate)
    return () => {
      window.removeEventListener("user-updated", handleUserUpdate)
      window.removeEventListener("storage", handleUserUpdate)
    }
  }, [])

  const updateUser = (userData) => {
    try {
      const saved = localStorage.getItem("user")
      const parsed = saved ? JSON.parse(saved) : {}
      const merged = { ...parsed, ...userData }
      localStorage.setItem("user", JSON.stringify(merged))
      setUser(merged)
      window.dispatchEvent(new Event("user-updated"))
      window.dispatchEvent(new Event("storage"))
    } catch (e) {
      console.error("Error updating user:", e)
    }
  }

  const updateAvatar = (avatarUrl) => {
    try {
      const saved = localStorage.getItem("user")
      const parsed = saved ? JSON.parse(saved) : {}
      const merged = { ...parsed, avatar: avatarUrl, profile_image: avatarUrl, profileImage: avatarUrl }
      localStorage.setItem("user", JSON.stringify(merged))
      setUser(merged)
      window.dispatchEvent(new Event("user-updated"))
      window.dispatchEvent(new Event("storage"))
    } catch (e) {
      console.error("Error updating avatar:", e)
    }
  }

  return (
    <UserContext.Provider value={{ user, updateUser, updateAvatar }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  const context = useContext(UserContext)
  if (!context) {
    // Graceful fallback if used outside Provider
    const fallbackUpdateUser = (userData) => {
      try {
        const saved = localStorage.getItem("user")
        const parsed = saved ? JSON.parse(saved) : {}
        const merged = { ...parsed, ...userData }
        localStorage.setItem("user", JSON.stringify(merged))
        window.dispatchEvent(new Event("user-updated"))
        window.dispatchEvent(new Event("storage"))
      } catch (e) {
        console.error(e)
      }
    }
    const fallbackUpdateAvatar = (avatarUrl) => {
      try {
        const saved = localStorage.getItem("user")
        const parsed = saved ? JSON.parse(saved) : {}
        const merged = { ...parsed, avatar: avatarUrl, profile_image: avatarUrl, profileImage: avatarUrl }
        localStorage.setItem("user", JSON.stringify(merged))
        window.dispatchEvent(new Event("user-updated"))
        window.dispatchEvent(new Event("storage"))
      } catch (e) {
        console.error(e)
      }
    }
    return {
      user: null,
      updateUser: fallbackUpdateUser,
      updateAvatar: fallbackUpdateAvatar,
    }
  }
  return context
}
