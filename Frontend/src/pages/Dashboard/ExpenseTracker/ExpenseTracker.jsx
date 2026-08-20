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
  Filter,
  Search,
  X,
  Download,
} from "lucide-react";

import {
  CATEGORY_MAP,
  CATEGORIES,
  formatINR,
  dateKey,
  prettyDate,
  monthLabel,
  addDaysISO,
  getCategoryKey,
} from "./data.js";
import {
  MIN_YEAR,
  MAX_YEAR,
  getAllowedYears,
  isPrevMonthDisabled,
  isNextMonthDisabled,
  getMinDateISO,
  getMaxDateISO,
} from "../../../utils/dateRules.js";
import {
  getExpenseSummary,
  createExpense,
  updateExpense,
  deleteExpense,
  createIncome,
  updateIncome,
  deleteIncome,
  saveBudget as saveBudgetApi,
  deleteBudget as deleteBudgetApi,
} from "../../../api/expenseApi.js";
import { generateExpensePDF } from "../../../utils/pdfExport.js";
import DownloadReportModal from "../../../components/layout/DownloadReportModal/DownloadReportModal.jsx";
import TransactionModal from "./TransactionModal.jsx";
import TransactionDetailModal from "./TransactionDetailModal.jsx";
import BudgetModal from "./BudgetModal.jsx";
import "./ExpenseTracker.css";

const WEEKDAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"];

export default function ExpenseTracker() {
  // Initialize view state dynamically using the actual system date (never hardcoded July 2026)
  const now = new Date();
  const initialDate = dateKey(now.getFullYear(), now.getMonth(), now.getDate());
  const [view, setView] = useState({ year: now.getFullYear(), month: now.getMonth() });
  const [selected, setSelected] = useState(initialDate);

  // Server state fetched from PostgreSQL API
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal dialog states
  const [txModal, setTxModal] = useState(null); // { mode, type, initial }
  const [detailTx, setDetailTx] = useState(null);
  const [budgetModal, setBudgetModal] = useState(null); // { mode, initial }
  const [showDownloadConfirm, setShowDownloadConfirm] = useState(false);

  // -------------------------------------------------------------
  // FRD-022: Filter & Search State
  // -------------------------------------------------------------
  const [filterKeyword, setFilterKeyword] = useState("");
  const [filterCategory, setFilterCategory] = useState("all");
  const [filterType, setFilterType] = useState("all"); // "all" | "expense" | "income"
  const [filterDateFrom, setFilterDateFrom] = useState(initialDate);
  const [filterDateTo, setFilterDateTo] = useState(addDaysISO(initialDate, 7));
  const [filterAmountMin, setFilterAmountMin] = useState("");
  const [filterAmountMax, setFilterAmountMax] = useState("");

  const handleSelectDate = (dateKeyStr) => {
    setSelected(dateKeyStr);
    setFilterDateFrom(dateKeyStr);
    setFilterDateTo(addDaysISO(dateKeyStr, 7));
  };

  const handleFilterDateFromChange = (val) => {
    if (!val) return;
    const yr = Number(val.slice(0, 4));
    if (yr && (yr < MIN_YEAR || yr > MAX_YEAR)) return;
    setFilterDateFrom(val);
    const minTo = addDaysISO(val, 7);
    setFilterDateTo((prevTo) => {
      if (!prevTo || prevTo < minTo) {
        return minTo;
      }
      return prevTo;
    });
  };

  const handleFilterDateToChange = (val) => {
    if (!val) return;
    const yr = Number(val.slice(0, 4));
    if (yr && (yr < MIN_YEAR || yr > MAX_YEAR)) return;
    const minTo = addDaysISO(filterDateFrom, 7);
    if (minTo && val < minTo) return;
    setFilterDateTo(val);
  };

  const handleResetFilters = () => {
    setFilterKeyword("");
    setFilterCategory("all");
    setFilterType("all");
    setFilterDateFrom(selected);
    setFilterDateTo(addDaysISO(selected, 7));
    setFilterAmountMin("");
    setFilterAmountMax("");
  };

  const isFiltering = Boolean(
    filterKeyword.trim() ||
    filterCategory !== "all" ||
    filterType !== "all" ||
    (filterDateFrom && filterDateFrom !== selected) ||
    (filterDateTo && filterDateTo !== addDaysISO(filterDateFrom, 7)) ||
    filterAmountMin !== "" ||
    filterAmountMax !== ""
  );

  // Ref for native month/year calendar picker
  const monthInputRef = useRef(null);

  const openNativeMonthPicker = () => {
    if (monthInputRef.current && monthInputRef.current.showPicker) {
      monthInputRef.current.showPicker();
    }
  };

  const handleNativeMonthChange = (e) => {
    const val = e.target.value; // "YYYY-MM"
    if (!val) return;
    const [yStr, mStr] = val.split("-");
    const y = parseInt(yStr, 10);
    const m = parseInt(mStr, 10) - 1; // Convert 1-indexed string to 0-indexed JS month

    if (!isNaN(y) && !isNaN(m)) {
      if (y < MIN_YEAR || y > MAX_YEAR) return;
      setView({ year: y, month: m });
      const newSel = dateKey(y, m, 1);
      handleSelectDate(newSel);
    }
  };

  /**
   * Fetch complete monthly expense summary from FastAPI backend endpoint:
   * GET /api/v1/expenses/summary?year=Y&month=M
   */
  const loadSummary = useCallback(async (year, month, forceLoader = false) => {
    if (forceLoader || !summaryData) {
      setLoading(true);
    }
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
  }, [summaryData]);

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
      const rawCat = e.category?.categoryName || "Other";
      const catKey = getCategoryKey(rawCat);
      const catObj = CATEGORY_MAP[catKey] || { label: rawCat, color: "#8a94a6" };
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
        categoryName: catObj.label,
        method: e.paymentMethod || "UPI",
        notes: e.notes || "",
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
      const rawCat = b.category?.categoryName || "Other";
      const catKey = getCategoryKey(rawCat);
      const catInfo = CATEGORY_MAP[catKey] || { label: rawCat, color: "#4f83ff" };
      return {
        id: b.budgetId,
        rawId: b.budgetId,
        category: catKey,
        categoryName: catInfo.label,
        label: catInfo.label,
        limit: Number(b.budgetAmount) || 0,
        spent: spentByCatMap[catKey] || 0,
        notes: b.notes || "",
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

  /* ---------------------------------------------------------------------------
   * FRD-022: Multi-Criteria Filtered Transactions
   * Combines keyword, category, type, date range, and amount boundaries
   * --------------------------------------------------------------------------- */
  const filteredTransactions = useMemo(() => {
    return allTransactions.filter((t) => {
      // 1. Keyword search (case-insensitive across notes, method, categoryName)
      if (filterKeyword.trim()) {
        const kw = filterKeyword.toLowerCase().trim();
        const notesMatch = t.notes && t.notes.toLowerCase().includes(kw);
        const methodMatch = t.method && t.method.toLowerCase().includes(kw);
        const catMatch = t.categoryName && t.categoryName.toLowerCase().includes(kw);
        if (!notesMatch && !methodMatch && !catMatch) return false;
      }
      // 2. Transaction type filter
      if (filterType !== "all" && t.type !== filterType) {
        return false;
      }
      // 3. Date Range
      if (filterDateFrom && t.date < filterDateFrom) {
        return false;
      }
      if (filterDateTo && t.date > filterDateTo) {
        return false;
      }
      // 4. Amount Range
      if (filterAmountMin !== "" && !isNaN(Number(filterAmountMin))) {
        if (t.amount < Number(filterAmountMin)) return false;
      }
      if (filterAmountMax !== "" && !isNaN(Number(filterAmountMax))) {
        if (t.amount > Number(filterAmountMax)) return false;
      }
      return true;
    });
  }, [
    allTransactions,
    filterKeyword,
    filterType,
    filterDateFrom,
    filterDateTo,
    filterAmountMin,
    filterAmountMax,
  ]);

  const activeDisplayTxs = isFiltering ? filteredTransactions : dayTx;
  const activeDisplayTotal = useMemo(
    () => activeDisplayTxs.reduce((s, t) => s + (t.type === "expense" ? t.amount : 0), 0),
    [activeDisplayTxs]
  );

  const { selectedTxs, otherTxs } = useMemo(() => {
    if (filterCategory === "all") {
      return { selectedTxs: [], otherTxs: activeDisplayTxs };
    }
    const sel = activeDisplayTxs.filter((t) => t.category === filterCategory);
    const oth = activeDisplayTxs.filter((t) => t.category !== filterCategory);
    return { selectedTxs: sel, otherTxs: oth };
  }, [activeDisplayTxs, filterCategory]);

  const renderTransactionItem = (t, isSelectedExpense = false) => {
    const isExpense = t.type === "expense";
    const catObj = CATEGORY_MAP[t.category] || {};
    const IconComp = isExpense ? catObj.icon || Wallet : ArrowRightLeft;
    let rawTitle = isExpense
      ? (t.notes && String(t.notes).trim() ? String(t.notes).trim() : (catObj.label || t.categoryName || "Expense"))
      : (t.notes && String(t.notes).trim() ? String(t.notes).trim() : "Income Deposit");

    if (typeof rawTitle === "object" && rawTitle !== null) {
      rawTitle = rawTitle.notes || rawTitle.specify_expense || rawTitle.name || (catObj.label || "Expense");
    } else if (typeof rawTitle === "string" && rawTitle.trim().startsWith("{")) {
      try {
        const parsed = JSON.parse(rawTitle);
        rawTitle = parsed.notes || parsed.specify_expense || parsed.name || (catObj.label || "Expense");
      } catch (e) {}
    }
    const titleText = String(rawTitle);

    return (
      <div
        key={t.id}
        className="et-tx-item"
        style={
          isSelectedExpense
            ? {
                borderColor: "rgba(56, 189, 248, 0.4)",
                background: "rgba(56, 189, 248, 0.05)",
              }
            : undefined
        }
        onClick={() => setDetailTx(t)}
      >
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
          <div className="et-tx-item__title">{titleText}</div>
          <div className="et-tx-item__meta">
            {isExpense && (
              <span className="et-tx-item__badge">{catObj.label || t.categoryName || "Other"}</span>
            )}
            <span>{t.method}</span>
            <span>•</span>
            <span>{t.date}</span>
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
  };

  /* Sorted Budget Buckets by Risk (Highest % Spent First) */
  const sortedBudgets = useMemo(() => {
    return [...activeMonthBudgets].sort((a, b) => {
      const pctA = a.limit > 0 ? a.spent / a.limit : 0;
      const pctB = b.limit > 0 ? b.spent / b.limit : 0;
      return pctB - pctA;
    });
  }, [activeMonthBudgets]);

  /* Calendar Grid Computation (Dynamically sized to actual month rows) */
  const { cells, numRows } = useMemo(() => {
    const totalDays = new Date(view.year, view.month + 1, 0).getDate();
    const firstDayIndex = new Date(view.year, view.month, 1).getDay(); // 0 is Sun
    const startOffset = (firstDayIndex + 6) % 7; // Monday = 0
    const daysInMonth = totalDays;

    const out = [];
    for (let i = 0; i < startOffset; i++) out.push(null);
    for (let d = 1; d <= daysInMonth; d++) out.push(d);
    
    // Exact number of rows needed for this month (4, 5, or 6)
    const requiredRows = Math.ceil(out.length / 7);
    const targetLength = requiredRows * 7;
    while (out.length < targetLength) out.push(null);
    return { cells: out, numRows: requiredRows };
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
      if (dir < 0 && isPrevMonthDisabled(v.year, v.month)) return v;
      if (dir > 0 && isNextMonthDisabled(v.year, v.month)) return v;
      const newSel = dateKey(newYr, newMo, 1);
      handleSelectDate(newSel);
      return { year: newYr, month: newMo };
    });
  };

  /* ----- Backend Mutations ----- */
  const isSavingRef = useRef(false);

  const saveTx = async (payload) => {
    if (isSavingRef.current) return;
    try {
      isSavingRef.current = true;
      if (txModal?.mode === "edit" && txModal?.initial) {
        const rawId = txModal.initial.rawId || (typeof txModal.initial.id === "string" ? txModal.initial.id.replace(/^(exp_|inc_)/, "") : txModal.initial.id);
        if (txModal.type === "expense") {
          const catKey = getCategoryKey(payload.category);
          const catObj = CATEGORY_MAP[catKey];
          const categoryName = catObj ? catObj.label : "Other";
          await updateExpense(rawId, {
            amount: Number(payload.amount),
            expenseDate: payload.date,
            categoryName: categoryName,
            paymentMethod: payload.method || "UPI",
            notes: payload.notes || "",
          });
        } else {
          await updateIncome(rawId, {
            amount: Number(payload.amount),
            incomeDate: payload.date,
            paymentMethod: payload.method || "Salary",
            notes: payload.notes || "",
          });
        }
      } else {
        if (txModal?.type === "expense") {
          const catKey = getCategoryKey(payload.category);
          const catObj = CATEGORY_MAP[catKey];
          const categoryName = catObj ? catObj.label : "Other";
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
      }

      setTxModal(null);
      // Refetch authoritative backend summary
      await loadSummary(view.year, view.month);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("expense-updated"));
      }
    } catch (err) {
      console.error("[ExpenseTracker] Error saving transaction:", err);
      throw err;
    } finally {
      isSavingRef.current = false;
    }
  };

  const deleteTx = async (tx) => {
    if (!tx) return;
    try {
      const rawId = tx.rawId || (typeof tx.id === "string" ? tx.id.replace(/^(exp_|inc_)/, "") : tx.id);
      if (tx.type === "expense") {
        await deleteExpense(rawId);
      } else {
        await deleteIncome(rawId);
      }
      setDetailTx(null);
      // Refetch authoritative backend summary to update UI
      await loadSummary(view.year, view.month);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("expense-updated"));
      }
    } catch (err) {
      console.error("[ExpenseTracker] Error deleting transaction:", err);
      setError(err.message || "Failed to delete transaction.");
    }
  };

  const saveBudget = async (payload) => {
    try {
      const catObj = CATEGORY_MAP[payload.category];
      const categoryName = payload.category === "other" && payload.label ? payload.label : (catObj ? catObj.label : payload.category || "General");
      await saveBudgetApi({
        categoryName: categoryName,
        budgetAmount: Number(payload.limit),
        budgetMonth: view.month + 1,
        budgetYear: view.year,
      });

      setBudgetModal(null);
      await loadSummary(view.year, view.month);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("expense-updated"));
      }
    } catch (err) {
      console.error("[ExpenseTracker] Error saving budget:", err);
      setError(err.message || "Failed to save budget.");
      throw err;
    }
  };

  const handleDeleteBudget = async (budgetId) => {
    try {
      await deleteBudgetApi(budgetId);
      setBudgetModal(null);
      await loadSummary(view.year, view.month);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("expense-updated"));
      }
    } catch (err) {
      console.error("[ExpenseTracker] Error deleting budget:", err);
      setError(err.message || "Failed to delete budget.");
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
            className="goal-hero__btn-secondary et-download-btn"
            style={{ padding: "8px 12px", borderRadius: "10px", display: "inline-flex", alignItems: "center", justifyContent: "center" }}
            onClick={() => setShowDownloadConfirm(true)}
            title="Download Statement Report (PDF)"
            aria-label="Download PDF Report"
          >
            <Download size={16} />
          </button>

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

      {/* ------------------- FRD-017: BUDGET ALERT BANNER ------------------- */}
      {summaryData?.budgetAlerts && summaryData.budgetAlerts.length > 0 && (
        <div
          className={`et-budget-alert-banner ${
            summaryData.budgetAlerts.some((a) => a.alertType === "exceeded")
              ? "et-budget-alert-banner--exceeded"
              : ""
          }`}
        >
          {summaryData.budgetAlerts.map((alert, idx) => {
            const isExceeded = alert.alertType === "exceeded";
            return (
              <div
                key={idx}
                className={`et-budget-alert-item ${
                  isExceeded ? "et-budget-alert-item--exceeded" : "et-budget-alert-item--approaching"
                }`}
              >
                <AlertCircle size={15} />
                <span>
                  {isExceeded ? (
                    <strong>
                      ⚠️ {alert.categoryName} Budget Exceeded! ({alert.utilizationPct}% used — spent {formatINR(alert.spent)} of {formatINR(alert.limit)})
                    </strong>
                  ) : (
                    <span>
                      ⚡ <strong>{alert.categoryName} Budget Approaching Limit</strong> ({alert.utilizationPct}% used — spent {formatINR(alert.spent)} of {formatINR(alert.limit)})
                    </span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* ------------------- FRD-022: SEARCH & FILTER BAR ------------------- */}
      <div className="et-filter-section">
        <div className="et-filter-header">
          <div className="et-filter-header__title">
            <Filter size={16} />
            <span>Search & Filter Transactions</span>
            {isFiltering && (
              <span
                style={{
                  background: "rgba(56, 189, 248, 0.15)",
                  color: "#38bdf8",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  fontSize: "11px",
                  fontWeight: 700,
                }}
              >
                {filteredTransactions.length} results
              </span>
            )}
          </div>
          {isFiltering && (
            <div className="et-filter-header__actions">
              <button
                type="button"
                className="et-filter-btn-reset"
                onClick={handleResetFilters}
              >
                <X size={13} />
                <span>Clear Filter</span>
              </button>
            </div>
          )}
        </div>

        <div className="et-filter-grid">
          {/* Keyword Field */}
          <div className="et-filter-field">
            <span className="et-filter-label">Keyword</span>
            <div style={{ position: "relative" }}>
              <input
                type="text"
                className="et-filter-input"
                placeholder="Search notes, payment method..."
                value={filterKeyword}
                onChange={(e) => setFilterKeyword(e.target.value)}
                style={{ paddingLeft: "28px" }}
              />
              <Search
                size={14}
                style={{
                  position: "absolute",
                  left: "9px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#6b7385",
                }}
              />
            </div>
          </div>

          {/* Category Dropdown */}
          <div className="et-filter-field">
            <span className="et-filter-label">Category</span>
            <select
              className="et-filter-select"
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
            >
              <option value="all">All Categories</option>
              {CATEGORIES.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          {/* Transaction Type Dropdown */}
          <div className="et-filter-field">
            <span className="et-filter-label">Type</span>
            <select
              className="et-filter-select"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
            >
              <option value="all">All Types</option>
              <option value="expense">Expense (-)</option>
              <option value="income">Income (+)</option>
            </select>
          </div>

          {/* Date From */}
          <div className="et-filter-field">
            <span className="et-filter-label">Date From</span>
            <div
              style={{ position: "relative", cursor: "pointer" }}
              onClick={(e) => {
                const el = e.currentTarget.querySelector("input[type='date']");
                if (el && el.showPicker) el.showPicker();
              }}
            >
              <input
                type="date"
                className="et-filter-input"
                value={filterDateFrom}
                min={getMinDateISO()}
                max={getMaxDateISO()}
                onChange={(e) => handleFilterDateFromChange(e.target.value)}
                onKeyDown={(e) => e.preventDefault()}
                style={{
                  position: "absolute",
                  inset: 0,
                  opacity: 0,
                  cursor: "pointer",
                  width: "100%",
                  height: "100%",
                  zIndex: 2,
                }}
              />
              <div
                className="et-filter-input"
                style={{
                  display: "flex",
                  alignItems: "center",
                  color: filterDateFrom ? "var(--text, #f4f6fb)" : "var(--text-3, #6b7385)",
                  fontWeight: 600,
                  letterSpacing: "0.5px",
                  cursor: "pointer",
                  userSelect: "none",
                }}
              >
                {filterDateFrom ? (
                  (() => {
                    const [y, m, d] = filterDateFrom.split("-");
                    return y && m && d ? `${d}-${m}-${y}` : filterDateFrom;
                  })()
                ) : (
                  "DD-MM-YYYY"
                )}
              </div>
            </div>
          </div>

          {/* Date To */}
          <div className="et-filter-field">
            <span className="et-filter-label">Date To</span>
            <div
              style={{ position: "relative", cursor: "pointer" }}
              onClick={(e) => {
                const el = e.currentTarget.querySelector("input[type='date']");
                if (el && el.showPicker) el.showPicker();
              }}
            >
              <input
                type="date"
                className="et-filter-input"
                value={filterDateTo}
                min={addDaysISO(filterDateFrom, 7) || getMinDateISO()}
                max={getMaxDateISO()}
                onChange={(e) => handleFilterDateToChange(e.target.value)}
                onKeyDown={(e) => e.preventDefault()}
                style={{
                  position: "absolute",
                  inset: 0,
                  opacity: 0,
                  cursor: "pointer",
                  width: "100%",
                  height: "100%",
                  zIndex: 2,
                }}
              />
              <div
                className="et-filter-input"
                style={{
                  display: "flex",
                  alignItems: "center",
                  color: filterDateTo ? "var(--text, #f4f6fb)" : "var(--text-3, #6b7385)",
                  fontWeight: 600,
                  letterSpacing: "0.5px",
                  cursor: "pointer",
                  userSelect: "none",
                }}
              >
                {filterDateTo ? (
                  (() => {
                    const [y, m, d] = filterDateTo.split("-");
                    return y && m && d ? `${d}-${m}-${y}` : filterDateTo;
                  })()
                ) : (
                  "DD-MM-YYYY"
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ------------------- SECTION 3: MAIN 2-COLUMN EQUAL GRID ------------------- */}
      <div className="goal-main-grid">
        {/* LEFT COLUMN: Calendar Navigation Panel */}
        <div className="goal-panel et-cal-panel">
          <div className="goal-panel__head" style={{ gap: "8px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <CalendarIcon size={16} className="goal-panel__head-icon" />
              <select
                aria-label="Select month"
                className="et-cal__select"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "#ffffff",
                  borderRadius: "6px",
                  padding: "4px 8px",
                  fontSize: "13px",
                  fontWeight: "600",
                  cursor: "pointer",
                  outline: "none",
                }}
                value={view.month}
                onChange={(e) => {
                  const m = Number(e.target.value);
                  setView({ year: view.year, month: m });
                  handleSelectDate(dateKey(view.year, m, 1));
                }}
              >
                {[
                  "January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"
                ].map((name, idx) => (
                  <option key={name} value={idx} style={{ background: "#0f131f", color: "#fff" }}>
                    {name}
                  </option>
                ))}
              </select>

              <select
                aria-label="Select year"
                className="et-cal__select"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "#ffffff",
                  borderRadius: "6px",
                  padding: "4px 8px",
                  fontSize: "13px",
                  fontWeight: "600",
                  cursor: "pointer",
                  outline: "none",
                }}
                value={view.year}
                onChange={(e) => {
                  const y = Number(e.target.value);
                  setView({ year: y, month: view.month });
                  handleSelectDate(dateKey(y, view.month, 1));
                }}
              >
                {getAllowedYears().map((y) => (
                  <option key={y} value={y} style={{ background: "#0f131f", color: "#fff" }}>
                    {y}
                  </option>
                ))}
              </select>
            </div>

            <div className="et-cal__nav" style={{ marginLeft: "auto" }}>
              <button
                type="button"
                aria-label="Previous month"
                onClick={() => changeMonth(-1)}
                disabled={isPrevMonthDisabled(view.year, view.month)}
                style={{
                  opacity: isPrevMonthDisabled(view.year, view.month) ? 0.3 : 1,
                  cursor: isPrevMonthDisabled(view.year, view.month) ? "not-allowed" : "pointer",
                }}
              >
                <ChevronLeft size={16} />
              </button>
              <button
                type="button"
                aria-label="Next month"
                onClick={() => changeMonth(1)}
                disabled={isNextMonthDisabled(view.year, view.month)}
                style={{
                  opacity: isNextMonthDisabled(view.year, view.month) ? 0.3 : 1,
                  cursor: isNextMonthDisabled(view.year, view.month) ? "not-allowed" : "pointer",
                }}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          <div className="et-cal__weekdays">
            {WEEKDAYS.map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>

          <div
            className="et-cal__grid"
            style={{
              gridTemplateRows: `repeat(${numRows}, minmax(0, 1fr))`,
            }}
          >
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
                  onClick={() => handleSelectDate(key)}
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
            <h3 className="goal-panel__title">
              {isFiltering ? "Filtered Transactions" : "Transactions"}
            </h3>
            <span className="et-panel__tag">{activeDisplayTxs.length} items</span>
            <span className="et-tx__date-sub">
              {isFiltering ? "Matching search & filter criteria" : prettyDate(selected)}
            </span>
          </div>

          <div className="et-tx__list">
            {loading ? (
              <div className="et-skeleton-list">
                <div className="et-skeleton-bar" />
                <div className="et-skeleton-bar" />
              </div>
            ) : selectedTxs.length === 0 && otherTxs.length === 0 ? (
              <div className="et-empty-state">
                <p>
                  {isFiltering
                    ? "No transactions match your search / filter criteria."
                    : `No transactions recorded for ${prettyDate(selected)}.`}
                </p>
                {isFiltering ? (
                  <button
                    type="button"
                    className="et-empty-state__action-btn"
                    onClick={handleResetFilters}
                  >
                    Clear Filter
                  </button>
                ) : (
                  <button
                    type="button"
                    className="et-empty-state__action-btn"
                    onClick={() => setTxModal({ mode: "add", type: "expense" })}
                  >
                    + Add Expense for this date
                  </button>
                )}
              </div>
            ) : (
              <>
                {selectedTxs.length > 0 && (
                  <div style={{ marginBottom: otherTxs.length > 0 ? "10px" : "0" }}>
                    <div
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        color: "#38bdf8",
                        letterSpacing: "0.5px",
                        padding: "4px 8px 6px 8px",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <span>Selected Expense</span>
                      <span
                        style={{
                          fontSize: "10px",
                          background: "rgba(56, 189, 248, 0.15)",
                          color: "#38bdf8",
                          padding: "1px 6px",
                          borderRadius: "4px",
                        }}
                      >
                        {CATEGORY_MAP[filterCategory]?.label || filterCategory}
                      </span>
                    </div>
                    {selectedTxs.map((t) => renderTransactionItem(t, true))}
                  </div>
                )}

                {otherTxs.length > 0 && (
                  <div>
                    {selectedTxs.length > 0 && (
                      <div
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          color: "var(--text-3, #6b7385)",
                          letterSpacing: "0.5px",
                          padding: "8px 8px 6px 8px",
                          borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                          marginTop: "6px",
                        }}
                      >
                        Other Transactions
                      </div>
                    )}
                    {otherTxs.map((t) => renderTransactionItem(t, false))}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="et-tx__footer">
            <span>{isFiltering ? "Total Filtered Expenses" : "Total Spent Today"}</span>
            <strong>{formatINR(activeDisplayTotal)}</strong>
          </div>
        </div>
      </div>

      {/* ------------------- SECTION 4: LOWER 2-COLUMN EQUAL GRID ------------------- */}
      <div className="goal-main-grid" style={{ marginTop: "16px" }}>
        {/* LEFT COLUMN: Category Breakdown Panel */}
        <div className="goal-panel et-cat-panel">
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
                  <div
                    key={r.id}
                    className="et-cat-row"
                    style={{
                      cursor: "pointer",
                      borderColor: filterCategory === r.id ? "rgba(56, 189, 248, 0.5)" : undefined,
                      background: filterCategory === r.id ? "rgba(56, 189, 248, 0.08)" : undefined,
                    }}
                    onClick={() => setFilterCategory(filterCategory === r.id ? "all" : r.id)}
                    title={`Click to view ${r.label} transactions first`}
                  >
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
        <div className="goal-panel et-budget-panel">
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
                  className="et-empty-state__action-btn"
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
                const isApproaching = !isOver && pct >= 80;
                const catObj = CATEGORY_MAP[b.category] || {};
                const IconComp = catObj.icon || Wallet;

                return (
                  <div
                    key={b.id}
                    className={`et-budget-card ${
                      isOver
                        ? "et-budget-card--over"
                        : isApproaching
                        ? "et-budget-card--approaching"
                        : ""
                    }`}
                  >
                    <div className="et-budget-card__head">
                      <div className="et-budget-card__identity">
                        <div
                          className="et-budget-card__icon"
                          style={{
                            backgroundColor: isOver
                              ? "rgba(239, 68, 68, 0.15)"
                              : isApproaching
                              ? "rgba(245, 158, 11, 0.15)"
                              : `${catObj.color || "#4f83ff"}1f`,
                            color: isOver
                              ? "#ef4444"
                              : isApproaching
                              ? "#f59e0b"
                              : catObj.color || "#4f83ff",
                          }}
                        >
                          <IconComp size={15} />
                        </div>
                        <div>
                          <div className="et-budget-card__name">{catObj.label || b.categoryName || "Budget Category"}</div>
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
                        className={`et-budget-card__fill ${
                          isOver
                            ? "et-budget-card__fill--over"
                            : isApproaching
                            ? "et-budget-card__fill--approaching"
                            : ""
                        }`}
                        style={{
                          width: `${pct}%`,
                          backgroundColor: isOver
                            ? "#ef4444"
                            : isApproaching
                            ? "#f59e0b"
                            : catObj.color || "#4f83ff",
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
                      ) : isApproaching ? (
                        <span className="et-budget-card__tag et-budget-card__tag--approaching">
                          ⚡ Approaching limit ({pct}%)
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
          selectedMonthView={view}
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
          onDelete={(targetTx) => deleteTx(targetTx || detailTx)}
        />
      )}

      {budgetModal && (
        <BudgetModal
          open={Boolean(budgetModal)}
          mode={budgetModal.mode}
          initial={budgetModal.initial}
          existingBudgets={activeMonthBudgets}
          onClose={() => setBudgetModal(null)}
          onSave={saveBudget}
          onDelete={() => handleDeleteBudget(budgetModal.initial?.rawId || budgetModal.initial?.id)}
        />
      )}

      <DownloadReportModal
        open={showDownloadConfirm}
        onClose={() => setShowDownloadConfirm(false)}
        onConfirm={() => generateExpensePDF(allTransactions, monthLabel(view.year, view.month), totals)}
        periodLabel={monthLabel(view.year, view.month)}
      />
    </div>
  );
}