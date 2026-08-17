import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

/**
 * Generates and downloads a clean, professional PDF report of Income & Expense transactions.
 * Columns: Date | Category | Amount | Payment Method | Note
 */
export function generateExpensePDF(transactions = [], periodLabel = "", totals = { spending: 0, income: 0, savings: 0 }) {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "pt",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.getWidth();

  // Header Banner
  doc.setFillColor(15, 23, 42); // Slate dark #0f172a
  doc.rect(0, 0, pageWidth, 75, "F");

  // GlobalPulse Logo / Branding Text
  doc.setTextColor(56, 189, 248); // Sky blue #38bdf8
  doc.setFont("helvetica", "bold");
  doc.setFontSize(20);
  doc.text("GLOBALPULSE", 40, 36);

  doc.setTextColor(148, 163, 184); // Slate #94a3b8
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text("Financial Intelligence & Expense Tracker Report", 40, 52);

  // Period / Date on top right
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text(`Period: ${periodLabel || "All Records"}`, pageWidth - 40, 36, { align: "right" });

  doc.setTextColor(148, 163, 184);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(`Generated: ${new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}`, pageWidth - 40, 52, { align: "right" });

  // Summary Metrics Bar
  let startY = 95;
  const summaryBoxWidth = (pageWidth - 80 - 20) / 3;

  // Box 1: Total Income
  doc.setFillColor(240, 253, 244);
  doc.setDrawColor(187, 247, 208);
  doc.roundedRect(40, startY, summaryBoxWidth, 46, 6, 6, "FD");
  doc.setTextColor(22, 101, 52);
  doc.setFontSize(8.5);
  doc.setFont("helvetica", "bold");
  doc.text("TOTAL INCOME", 50, startY + 16);
  doc.setFontSize(12);
  doc.text(`+ Rs. ${Number(totals.income || 0).toLocaleString("en-IN")}`, 50, startY + 34);

  // Box 2: Total Spending
  doc.setFillColor(254, 242, 242);
  doc.setDrawColor(254, 202, 202);
  doc.roundedRect(40 + summaryBoxWidth + 10, startY, summaryBoxWidth, 46, 6, 6, "FD");
  doc.setTextColor(153, 27, 27);
  doc.setFontSize(8.5);
  doc.setFont("helvetica", "bold");
  doc.text("TOTAL SPENDING", 40 + summaryBoxWidth + 20, startY + 16);
  doc.setFontSize(12);
  doc.text(`- Rs. ${Number(totals.spending || 0).toLocaleString("en-IN")}`, 40 + summaryBoxWidth + 20, startY + 34);

  // Box 3: Net Savings
  doc.setFillColor(239, 246, 255);
  doc.setDrawColor(191, 219, 254);
  doc.roundedRect(40 + (summaryBoxWidth + 10) * 2, startY, summaryBoxWidth, 46, 6, 6, "FD");
  doc.setTextColor(30, 64, 175);
  doc.setFontSize(8.5);
  doc.setFont("helvetica", "bold");
  doc.text("NET SAVINGS", 40 + (summaryBoxWidth + 10) * 2 + 10, startY + 16);
  doc.setFontSize(12);
  doc.text(`Rs. ${Number(totals.savings || 0).toLocaleString("en-IN")}`, 40 + (summaryBoxWidth + 10) * 2 + 10, startY + 34);

  // Table Data Mapping: Date | Category | Amount | Payment Method | Note
  const tableData = transactions.map((t) => {
    const isExpense = t.type === "expense";
    const amountStr = `${isExpense ? "-" : "+"} Rs. ${Number(t.amount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
    const [y, m, d] = (t.date || "").split("-");
    const dateFormatted = y && m && d ? `${d}-${m}-${y}` : (t.date || "—");
    const categoryStr = isExpense ? (t.categoryName || t.category || "Expense") : "Income Deposit";
    const methodStr = t.method || "—";
    const noteStr = t.notes || "—";

    return [dateFormatted, categoryStr, amountStr, methodStr, noteStr];
  });

  autoTable(doc, {
    startY: startY + 60,
    head: [["Date", "Category", "Amount", "Payment Method", "Note"]],
    body: tableData.length > 0 ? tableData : [["—", "No transactions recorded", "—", "—", "—"]],
    margin: { left: 40, right: 40, bottom: 40 },
    theme: "grid",
    headStyles: {
      fillColor: [15, 23, 42],
      textColor: [255, 255, 255],
      fontSize: 9.5,
      fontStyle: "bold",
      halign: "left",
      cellPadding: 7,
    },
    bodyStyles: {
      fontSize: 9,
      textColor: [30, 41, 59],
      cellPadding: 6,
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252],
    },
    columnStyles: {
      0: { cellWidth: 75 }, // Date (DD-MM-YYYY)
      1: { cellWidth: 105 }, // Category
      2: { cellWidth: 95, fontStyle: "bold" }, // Amount
      3: { cellWidth: 100 }, // Payment Method
      4: { cellWidth: "auto" }, // Note
    },
    didDrawPage: function (data) {
      // Footer page numbering
      const str = `Page ${doc.internal.getNumberOfPages()}`;
      doc.setFontSize(8.5);
      doc.setTextColor(148, 163, 184);
      doc.text(str, pageWidth - 40, doc.internal.pageSize.getHeight() - 20, { align: "right" });
      doc.text("Confidential • GlobalPulse Financial Statement", 40, doc.internal.pageSize.getHeight() - 20);
    },
  });

  const filenameSafe = (periodLabel || "Statement").replace(/[^a-zA-Z0-9_-]/g, "_");
  doc.save(`GlobalPulse_Expense_Report_${filenameSafe}.pdf`);
}
