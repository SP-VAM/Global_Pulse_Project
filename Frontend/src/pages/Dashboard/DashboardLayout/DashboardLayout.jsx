import { useState } from "react"
import { Outlet } from "react-router-dom"

import { Navbar, Sidebar } from "../../../components/layout"
import { GoalsProvider } from "../Goals/goalsContext.jsx"
import StarField from "../../../components/common/StarField/StarField.jsx"

import "./DashboardLayout.css"

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className={`shell${sidebarOpen ? " shell--sidebar-open" : ""}`}>
      <StarField count={80} />

      <Navbar />

      <GoalsProvider>
        <Sidebar onHoverChange={setSidebarOpen} />

        <main className="shell__content" id="main-content">
          <div className="shell__content-inner">
            <Outlet />
          </div>
        </main>
      </GoalsProvider>
    </div>
  )
}
