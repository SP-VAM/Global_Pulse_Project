// Centralized mock data for GlobalPulse. In production this would come from an API layer.

export const marketIndices = [
  { id: "sensex", label: "SENSEX", value: "72,503.12", change: "+0.80%", positive: true },
  { id: "nifty", label: "NIFTY 50", value: "22,053.45", change: "+0.75%", positive: true },
  { id: "nasdaq", label: "NASDAQ", value: "18,680.12", change: "+1.10%", positive: true },
  { id: "usdinr", label: "USD / INR", value: "83.24", change: "-0.12%", positive: false },
]

// Compact square summary cards shown at the top of the dashboard.
export const summaryCards = [
  { id: "spending", label: "Monthly Spending", value: "₹48,200", change: "+4.2%", positive: false, icon: "Wallet", tone: "blue" },
  { id: "income", label: "Income", value: "₹92,000", change: "+1.8%", positive: true, icon: "TrendingUp", tone: "green" },
  { id: "budget", label: "Remaining Budget", value: "₹18,500", change: "-6.5%", positive: false, icon: "PieChart", tone: "amber" },
  { id: "savings", label: "Savings", value: "₹43,800", change: "+9.1%", positive: true, icon: "PiggyBank", tone: "green" },
]

// Market overview mini-index tile (Nifty 50 + status).
export const marketOverview = {
  status: "OPEN",
  indices: [
    { id: "nifty", label: "NIFTY 50", value: "25,130", change: "+0.85%", positive: true },
  ],
}

export const companies = [
  { id: "reliance", name: "Reliance Industries", ticker: "RELIANCE.NS", price: "₹2,945.30", change: "+2.45%", positive: true },
  { id: "hdfc", name: "HDFC Bank", ticker: "HDFCBANK.NS", price: "₹1,642.15", change: "-0.12%", positive: false },
  { id: "infosys", name: "Infosys", ticker: "INFY.NS", price: "₹1,568.40", change: "+1.82%", positive: true },
  { id: "tcs", name: "TCS", ticker: "TCS.NS", price: "₹3,921.75", change: "+0.95%", positive: true },
  { id: "infosys_dup", name: "Infosys", ticker: "INFY.NS", price: "₹1,568.40", change: "+1.82%", positive: true },
  { id: "tcs_dup", name: "TCS", ticker: "TCS.NS", price: "₹3,921.75", change: "+0.95%", positive: true },
]

export const topMovers = [
  { id: "reliance", name: "Reliance", ticker: "RELIANCE.NS", value: "2,947.65", change: "+2.31%", positive: true },
  { id: "tcs", name: "TCS", ticker: "TCS.NS", value: "3,915.40", change: "+1.85%", positive: true },
  { id: "hdfc", name: "HDFC Bank", ticker: "HDFCBANK.NS", value: "1,672.30", change: "-0.35%", positive: false },
  { id: "infosys", name: "Infosys", ticker: "INFY.NS", value: "1,456.20", change: "+1.25%", positive: true },
  { id: "wipro", name: "Wipro", ticker: "WIPRO.NS", value: "285.40", change: "+0.95%", positive: true },
  { id: "sbi", name: "State Bank of India", ticker: "SBIN.NS", value: "865.25", change: "+1.35%", positive: true },
]

export const sectors = [
  { id: "it", label: "IT Services", icon: "Laptop", status: "POSITIVE", tone: "positive", note: "Higher export revenue due to USD strength." },
  { id: "banking", label: "Banking", icon: "Landmark", status: "NEGATIVE", tone: "negative", note: "Pressure on liquidity and yield spreads." },
  { id: "auto", label: "Automobile", icon: "Car", status: "NEUTRAL", tone: "neutral", note: "Supply chain cost offset by festive demand." },
  { id: "pharma", label: "Pharma", icon: "Cross", status: "POSITIVE", tone: "positive", note: "Export-oriented growth benefits from FX gains." },
  { id: "energy", label: "Energy", icon: "Flame", status: "HIGH RISK", tone: "risk", note: "Rising import bill for crude and gas." },
]

// Full Nifty 50 constituents used by the "All Constituents" page.
export const constituents = [
  { name: "Reliance Industries", ticker: "RELIANCE", sector: "Energy", price: 2945.3, change: 2.45, mcap: "19.9L Cr" },
  { name: "Tata Consultancy Services", ticker: "TCS", sector: "IT", price: 3921.75, change: 0.95, mcap: "14.2L Cr" },
  { name: "HDFC Bank", ticker: "HDFCBANK", sector: "Banking", price: 1642.15, change: -0.12, mcap: "12.4L Cr" },
  { name: "ICICI Bank", ticker: "ICICIBANK", sector: "Banking", price: 1189.6, change: 0.64, mcap: "8.3L Cr" },
  { name: "Bharti Airtel", ticker: "BHARTIARTL", sector: "Telecom", price: 1584.9, change: 0.88, mcap: "9.1L Cr" },
  { name: "State Bank of India", ticker: "SBIN", sector: "Banking", price: 812.35, change: 1.12, mcap: "7.2L Cr" },
  { name: "Infosys", ticker: "INFY", sector: "IT", price: 1568.4, change: 1.82, mcap: "6.5L Cr" },
  { name: "ITC", ticker: "ITC", sector: "FMCG", price: 462.15, change: -0.22, mcap: "5.8L Cr" },
  { name: "Hindustan Unilever", ticker: "HINDUNILVR", sector: "FMCG", price: 2415.2, change: -0.45, mcap: "5.7L Cr" },
  { name: "Larsen & Toubro", ticker: "LT", sector: "Infra", price: 3612.4, change: 1.34, mcap: "4.9L Cr" },
  { name: "Axis Bank", ticker: "AXISBANK", sector: "Banking", price: 1175.5, change: 0.42, mcap: "3.6L Cr" },
  { name: "Kotak Mahindra Bank", ticker: "KOTAKBANK", sector: "Banking", price: 1780.2, change: 0.15, mcap: "3.5L Cr" },
  { name: "HCL Technologies", ticker: "HCLTECH", sector: "IT", price: 1540.8, change: 1.2, mcap: "4.1L Cr" },
  { name: "Bajaj Finance", ticker: "BAJFINANCE", sector: "Banking", price: 6890.0, change: 0.75, mcap: "4.2L Cr" },
  { name: "Sun Pharmaceutical", ticker: "SUNPHARMA", sector: "Pharma", price: 1620.4, change: 1.45, mcap: "3.8L Cr" },
  { name: "Mahindra & Mahindra", ticker: "M&M", sector: "Auto", price: 2840.6, change: 2.1, mcap: "3.5L Cr" },
  { name: "Maruti Suzuki India", ticker: "MARUTI", sector: "Auto", price: 12450.0, change: 0.9, mcap: "3.9L Cr" },
  { name: "Tata Motors", ticker: "TATAMOTORS", sector: "Auto", price: 985.3, change: 1.65, mcap: "3.6L Cr" },
  { name: "NTPC", ticker: "NTPC", sector: "Energy", price: 395.2, change: 0.55, mcap: "3.8L Cr" },
  { name: "Oil & Natural Gas Corp", ticker: "ONGC", sector: "Energy", price: 310.4, change: -0.3, mcap: "3.9L Cr" },
  { name: "UltraTech Cement", ticker: "ULTRACEMCO", sector: "Infra", price: 10850.0, change: 0.8, mcap: "3.1L Cr" },
  { name: "Power Grid Corp", ticker: "POWERGRID", sector: "Energy", price: 325.1, change: 0.4, mcap: "3.0L Cr" },
  { name: "Titan Company", ticker: "TITAN", sector: "FMCG", price: 3420.5, change: -0.6, mcap: "3.0L Cr" },
  { name: "Adani Enterprises", ticker: "ADANIENT", sector: "Infra", price: 3150.0, change: 1.8, mcap: "3.6L Cr" },
  { name: "Adani Ports & SEZ", ticker: "ADANIPORTS", sector: "Infra", price: 1380.4, change: 1.25, mcap: "2.9L Cr" },
  { name: "Coal India", ticker: "COALINDIA", sector: "Energy", price: 485.6, change: 0.7, mcap: "2.9L Cr" },
  { name: "Tata Steel", ticker: "TATASTEEL", sector: "Infra", price: 165.4, change: -0.85, mcap: "2.1L Cr" },
  { name: "Wipro", ticker: "WIPRO", sector: "IT", price: 495.2, change: 0.95, mcap: "2.6L Cr" },
  { name: "Asian Paints", ticker: "ASIANPAINT", sector: "FMCG", price: 2890.3, change: -0.4, mcap: "2.7L Cr" },
  { name: "Siemens India", ticker: "SIEMENS", sector: "Infra", price: 7240.0, change: 1.5, mcap: "2.5L Cr" },
  { name: "JSW Steel", ticker: "JSWSTEEL", sector: "Infra", price: 910.2, change: -0.15, mcap: "2.2L Cr" },
  { name: "Grasim Industries", ticker: "GRASIM", sector: "Infra", price: 2650.0, change: 0.65, mcap: "1.8L Cr" },
  { name: "Tech Mahindra", ticker: "TECHM", sector: "IT", price: 1420.8, change: 1.1, mcap: "1.4L Cr" },
  { name: "Hindalco Industries", ticker: "HINDALCO", sector: "Infra", price: 645.3, change: 0.45, mcap: "1.4L Cr" },
  { name: "LTIMindtree", ticker: "LTIM", sector: "IT", price: 5120.0, change: 0.85, mcap: "1.5L Cr" },
  { name: "Bajaj Finserv", ticker: "BAJAJFINSV", sector: "Banking", price: 1590.2, change: 0.35, mcap: "2.5L Cr" },
  { name: "Cipla", ticker: "CIPLA", sector: "Pharma", price: 1495.0, change: 0.95, mcap: "1.2L Cr" },
  { name: "Dr. Reddy's Labs", ticker: "DRREDDY", sector: "Pharma", price: 6450.0, change: 0.5, mcap: "1.1L Cr" },
  { name: "SBI Life Insurance", ticker: "SBILIFE", sector: "Banking", price: 1680.4, change: 0.75, mcap: "1.7L Cr" },
  { name: "Britannia Industries", ticker: "BRITANNIA", sector: "FMCG", price: 5340.0, change: -0.2, mcap: "1.3L Cr" },
  { name: "IndusInd Bank", ticker: "INDUSINDBK", sector: "Banking", price: 1410.5, change: -0.65, mcap: "1.1L Cr" },
  { name: "Apollo Hospitals", ticker: "APOLLOHOSP", sector: "Pharma", price: 6280.0, change: 1.4, mcap: "0.9L Cr" },
  { name: "Eicher Motors", ticker: "EICHERMOT", sector: "Auto", price: 4650.0, change: 0.8, mcap: "1.2L Cr" },
  { name: "Divi's Laboratories", ticker: "DIVISLAB", sector: "Pharma", price: 4520.0, change: 0.6, mcap: "1.2L Cr" },
  { name: "Trent", ticker: "TRENT", sector: "FMCG", price: 6890.0, change: 2.85, mcap: "2.4L Cr" },
  { name: "Shriram Finance", ticker: "SHRIRAMFIN", sector: "Banking", price: 2780.0, change: 1.15, mcap: "1.0L Cr" },
  { name: "Hero MotoCorp", ticker: "HEROMOTOCO", sector: "Auto", price: 5240.0, change: 0.55, mcap: "1.0L Cr" },
  { name: "Bharat Petroleum", ticker: "BPCL", sector: "Energy", price: 320.5, change: -0.4, mcap: "1.4L Cr" },
  { name: "HDFC Life Insurance", ticker: "HDFCLIFE", sector: "Banking", price: 685.2, change: 0.3, mcap: "1.5L Cr" },
  { name: "Tata Consumer Products", ticker: "TATACONSUM", sector: "FMCG", price: 1140.0, change: 0.25, mcap: "1.1L Cr" },
]

export const sparklines = {
  reliance: [15, 32, 28, 68, 92],
  hdfc: [12, 25, 42, 65, 85],
  infosys: [14, 28, 48, 60, 88],
  tcs: [10, 20, 35, 58, 90],
  wipro: [12, 24, 38, 55, 82],
  icici: [10, 22, 40, 62, 86],
}

export const indexSparklines = {
  sensex: [30, 45, 38, 55, 70],
  nifty: [28, 40, 52, 66, 80],
  nasdaq: [20, 35, 50, 64, 84],
  usdinr: [72, 68, 60, 52, 44],
}
