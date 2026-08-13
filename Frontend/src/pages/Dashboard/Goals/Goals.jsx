import React, { useContext, useState, useEffect } from "react";
import { GoalsContext } from "./goalsContext.jsx";

import GoalsLanding from "./components/GoalsLanding/GoalsLanding.jsx";
import GoalCreation from "./components/GoalCreation/GoalCreation.jsx";
import GoalDashboard from "./components/GoalDashboard/GoalDashboard.jsx";
import UpdateGoalDrawer from "./components/UpdateGoalDrawer/UpdateGoalDrawer.jsx";
import UpdateProgressDrawer from "./components/UpdateProgressDrawer/UpdateProgressDrawer.jsx";
import DeleteConfirmationModal from "./components/DeleteConfirmationModal/DeleteConfirmationModal.jsx";

import "./Goals.css";

export default function Goals() {
  const {
    activeGoal,
    createGoal,
    updateGoal,
    addProgress,
    deleteGoal,
  } = useContext(GoalsContext);

  // View modes: 'landing' | 'create' | 'dashboard'
  const [view, setView] = useState(() => (activeGoal ? "dashboard" : "landing"));

  // Slide-over drawers & Modals
  const [showUpdateGoal, setShowUpdateGoal] = useState(false);
  const [showUpdateProgress, setShowUpdateProgress] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);

  // Sync view when activeGoal state changes
  useEffect(() => {
    if (!activeGoal && view === "dashboard") {
      setView("landing");
    } else if (activeGoal && view === "landing") {
      setView("dashboard");
    }
  }, [activeGoal, view]);

  // Handle Goal Creation
  const handleCreateGoal = (payload) => {
    createGoal(payload);
    setView("dashboard");
  };

  // Handle Goal Update
  const handleUpdateGoal = (updatedFields) => {
    if (activeGoal) {
      updateGoal(activeGoal.id, updatedFields);
      setToastMsg("Goal details updated successfully!");
      setTimeout(() => setToastMsg(null), 3500);
    }
  };

  // Handle Progress Addition
  const handleAddProgress = (progressData) => {
    if (activeGoal) {
      addProgress(activeGoal.id, progressData);
      setToastMsg("Goal progress updated successfully!");
      setTimeout(() => setToastMsg(null), 3500);
    }
  };

  // Handle Goal Deletion
  const handleConfirmDelete = () => {
    if (activeGoal) {
      deleteGoal(activeGoal.id);
      setShowDeleteConfirm(false);
      setShowUpdateGoal(false);
      setShowUpdateProgress(false);
      setView("landing");
    }
  };

  return (
    <div className="goals-page">
      {toastMsg && (
        <div style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          background: "rgba(46, 194, 126, 0.95)",
          color: "#ffffff",
          padding: "12px 20px",
          borderRadius: "10px",
          fontWeight: 600,
          fontSize: "13.5px",
          boxShadow: "0 10px 25px rgba(0,0,0,0.4)",
          zIndex: 99999,
          display: "flex",
          alignItems: "center",
          gap: "8px"
        }}>
          <span>✓ {toastMsg}</span>
        </div>
      )}
      {/* 1. Goals Landing Page */}
      {view === "landing" && (
        <GoalsLanding onSetGoal={() => setView("create")} />
      )}

      {/* 2. Goal Creation Page */}
      {view === "create" && (
        <GoalCreation
          onCancel={() => setView(activeGoal ? "dashboard" : "landing")}
          onCreateSuccess={handleCreateGoal}
        />
      )}

      {/* 3. Goal Dashboard */}
      {view === "dashboard" && activeGoal && (
        <GoalDashboard
          goal={activeGoal}
          onOpenUpdateGoal={() => setShowUpdateGoal(true)}
          onOpenUpdateProgress={() => setShowUpdateProgress(true)}
          onDeleteGoal={() => setShowDeleteConfirm(true)}
        />
      )}

      {/* Slide-over Drawer: Update Goal */}
      {showUpdateGoal && activeGoal && (
        <UpdateGoalDrawer
          goal={activeGoal}
          onClose={() => setShowUpdateGoal(false)}
          onUpdateGoal={handleUpdateGoal}
          onOpenDeleteConfirm={() => setShowDeleteConfirm(true)}
        />
      )}

      {/* Slide-over Drawer: Update Progress */}
      {showUpdateProgress && activeGoal && (
        <UpdateProgressDrawer
          goal={activeGoal}
          onClose={() => setShowUpdateProgress(false)}
          onAddProgress={handleAddProgress}
        />
      )}

      {/* Modal: Delete Confirmation */}
      {showDeleteConfirm && (
        <DeleteConfirmationModal
          onClose={() => setShowDeleteConfirm(false)}
          onConfirmDelete={handleConfirmDelete}
        />
      )}
    </div>
  );
}
