import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import {
  Plus,
  PlusCircle,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  ArrowRightLeft,
  PiggyBank,
  Calendar as CalendarIcon,
  Pencil,
  Wallet,
  History,
  PieChart,
  Award,
  TrendingUp,
  RefreshCw,
  AlertCircle,
  FolderPlus,
} from "lucide-react";

import {
  CATEGORY_MAP,
  CATEGORIES,
  formatINR,
  dateKey,
  prettyDate,
  monthLabel,
} from "./data.js";
import {
  getExpenseSummary,
  createExpense,
  deleteExpense,
  createIncome,
  deleteIncome,
  saveBudget as saveBudgetApi,
  deleteBudget as deleteBudgetApi,
} from "../../../api/expenseApi.js";
import TransactionModal from "./TransactionModal.jsx";
import TransactionDetailModal from "./TransactionDetailModal.jsx";
import BudgetModal from "./BudgetModal.jsx";
import "./ExpenseTracker.css";

const WEEKDAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"];

export default function ExpenseTracker() {
  // Initialize view state dynamically using the actual system date (never hardcoded July 2026)
  const now = new Date();
  const [view, setView] = useState({ year: now.getFullYear(), month: now.getMonth() });
  const [selected, setSelected] = useState(dateKey(now.getFullYear(), now.getMonth(), now.getDate()));

  // Server state fetched from PostgreSQL API
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal dialog states
  const [txModal, setTxModal] = useState(null); // { mode, type, initial }
  const [detailTx, setDetailTx] = useState(null);
  const [budgetModal, setBudgetModal] = useState(null); // { mode, initial }

  // Ref for native month/year calendar picker
  const monthInputRef = useRef(null);

  const openNativeMonthPicker = () => {
    if (monthInputRef.current && monthInputRef.current.showPicker) {
      monthInputRef.current.showPicker();
    } else if (monthInputRef.current) {
      monthInputRef.current.click();
    }
  };

  /**
   * Fetch complete monthly expense summary from FastAPI backend endpoint:
   * GET /api/v1/expenses/summary?year=Y&month=M
   */
  const loadSummary = useCallback(async (year, month) => {
    setLoading(true);
    setError(null);
    try {
      // API expects 1-indexed month (1-12)
      const data = await getExpenseSummary(year, month + 1);
      setSummaryData(data);
    } catch (err) {
      console.error("Error loading expense summary:", err);
      setError(err.message || "Unable to load expense data.");
      setSummaryData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch summary on mount and when view (year/month) changes
  useEffect(() => {
    loadSummary(view.year, view.month);
  }, [view.year, view.month, loadSummary]);

  /* ----- Derived Backend Financial Records ----- */
  const { allTransactions, totals, breakdownRows, spentByCategory, activeMonthBudgets, activeDays } = useMemo(() => {
    if (!summaryData) {
      return {
        allTransactions: [],
        totals: { spending: 0, income: 0, savings: 0 },
        breakdownRows: [],
        spentByCategory: {},
        activeMonthBudgets: [],
        activeDays: new Set(),
      };
    }

    const expensesList = summaryData.expenses || [];
    const incomesList = summaryData.incomes || [];
    const budgetsList = summaryData.budgets || [];

    // Map expenses to unified transaction schema
    const mappedExpenses = expensesList.map((e) => {
      const catName = e.category?.categoryName || "Other";
      const catKey = catName.toLowerCase();
      const timeStr = e.createdAt
        ? new Date(e.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : "12:00 PM";
      return {
        id: `exp_${e.expenseId}`,
        rawId: e.expenseId,
        type: "expense",
        amount: Number(e.amount) || 0,
        date: String(e.expenseDate),
        category: catKey,
        categoryName: catName,
        method: e.paymentMethod || "UPI",
        notes: e.notes || catName,
        time: timeStr,
        status: "Completed",
      };
    });

    // Map incomes to unified transaction schema
    const mappedIncomes = incomesList.map((i) => {
      const timeStr = i.createdAt
        ? new Date(i.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : "12:00 PM";
      return {
        id: `inc_${i.incomeId}`,
        rawId: i.incomeId,
        type: "income",
        amount: Number(i.amount) || 0,
        date: String(i.incomeDate),
        category: null,
        categoryName: "Income",
        method: i.paymentMethod || "Salary",
        notes: i.notes || "Income Deposit",
        time: timeStr,
        status: "Completed",
      };
    });

    const txs = [...mappedExpenses, ...mappedIncomes].sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );

    const totalsObj = {
      spending: summaryData.monthlySpending ?? 0,
      income: summaryData.monthlyIncome ?? 0,
      savings: summaryData.savings ?? 0,
    };

    // Calculate category spending breakdown dynamically
    const catMap = new Map();
    const spentByCatMap = {};
    for (const e of mappedExpenses) {
      const catKey = e.category;
      const amt = e.amount;
      catMap.set(catKey, (catMap.get(catKey) || 0) + amt);
      spentByCatMap[catKey] = (spentByCatMap[catKey] || 0) + amt;
    }

    const rows = [...catMap.entries()].map(([catKey, amount]) => {
      const catInfo = CATEGORY_MAP[catKey] || {
        label: catKey.charAt(0).toUpperCase() + catKey.slice(1),
        color: "#8a94a6",
      };
      return {
        id: catKey,
        amount,
        label: catInfo.label,
        color: catInfo.color,
      };
    });
    rows.sort((a, b) => b.amount - a.amount);

    // Filter budget buckets returned by backend
    const mappedBudgets = budgetsList.map((b) => {
      const catName = b.category?.categoryName || "General";
      const catKey = catName.toLowerCase();
      const catInfo = CATEGORY_MAP[catKey] || { label: catName, color: "#4f83ff" };
      return {
        id: b.budgetId,
        rawId: b.budgetId,
        category: catKey,
        label: catInfo.label,
        limit: Number(b.budgetAmount) || 0,
        notes: b.category?.description || `${catInfo.label} Budget`,
      };
    });

    // Collect calendar days with active transactions
    const daysSet = new Set();
    for (const t of txs) {
      if (t.date) {
        const dayNum = Number(t.date.split("-")[2]);
        if (!isNaN(dayNum)) daysSet.add(dayNum);
      }
    }

    return {
      allTransactions: txs,
      totals: totalsObj,
      breakdownRows: rows,
      spentByCategory: spentByCatMap,
      activeMonthBudgets: mappedBudgets,
      activeDays: daysSet,
    };
  }, [summaryData]);

  /* Filter transactions for currently selected date */
  const dayTx = useMemo(
    () => allTransactions.filter((t) => t.date === selected),
    [allTransactions, selected]
  );
  const dayTotal = useMemo(
    () => dayTx.reduce((s, t) => s + (t.type === "expense" ? t.amount : 0), 0),
    [dayTx]
  );

  /* Sorted Budget Buckets by Risk (Highest % Spent First) */
  const sortedBudgets = useMemo(() => {
    return [...activeMonthBudgets].sort((a, b) => {
      const spentA = spentByCategory[a.category] || 0;
      const spentB = spentByCategory[b.category] || 0;
      const pctA = a.limit ? (spentA / a.limit) * 100 : 0;
      const pctB = b.limit ? (spentB / b.limit) * 100 : 0;
      return pctB - pctA;
    });
  }, [activeMonthBudgets, spentByCategory]);

  /* Calendar Grid Calculation */
  const cells = useMemo(() => {
    const first = new Date(view.year, view.month, 1);
    const daysInMonth = new Date(view.year, view.month + 1, 0).getDate();
    const startOffset = (first.getDay() + 6) % 7;
    const out = [];
    for (let i = 0; i < startOffset; i++) out.push(null);
    for (let d = 1; d <= daysInMonth; d++) out.push(d);
    return out;
  }, [view]);

  /* Month Navigation */
  const changeMonth = (dir) => {
    setView((v) => {
      let newYr = v.year;
      let newMo = v.month + dir;
      if (newMo < 0) {
        newYr -= 1;
        newMo = 11;
      } else if (newMo > 11) {
        newYr += 1;
        newMo = 0;
      }
      setSelected(dateKey(newYr, newMo, 1));
      return { year: newYr, month: newMo };
    });
  };

  /* ----- Backend Mutations ----- */
  const saveTx = async (payload) => {
    try {
      if (txModal.type === "expense") {
        const catObj = CATEGORY_MAP[payload.category];
        const categoryName = catObj ? catObj.label : payload.category || "Other";
        await createExpense({
          amount: Number(payload.amount),
          expenseDate: payload.date,
          categoryName: categoryName,
          paymentMethod: payload.method || "UPI",
          notes: payload.notes || "",
        });
      } else {
        await createIncome({
          amount: Number(payload.amount),
          incomeDate: payload.date,
          paymentMethod: payload.method || "Salary",
          notes: payload.notes || "",
        });
      }

      setTxModal(null);
      // Refetch authoritative backend summary
      await loadSummary(view.year, view.month);
    } catch (err) {
      alert(`Error saving transaction: ${err.message}`);
    }
  };

  const deleteTx = async (tx) => {
    try {
      if (tx.type === "expense") {
        await deleteExpense(tx.rawId);
      } else {
        await deleteIncome(tx.rawId);
      }
      setDetailTx(null);
      await loadSummary(view.year, view.month);
    } catch (err) {
      alert(`Error deleting transaction: ${err.message}`);
    }
  };

  const saveBudget = async (payload) => {
    try {
      const catObj = CATEGORY_MAP[payload.category];
      const categoryName = catObj ? catObj.label : payload.category || "General";
      await saveBudgetApi({
        categoryName: categoryName,
        budgetAmount: Number(payload.limit),
        budgetMonth: view.month + 1,
        budgetYear: view.year,
      });

      setBudgetModal(null);
      await loadSummary(view.year, view.month);
    } catch (err) {
      alert(`Error saving budget: ${err.message}`);
    }
  };

  const handleDeleteBudget = async (budgetId) => {
    try {
      await deleteBudgetApi(budgetId);
      setBudgetModal(null);
      await loadSummary(view.year, view.month);
    } catch (err) {
      alert(`Error deleting budget: ${err.message}`);
    }
  };

  return (
    <div className="goal-dash card-appear et-page">
      {/* ------------------- PAGE HEADER ------------------- */}
      <div className="goal-hero__head" style={{ marginBottom: "8px" }}>
        <div className="goal-hero__identity">
          <div className="goal-hero__icon-badge">
            <Wallet size={22} className="goal-hero__icon" />
          </div>
          <div>
            <div className="goal-hero__title-row">
              <h1 className="goal-hero__name">Expense Tracker</h1>
            </div>
            <p className="goal-hero__note">
              Monitor your spending, analyze category trends, and stay within your budget • {monthLabel(view.year, view.month)}
            </p>
          </div>
        </div>

        {/* Action CTAs */}
        <div className="goal-hero__actions">
          <button
            type="button"
            className="goal-hero__btn-secondary"
            onClick={() => setTxModal({ mode: "add", type: "income" })}
          >
            <Plus size={15} />
            <span>Add Income</span>
          </button>

          <button
            type="button"
            className="goal-hero__btn-primary"
            onClick={() => setTxModal({ mode: "add", type: "expense" })}
          >
            <PlusCircle size={16} />
            <span>Add Expense</span>
          </button>
        </div>
      </div>

      {/* ------------------- ERROR STATE BANNER ------------------- */}
      {error && (
        <div className="et-error-banner" style={{
          background: "rgba(239, 68, 68, 0.12)",
          border: "1px solid rgba(239, 68, 68, 0.3)",
          borderRadius: "12px",
          padding: "16px 20px",
          marginBottom: "16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          color: "#f87171"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertCircle size={20} />
            <span>Unable to load expense data: {error}</span>
          </div>
          <button
            type="button"
            onClick={() => loadSummary(view.year, view.month)}
            style={{
              background: "#ef4444",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              padding: "6px 14px",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            <RefreshCw size={14} />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* ------------------- SECTION 2: KPI CARDS GRID ------------------- */}
      <div className="goal-kpi-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        {/* KPI 1: Monthly Spending */}
        <div className="kpi-card kpi-card--amber">
          <div className="kpi-card__icon">
            <DollarSign size={16} />
          </div>
          <span className="kpi-card__label">Monthly Spending</span>
          <div className="kpi-card__val">
            {loading ? <span className="et-skeleton-text" /> : formatINR(totals.spending)}
          </div>
          <span className="kpi-card__sub" style={{ color: "#f5a524" }}>
            <TrendingUp size={12} />
            <span>
              {allTransactions.filter((t) => t.type === "expense").length} Transactions ({monthLabel(view.year, view.month).split(" ")[0]})
            </span>
          </span>
        </div>

        {/* KPI 2: Total Income */}
        <div className="kpi-card kpi-card--green">
          <div className="kpi-card__icon">
            <ArrowRightLeft size={16} />
          </div>
          <span className="kpi-card__label">Total Income</span>
          <div className="kpi-card__val">
            {loading ? <span className="et-skeleton-text" /> : formatINR(totals.income)}
          </div>
          <span className="kpi-card__sub gp-pos">
            <TrendingUp size={12} />
            <span>{monthLabel(view.year, view.month).split(" ")[0]} income</span>
          </span>
        </div>

        {/* KPI 3: Net Savings */}
        <div className="kpi-card">
          <div className="kpi-card__icon">
            <PiggyBank size={16} />
          </div>
          <span className="kpi-card__label">Net Savings</span>
          <div className="kpi-card__val">
            {loading ? <span className="et-skeleton-text" /> : formatINR(totals.savings)}
          </div>
          <span className="kpi-card__sub" style={{ color: "#38bdf8" }}>
            <span>{monthLabel(view.year, view.month).split(" ")[0]} net balance</span>
          </span>
        </div>

        {/* KPI 4: Selected Day Total */}
        <div className="kpi-card">
          <div className="kpi-card__icon">
            <CalendarIcon size={16} />
          </div>
          <span className="kpi-card__label">Spent on {prettyDate(selected).slice(0, 6)}</span>
          <div className="kpi-card__val">
            {loading ? <span className="et-skeleton-text" /> : formatINR(dayTotal)}
          </div>
          <span className="kpi-card__sub" style={{ color: "#aeb6c7" }}>
            <span>{dayTx.length} items on this date</span>
          </span>
        </div>
      </div>

      {/* ------------------- SECTION 3: MAIN 2-COLUMN EQUAL GRID ------------------- */}
      <div className="goal-main-grid">
        {/* LEFT COLUMN: Calendar Navigation Panel */}
        <div className="goal-panel">
          <div className="goal-panel__head">
            {/* Direct Native Month Calendar Picker Trigger */}
            <div
              style={{ position: "relative", display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}
              onClick={openNativeMonthPicker}
              title="Click to open Month Calendar"
            >
              <CalendarIcon size={16} className="goal-panel__head-icon" />
              <h3 className="goal-panel__title">
                {monthLabel(view.year, view.month)} <span style={{ fontSize: "11px", color: "var(--text-3, #6b7385)" }}>▾</span>
              </h3>
              <input
                ref={monthInputRef}
                type="month"
                style={{
                  position: "absolute",
                  opacity: 0,
                  pointerEvents: "none",
                  width: 0,
                  height: 0,
                }}
                value={`${view.year}-${String(view.month + 1).padStart(2, "0")}`}
                onChange={(e) => {
                  if (!e.target.value) return;
                  const [y, m] = e.target.value.split("-").map(Number);
                  setView({ year: y, month: m - 1 });
                  setSelected(dateKey(y, m - 1, 1));
                }}
              />
            </div>

            <div className="et-cal__nav" style={{ marginLeft: "auto" }}>
              <button type="button" aria-label="Previous month" onClick={() => changeMonth(-1)}>
                <ChevronLeft size={16} />
              </button>
              <button type="button" aria-label="Next month" onClick={() => changeMonth(1)}>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          <div className="et-cal__weekdays">
            {WEEKDAYS.map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>

          <div className="et-cal__grid">
            {cells.map((day, i) => {
              if (day === null)
                return <span key={`e${i}`} className="et-cal__cell et-cal__cell--empty" />;
              const key = dateKey(view.year, view.month, day);
              const isSelected = key === selected;
              const hasTx = activeDays.has(day);
              return (
                <button
                  key={key}
                  type="button"
                  className={`et-cal__cell ${isSelected ? "et-cal__cell--selected" : ""} ${
                    hasTx ? "et-cal__cell--has-tx" : ""
                  }`}
                  onClick={() => setSelected(key)}
                >
                  <span className="et-cal__day-num">{day}</span>
                  {hasTx && <span className="et-cal__dot" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* RIGHT COLUMN: Transactions Panel */}
        <div className="goal-panel et-tx-panel">
          <div className="goal-panel__head">
            <History size={16} className="goal-panel__head-icon" />
            <h3 className="goal-panel__title">Transactions</h3>
            <span className="et-panel__tag">{dayTx.length} items</span>
            <span className="et-tx__date-sub">{prettyDate(selected)}</span>
          </div>

          <div className="et-tx__list">
            {loading ? (
              <div className="et-skeleton-list">
                <div className="et-skeleton-bar" />
                <div className="et-skeleton-bar" />
              </div>
            ) : dayTx.length === 0 ? (
              <div className="et-empty-state">
                <p>No transactions recorded for this date.</p>
                <button
                  type="button"
                  className="goal-hero__btn-secondary"
                  style={{ marginTop: "12px", padding: "6px 12px", fontSize: "12px" }}
                  onClick={() => setTxModal({ mode: "add", type: "expense" })}
                >
                  + Add Expense for {prettyDate(selected).slice(0, 6)}
                </button>
              </div>
            ) : (
              dayTx.map((t) => {
                const isExpense = t.type === "expense";
                const catObj = CATEGORY_MAP[t.category] || {};
                const IconComp = isExpense ? catObj.icon || Wallet : ArrowRightLeft;

                return (
                  <div key={t.id} className="et-tx-item" onClick={() => setDetailTx(t)}>
                    <div
                      className="et-tx-item__icon"
                      style={{
                        backgroundColor: isExpense
                          ? `${catObj.color || "#8a94a6"}1f`
                          : "rgba(46,194,126,0.15)",
                        color: isExpense ? catObj.color || "#8a94a6" : "#2ec27e",
                      }}
                    >
                      <IconComp size={16} />
                    </div>

                    <div className="et-tx-item__body">
                      <div className="et-tx-item__title">
                        {t.notes || (isExpense ? catObj.label || "Expense" : "Income Deposit")}
                      </div>
                      <div className="et-tx-item__meta">
                        {isExpense && (
                          <span className="et-tx-item__badge">{catObj.label || t.categoryName}</span>
                        )}
                        <span>{t.method}</span>
                        <span>•</span>
                        <span>{t.time}</span>
                      </div>
                    </div>

                    <div
                      className={`et-tx-item__amount ${
                        isExpense ? "et-tx-item__amount--exp" : "et-tx-item__amount--inc"
                      }`}
                    >
                      {isExpense ? "-" : "+"}
                      {formatINR(t.amount)}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className="et-tx__footer">
            <span>Total Spent Today</span>
            <strong>{formatINR(dayTotal)}</strong>
          </div>
        </div>
      </div>

      {/* ------------------- SECTION 4: LOWER 2-COLUMN EQUAL GRID ------------------- */}
      <div className="goal-main-grid" style={{ marginTop: "16px" }}>
        {/* LEFT COLUMN: Category Breakdown Panel */}
        <div className="goal-panel">
          <div className="goal-panel__head">
            <PieChart size={16} className="goal-panel__head-icon" />
            <h3 className="goal-panel__title">
              Category Breakdown ({monthLabel(view.year, view.month).split(" ")[0]})
            </h3>
            <span className="et-panel__tag">{breakdownRows.length} Categories</span>
          </div>

          <div className="et-cat__list">
            {loading ? (
              <div className="et-skeleton-list">
                <div className="et-skeleton-bar" />
                <div className="et-skeleton-bar" />
              </div>
            ) : breakdownRows.length === 0 ? (
              <div className="et-empty-state">
                <p>No spending recorded for this month.</p>
              </div>
            ) : (
              breakdownRows.map((r) => {
                const catObj = CATEGORY_MAP[r.id] || {};
                const IconComp = catObj.icon || Wallet;
                const pct = totals.spending > 0 ? ((r.amount / totals.spending) * 100).toFixed(1) : "0";

                return (
                  <div key={r.id} className="et-cat-row">
                    <div className="et-cat-row__header">
                      <div className="et-cat-row__left">
                        <div
                          className="et-cat-row__icon"
                          style={{
                            backgroundColor: `${r.color}1a`,
                            color: r.color,
                          }}
                        >
                          <IconComp size={15} />
                        </div>
                        <span className="et-cat-row__name">{r.label}</span>
                      </div>
                      <div className="et-cat-row__right">
                        <strong className="et-cat-row__val">{formatINR(r.amount)}</strong>
                        <span className="et-cat-row__pct">{pct}%</span>
                      </div>
                    </div>

                    <div className="et-cat-row__track">
                      <div
                        className="et-cat-row__fill"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: r.color,
                        }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Budget Buckets Panel */}
        <div className="goal-panel">
          <div className="goal-panel__head">
            <Award size={16} className="goal-panel__head-icon" />
            <h3 className="goal-panel__title">
              Budget Buckets ({monthLabel(view.year, view.month).split(" ")[0]})
            </h3>

            <button
              type="button"
              className="goal-hero__btn-secondary"
              style={{ marginLeft: "auto", padding: "4px 10px", fontSize: "12px" }}
              onClick={() => setBudgetModal({ mode: "add", initial: null })}
            >
              <Plus size={13} />
              <span>Add Budget</span>
            </button>
          </div>

          <div className="et-budget__list">
            {loading ? (
              <div className="et-skeleton-list">
                <div className="et-skeleton-bar" />
                <div className="et-skeleton-bar" />
              </div>
            ) : sortedBudgets.length === 0 ? (
              <div className="et-empty-state">
                <p>No budgets configured for this month.</p>
                <button
                  type="button"
                  className="goal-hero__btn-secondary"
                  style={{ marginTop: "10px", padding: "6px 12px", fontSize: "12px" }}
                  onClick={() => setBudgetModal({ mode: "add", initial: null })}
                >
                  + Add First Budget Limit
                </button>
              </div>
            ) : (
              sortedBudgets.map((b) => {
                const spent = spentByCategory[b.category] || 0;
                const limit = b.limit || 0;
                const over = spent > limit ? spent - limit : 0;
                const rem = limit > spent ? limit - spent : 0;
                const pct = limit > 0 ? Math.min(100, Math.round((spent / limit) * 100)) : 0;
                const isOver = over > 0;
                const catObj = CATEGORY_MAP[b.category] || {};
                const IconComp = catObj.icon || Wallet;

                return (
                  <div key={b.id} className={`et-budget-card ${isOver ? "et-budget-card--over" : ""}`}>
                    <div className="et-budget-card__head">
                      <div className="et-budget-card__identity">
                        <div
                          className="et-budget-card__icon"
                          style={{
                            backgroundColor: isOver
                              ? "rgba(239, 68, 68, 0.15)"
                              : `${catObj.color || "#4f83ff"}1f`,
                            color: isOver ? "#ef4444" : catObj.color || "#4f83ff",
                          }}
                        >
                          <IconComp size={15} />
                        </div>
                        <div>
                          <div className="et-budget-card__name">{b.label}</div>
                          <div className="et-budget-card__notes">{b.notes}</div>
                        </div>
                      </div>

                      <button
                        type="button"
                        className="et-budget-card__edit"
                        onClick={() => setBudgetModal({ mode: "edit", initial: b })}
                        title="Edit Budget Limit"
                      >
                        <Pencil size={13} />
                      </button>
                    </div>

                    <div className="et-budget-card__track">
                      <div
                        className={`et-budget-card__fill ${isOver ? "et-budget-card__fill--over" : ""}`}
                        style={{
                          width: `${pct}%`,
                          backgroundColor: isOver ? "#ef4444" : catObj.color || "#4f83ff",
                        }}
                      />
                    </div>

                    <div className="et-budget-card__meta">
                      <span className="et-budget-card__nums">
                        {formatINR(spent)} / {formatINR(limit)}
                      </span>
                      {isOver ? (
                        <span className="et-budget-card__tag et-budget-card__tag--over">
                          Over by {formatINR(over)}
                        </span>
                      ) : (
                        <span className="et-budget-card__tag">
                          {formatINR(rem)} left ({pct}%)
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* ------------------- MODAL DIALOGS ------------------- */}
      {txModal && (
        <TransactionModal
          open={Boolean(txModal)}
          mode={txModal.mode}
          type={txModal.type}
          initial={txModal.initial}
          selectedDate={selected}
          onClose={() => setTxModal(null)}
          onSave={saveTx}
        />
      )}

      {detailTx && (
        <TransactionDetailModal
          open={Boolean(detailTx)}
          tx={detailTx}
          onClose={() => setDetailTx(null)}
          onEdit={() => {
            const txToEdit = detailTx;
            setDetailTx(null);
            setTxModal({ mode: "edit", type: txToEdit.type, initial: txToEdit });
          }}
          onDelete={() => deleteTx(detailTx)}
        />
      )}

      {budgetModal && (
        <BudgetModal
          open={Boolean(budgetModal)}
          mode={budgetModal.mode}
          initial={budgetModal.initial}
          onClose={() => setBudgetModal(null)}
          onSave={saveBudget}
          onDelete={() => handleDeleteBudget(budgetModal.initial?.rawId || budgetModal.initial?.id)}
        />
      )}
    </div>
  );
}