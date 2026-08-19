import React, { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { v4 as uuidv4 } from "uuid";

export const GoalsContext = createContext(null);

const STORAGE_KEY = "gp_goals_v2_redesign";

export {
  ASSET_TYPES,
  ASSET_COLORS,
  formatINR,
  getTodayString,
  formatDateDisplay,
  calculateDaysLeft,
  getAssetAllocation,
  getMilestones,
  getMotivationalMessage,
  calculateGoalHealth,
  calculateSavingsForecast,
} from "./goalHelpers.js";

import {
  getTodayString,
} from "./goalHelpers.js";

import { fetchGoals, createGoalApi, updateGoalApi, deleteGoalApi, addGoalProgressApi } from "../../../api/goalsApi.js";

function transformBackendGoal(bg) {
  const history = (bg.history || []).map((h) => ({
    id: h.progress_id,
    date: h.progress_date,
    amount: Number(h.quantity_added) || 0,
    assetType: h.remarks?.replace("Added ", "") || "Gold",
    remarks: h.remarks,
    runningTotal: 0,
    progressPercent: 0,
    timestamp: new Date(h.created_at).getTime(),
  }));

  // Sort history ascending by date
  history.sort((a, b) => new Date(a.date) - new Date(b.date));
  let running = 0;
  history.forEach((item) => {
    running += item.amount;
    item.runningTotal = running;
    item.progressPercent = bg.target_quantity > 0 ? Math.round((running / bg.target_quantity) * 100) : 0;
  });
  // Reverse for display (latest first)
  const displayHistory = [...history].reverse();

  return {
    id: bg.goal_id,
    name: bg.goal_name,
    note: bg.notes || "",
    target: Number(bg.target_quantity) || 10000,
    progress: Number(bg.current_quantity) || 0,
    startDate: bg.start_date,
    endDate: bg.end_date,
    unit: bg.unit || "INR",
    history: displayHistory,
    completedAt: bg.completed_at,
    createdAt: new Date(bg.created_at).getTime(),
  };
}

const getStorageKey = () => `gp_goals_v2_${localStorage.getItem("access_token") || "anon"}`;

export function GoalsProvider({ children }) {
  const [goals, setGoals] = useState([]);
  const [activeGoalId, setActiveGoalId] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadGoals = useCallback(async () => {
    try {
      setLoading(true);
      const serverGoals = await fetchGoals();
      if (Array.isArray(serverGoals)) {
        const transformed = serverGoals.map(transformBackendGoal);
        setGoals(transformed);
        if (transformed.length > 0) {
          setActiveGoalId((curr) => (curr && transformed.some((g) => g.id === curr) ? curr : transformed[0].id));
        } else {
          setActiveGoalId(null);
        }
      }
    } catch (e) {
      console.warn("Failed to load goals from backend, checking user cache:", e);
      try {
        const raw = localStorage.getItem(getStorageKey());
        if (raw) {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setGoals(parsed);
            setActiveGoalId(parsed[0].id);
          }
        }
      } catch (cacheErr) {
        console.error("User cache load failed:", cacheErr);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Load backend goals on mount
  useEffect(() => {
    loadGoals();
  }, [loadGoals]);

  // Sync cache on updates
  useEffect(() => {
    if (goals.length > 0) {
      try {
        localStorage.setItem(getStorageKey(), JSON.stringify(goals));
      } catch (e) {
        console.error("Failed to save goals cache", e);
      }
    }
  }, [goals]);

  const activeGoal = useMemo(() => {
    return goals.find((g) => g.id === activeGoalId) || goals[0] || null;
  }, [goals, activeGoalId]);

  // Create Goal
  const createGoal = useCallback(
    async (payload) => {
      const serverGoal = await createGoalApi(payload);
      const transformed = transformBackendGoal(serverGoal);
      setGoals((prev) => [transformed, ...prev.filter((g) => g.id !== transformed.id)]);
      setActiveGoalId(transformed.id);
      return transformed;
    },
    []
  );

  // Update Goal Details
  const updateGoal = useCallback(
    async (id, fields) => {
      const serverGoal = await updateGoalApi(id, fields);
      const transformed = transformBackendGoal(serverGoal);
      setGoals((prev) => prev.map((g) => (g.id === id ? transformed : g)));
      return transformed;
    },
    []
  );

  // Update Progress
  const addProgress = useCallback(
    async (id, { amount, assetType, date, remarks }) => {
      const addedAmt = Number(amount) || 0;
      if (addedAmt <= 0) return;

      const serverGoal = await addGoalProgressApi(id, { amount: addedAmt, assetType, date, remarks });
      const transformed = transformBackendGoal(serverGoal);
      setGoals((prev) => prev.map((g) => (g.id === id ? transformed : g)));
      return transformed;
    },
    []
  );

  // Delete Goal
  const deleteGoal = useCallback(
    async (id) => {
      await deleteGoalApi(id);
      setGoals((prev) => prev.filter((g) => g.id !== id));
      setActiveGoalId((curr) => (curr === id ? null : curr));
    },
    []
  );

  return (
    <GoalsContext.Provider
      value={{
        goals,
        activeGoal,
        setActiveGoalId,
        createGoal,
        updateGoal,
        addProgress,
        deleteGoal,
        loadGoals,
        loading,
      }}
    >
      {children}
    </GoalsContext.Provider>
  );
}
