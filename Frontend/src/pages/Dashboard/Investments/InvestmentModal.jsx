import { useEffect, useState } from "react"
import { Plus, Pencil, Building2, Ticket, Hash, IndianRupee, Calendar, CheckCircle2, X } from "lucide-react"
import {
  sanitizeFinancialInput,
  validateFinancialAmount,
  validateTextLength,
  MAX_NAME_LENGTH,
  MAX_NOTE_LENGTH,
  MAX_FINANCIAL_INT_DIGITS,
} from "../../../utils/financialValidation.js"

const ASSET_TYPES = [
  { id: "STOCKS", label: "Stocks" },
  { id: "MUTUAL_FUNDS", label: "Mutual Funds" },
  { id: "SIPS", label: "SIP" },
  { id: "ETFS", label: "ETF" },
]

export default function InvestmentModal({ open, mode, initial, onClose, onSave }) {
  const isEdit = mode === "edit"
  const [form, setForm] = useState({
    assetType: "STOCKS",
    ticker: "",
    companyName: "",
    quantity: "",
    purchasePrice: "",
    purchaseDate: "",
    brokerName: "",
    notes: "",
  })
  const [error, setError] = useState("")

  useEffect(() => {
    if (!open) return
    const today = new Date().toISOString().slice(0, 10)
    setForm(
      initial
        ? {
            assetType: initial.assetType || "STOCKS",
            ticker: initial.ticker || "",
            companyName: initial.companyName || "",
            quantity: String(initial.quantity ?? ""),
            purchasePrice: String(initial.purchasePrice ?? ""),
            purchaseDate: initial.purchaseDate ? String(initial.purchaseDate) : today,
            brokerName: initial.brokerName || "",
            notes: initial.notes || "",
          }
        : {
            assetType: "STOCKS",
            ticker: "",
            companyName: "",
            quantity: "",
            purchasePrice: "",
            purchaseDate: today,
            brokerName: "",
            notes: "",
          },
    )
    setError("")
  }, [open, initial])

  if (!open) return null

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const submit = (e) => {
    e.preventDefault()

    const tickerVal = validateTextLength(form.ticker, 50, "Stock ticker", true)
    if (!tickerVal.isValid) {
      setError(tickerVal.error)
      return
    }

    const companyVal = validateTextLength(form.companyName, 150, "Company name", true)
    if (!companyVal.isValid) {
      setError(companyVal.error)
      return
    }

    const qtyVal = validateFinancialAmount(form.quantity, {
      fieldName: "Quantity",
      min: 0.0001,
      minError: "Quantity must be a positive number greater than 0.",
    })
    if (!qtyVal.isValid) {
      setError(qtyVal.error)
      return
    }

    const priceVal = validateFinancialAmount(form.purchasePrice, {
      fieldName: "Purchase price",
      min: 0.01,
      minError: "Purchase price must be a positive number greater than 0.",
    })
    if (!priceVal.isValid) {
      setError(priceVal.error)
      return
    }

    if (!form.purchaseDate) {
      setError("Please select a purchase date.")
      return
    }

    const brokerVal = validateTextLength(form.brokerName, MAX_NAME_LENGTH, "Broker name", false)
    if (!brokerVal.isValid) {
      setError(brokerVal.error)
      return
    }

    const notesVal = validateTextLength(form.notes, MAX_NOTE_LENGTH, "Notes", false)
    if (!notesVal.isValid) {
      setError(notesVal.error)
      return
    }

    onSave({
      assetType: form.assetType,
      ticker: form.ticker.trim().toUpperCase(),
      companyName: form.companyName.trim(),
      quantity: qtyVal.numValue,
      purchasePrice: priceVal.numValue,
      purchaseDate: form.purchaseDate,
      brokerName: form.brokerName.trim() || null,
      notes: form.notes.trim() || null,
    })
  }

  const title = isEdit ? "Edit Holding" : "Add Investment Holding"
  const TitleIcon = isEdit ? Pencil : Plus

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}>
      <div style={{ width: "100%", maxWidth: "500px", background: "#0d1117", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "16px", padding: "24px", color: "#fff", boxShadow: "0 20px 40px rgba(0,0,0,0.5)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ width: "36px", height: "36px", borderRadius: "10px", background: "rgba(47,107,255,0.15)", color: "#2f6bff", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <TitleIcon size={18} />
            </span>
            <h2 style={{ fontSize: "18px", fontWeight: "600", margin: 0 }}>{title}</h2>
          </div>
          <button style={{ background: "none", border: "none", color: "#8a94a6", cursor: "pointer" }} onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={submit} style={{ display: "grid", gap: "14px" }}>
          <div style={{ display: "flex", gap: "8px" }}>
            {ASSET_TYPES.map((a) => (
              <button
                key={a.id}
                type="button"
                style={{ flex: 1, padding: "8px 12px", borderRadius: "8px", border: form.assetType === a.id ? "1px solid #2f6bff" : "1px solid rgba(255,255,255,0.1)", background: form.assetType === a.id ? "rgba(47,107,255,0.2)" : "rgba(255,255,255,0.03)", color: form.assetType === a.id ? "#2f6bff" : "#8a94a6", fontSize: "13px", fontWeight: "600", cursor: "pointer" }}
                onClick={() => setForm((f) => ({ ...f, assetType: a.id }))}
              >
                {a.label}
              </button>
            ))}
          </div>

          <div>
            <label style={{ fontSize: "12px", color: "#8a94a6", display: "block", marginBottom: "4px" }}>Stock Ticker Symbol (e.g. RELIANCE.NS, TCS.NS, AAPL)</label>
            <div style={{ position: "relative" }}>
              <Ticket size={16} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "#8a94a6" }} />
              <input maxLength={50} style={{ width: "100%", padding: "10px 12px 10px 36px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", fontSize: "14px" }} placeholder="RELIANCE.NS" value={form.ticker} onChange={set("ticker")} required />
            </div>
          </div>

          <div>
            <label style={{ fontSize: "12px", color: "#8a94a6", display: "block", marginBottom: "4px" }}>Company / Asset Name</label>
            <div style={{ position: "relative" }}>
              <Building2 size={16} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "#8a94a6" }} />
              <input maxLength={150} style={{ width: "100%", padding: "10px 12px 10px 36px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", fontSize: "14px" }} placeholder="Reliance Industries" value={form.companyName} onChange={set("companyName")} required />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ fontSize: "12px", color: "#8a94a6", display: "block", marginBottom: "4px" }}>Quantity / Units</label>
              <div style={{ position: "relative" }}>
                <Hash size={16} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "#8a94a6" }} />
                <input maxLength={MAX_FINANCIAL_INT_DIGITS + 3} style={{ width: "100%", padding: "10px 12px 10px 36px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", fontSize: "14px" }} type="text" inputMode="decimal" placeholder="10" value={form.quantity} onChange={(e) => setForm((f) => ({ ...f, quantity: sanitizeFinancialInput(e.target.value, true) }))} required />
              </div>
            </div>

            <div>
              <label style={{ fontSize: "12px", color: "#8a94a6", display: "block", marginBottom: "4px" }}>Buy Price per Unit (₹)</label>
              <div style={{ position: "relative" }}>
                <IndianRupee size={16} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "#8a94a6" }} />
                <input maxLength={MAX_FINANCIAL_INT_DIGITS + 3} style={{ width: "100%", padding: "10px 12px 10px 36px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", fontSize: "14px" }} type="text" inputMode="decimal" placeholder="2500.00" value={form.purchasePrice} onChange={(e) => setForm((f) => ({ ...f, purchasePrice: sanitizeFinancialInput(e.target.value, true) }))} required />
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ fontSize: "12px", color: "#8a94a6", display: "block", marginBottom: "4px" }}>Purchase Date</label>
              <div style={{ position: "relative" }}>
                <Calendar size={16} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "#8a94a6" }} />
                <input style={{ width: "100%", padding: "10px 12px 10px 36px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", fontSize: "14px" }} type="date" value={form.purchaseDate} onChange={set("purchaseDate")} required />
              </div>
            </div>

            <div>
              <label style={{ fontSize: "12px", color: "#8a94a6", display: "block", marginBottom: "4px" }}>Broker Name (Optional)</label>
              <input maxLength={MAX_NAME_LENGTH} style={{ width: "100%", padding: "10px 12px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", fontSize: "14px" }} placeholder="Zerodha, Groww, etc." value={form.brokerName} onChange={set("brokerName")} />
            </div>
          </div>

          {error && <p style={{ color: "#ef4b5b", fontSize: "13px", margin: 0 }}>{error}</p>}

          <div style={{ display: "flex", gap: "12px", marginTop: "10px" }}>
            <button type="button" style={{ flex: 1, padding: "10px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)", background: "transparent", color: "#8a94a6", cursor: "pointer", fontWeight: "600" }} onClick={onClose}>
              Cancel
            </button>
            <button type="submit" style={{ flex: 2, padding: "10px", borderRadius: "8px", border: "none", background: "#2f6bff", color: "#fff", fontWeight: "600", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              <CheckCircle2 size={18} /> {isEdit ? "Update Holding" : "Save Holding"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
