import { useState } from "react"
import { Outlet, Navigate, useNavigate } from "react-router-dom"

import { Navbar, Sidebar, LogoutConfirmationModal } from "../../../components/layout"
import { GoalsProvider } from "../Goals/goalsContext.jsx"
import StarField from "../../../components/common/StarField/StarField.jsx"

import "./DashboardLayout.css"

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showLogoutModal, setShowLogoutModal] = useState(false)
  const navigate = useNavigate()
  const token = localStorage.getItem("access_token")

  // Auth Guard: Require valid non-demo JWT token for protected dashboard layout
  if (!token || token === "demo_token" || token === "null" || token === "undefined") {
    localStorage.removeItem("access_token")
    localStorage.removeItem("token")
    return <Navigate to="/login" replace />
  }

  const handleConfirmLogout = () => {
    setShowLogoutModal(false)
    localStorage.removeItem("access_token")
    localStorage.removeItem("token")
    localStorage.removeItem("user")
    sessionStorage.clear()
    navigate("/login")
  }

  return (
    <div className={`shell${sidebarOpen ? " shell--sidebar-open" : ""}`}>
      <StarField count={80} />

      <Navbar onLogoutClick={() => setShowLogoutModal(true)} />

      <GoalsProvider>
        <Sidebar
          onHoverChange={setSidebarOpen}
          onLogoutClick={() => setShowLogoutModal(true)}
        />

        <main className="shell__content" id="main-content">
          <div className="shell__content-inner">
            <Outlet />
          </div>
        </main>
      </GoalsProvider>

      <LogoutConfirmationModal
        open={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        onConfirm={handleConfirmLogout}
      />
    </div>
  )
}
