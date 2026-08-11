export const NIFTY_COMPANIES = [
  { symbol: "RELIANCE", name: "Reliance Industries Ltd", price: 2945.30, change: 2.45, prevClose: 2874.85, volume: "4.2M", open: 2880.00, high: 2955.00, low: 2870.00, lastUpdated: "Today 15:30 IST" },
  { symbol: "TCS", name: "Tata Consultancy Services", price: 3921.75, change: 0.95, prevClose: 3884.85, volume: "1.8M", open: 3890.00, high: 3935.00, low: 3880.00, lastUpdated: "Today 15:30 IST" },
  { symbol: "HDFCBANK", name: "HDFC Bank Ltd", price: 1642.15, change: -0.12, prevClose: 1644.12, volume: "6.5M", open: 1645.00, high: 1655.00, low: 1638.00, lastUpdated: "Today 15:30 IST" },
  { symbol: "INFY", name: "Infosys Ltd", price: 1568.40, change: 1.82, prevClose: 1540.36, volume: "3.1M", open: 1545.00, high: 1575.00, low: 1540.00, lastUpdated: "Today 15:30 IST" },
  { symbol: "ICICIBANK", name: "ICICI Bank Ltd", price: 1189.60, change: 0.64, prevClose: 1182.03, volume: "5.2M", open: 1184.00, high: 1195.00, low: 1180.00, lastUpdated: "Today 15:30 IST" },
  { symbol: "WIPRO", name: "Wipro Ltd", price: 542.80, change: 2.21, prevClose: 531.06, volume: "2.4M", open: 532.00, high: 546.00, low: 530.00, lastUpdated: "Today 15:30 IST" },
  { symbol: "SBIN", name: "State Bank of India", price: 812.35, change: 1.12, prevClose: 803.35, volume: "7.9M", open: 805.00, high: 816.00, low: 802.00, lastUpdated: "Today 15:30 IST" },
  { symbol: "TATAMOTORS", name: "Tata Motors Ltd", price: 1024.30, change: 3.12, prevClose: 993.30, volume: "8.1M", open: 995.00, high: 1030.00, low: 990.00, lastUpdated: "Today 15:30 IST" },
];

export const DATE_RANGES = [
  { label: "1 Month", value: "1M" },
  { label: "6 Months", value: "6M" },
  { label: "1 Year", value: "1Y" },
  { label: "5 Years", value: "5Y" },
];

export function getOverviewChartData(symbol, range) {
  const dates = [
    "Jul 2025", "Aug 2025", "Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025",
    "Jan 2026", "Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026", "Jun 2026"
  ];

  const priceValues = [1190, 1420, 1495, 1340, 1079, 1070, 1090, 1460, 1320, 1120, 1080, 1060, 1330];
  const sma20Values = [1140, 1220, 1365, 1340, 1150, 1100, 1120, 1310, 1340, 1160, 1090, 1050, 1180];
  const sma50Values = [1110, 1180, 1260, 1270, 1184, 1140, 1120, 1250, 1280, 1180, 1150, 1130, 1165];
  const sma200Values = [1060, 1100, 1140, 1155, 1143, 1130, 1145, 1170, 1200, 1190, 1175, 1160, 1170];
  const volumeValues = [2400, 4200, 5100, 3800, 2900, 2100, 2800, 4900, 4100, 2600, 2200, 2000, 3900];

  return dates.map((date, idx) => ({
    date,
    price: priceValues[idx % priceValues.length],
    sma20: sma20Values[idx % sma20Values.length],
    sma50: sma50Values[idx % sma50Values.length],
    sma200: sma200Values[idx % sma200Values.length],
    volume: volumeValues[idx % volumeValues.length],
  }));
}

export function getTechnicalData(symbol, range) {
  const dates = [
    "Jul 2025", "Aug 2025", "Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025",
    "Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026", "Jun 2026"
  ];
  const basePrice = NIFTY_COMPANIES.find(c => c.symbol === symbol)?.price || 2500;

  const chartData = dates.map((date, idx) => {
    const factor = 1 + (idx - dates.length / 2) * 0.005 + (Math.cos(idx) * 0.02);
    const price = Math.round(basePrice * factor * 100) / 100;
    const rsi = Math.round(40 + Math.sin(idx * 0.5) * 28);
    const macd = Math.round((Math.sin(idx) * 15) * 100) / 100;
    const signal = Math.round((Math.sin(idx - 1) * 12) * 100) / 100;
    const histogram = Math.round((macd - signal) * 100) / 100;
    const middleBand = price;
    const upperBand = Math.round((price * 1.05) * 100) / 100;
    const lowerBand = Math.round((price * 0.95) * 100) / 100;

    return {
      date,
      price,
      rsi,
      macd,
      signal,
      histogram,
      upperBand,
      middleBand,
      lowerBand,
    };
  });

  const indicatorTable = [
    { indicator: "RSI (14)", value: "62.4", signal: "Strong Buy", details: "Momentum is bullish above 50 baseline" },
    { indicator: "MACD (12,26,9)", value: "18.5", signal: "Buy", details: "MACD line crossed above signal line" },
    { indicator: "SMA (20)", value: `₹${Math.round(basePrice * 0.98)}`, signal: "Buy", details: "Price trading above 20-day average" },
    { indicator: "SMA (50)", value: `₹${Math.round(basePrice * 0.96)}`, signal: "Strong Buy", details: "Price trading above 50-day average" },
    { indicator: "Bollinger Bands", value: "Band Expansion", signal: "Neutral", details: "Price near upper boundary" },
    { indicator: "Stochastic (14,3,3)", value: "78.2", signal: "Overbought", details: "Approaching upper threshold" },
  ];

  return { chartData, indicatorTable };
}

export function getMLPredictionData(symbol) {
  const currentPrice = NIFTY_COMPANIES.find(c => c.symbol === symbol)?.price || 2500;

  const livePrediction = {
    signal: "STRONG BULLISH",
    bullish: 82.5,
    bearish: 17.5,
    expectedReturn: "+6.8%",
    coreNewsSentiment: "0.78 (Positive)",
    confidence: 88.4,
    influencingNews: [
      { title: `${symbol} posts strong Q3 earnings beating consensus estimates by 12%`, sourceDate: "Livemint • 2h ago", sentiment: "POSITIVE", confidence: "94%" },
      { title: `Analysts upgrade ${symbol} target price following robust expansion plans`, sourceDate: "Economic Times • 5h ago", sentiment: "POSITIVE", confidence: "89%" },
      { title: `Foreign Institutional Investors increase stake in ${symbol} sector`, sourceDate: "Moneycontrol • 1d ago", sentiment: "POSITIVE", confidence: "85%" },
    ],
  };

  const marketPrediction = {
    confidence: 88.4,
    probUp: 82.5,
    probDown: 17.5,
  };

  const predictionVsActual = Array.from({ length: 12 }).map((_, idx) => {
    const actual = Math.round(currentPrice * (1 + (idx - 8) * 0.006) * 100) / 100;
    const predicted = Math.round((actual * (1 + (Math.sin(idx) * 0.004))) * 100) / 100;
    return {
      date: `Month ${idx + 1}`,
      actual,
      predicted,
    };
  });

  const featureImportance = [
    { feature: "News Sentiment Score", importance: 0.32 },
    { feature: "RSI Momentum", importance: 0.24 },
    { feature: "SMA 20/50 Crossover", importance: 0.18 },
    { feature: "Quarterly Revenue Growth", importance: 0.15 },
    { feature: "Volume Spikes", importance: 0.11 },
  ];

  return { livePrediction, marketPrediction, predictionVsActual, featureImportance };
}

export function getNewsSentimentData(symbol) {
  return {
    score: "+0.78 (Bullish)",
    articlesTraced: 48,
    positive: 38,
    negative: 10,
    newsList: [
      {
        id: 1,
        title: `${symbol} reports record operating margins in latest fiscal quarter`,
        sentiment: "POSITIVE",
        confidence: "95%",
        sourceDate: "Reuters • 3 hours ago",
        excerpt: "The company reported higher-than-expected revenue driven by foreign order wins and improved cost optimization.",
      },
      {
        id: 2,
        title: `Strategic partnership announced by ${symbol} for green energy transition`,
        sentiment: "POSITIVE",
        confidence: "88%",
        sourceDate: "CNBC TV18 • 6 hours ago",
        excerpt: "Key alliance signed with global technology leaders to accelerate sustainable manufacturing goals.",
      },
      {
        id: 3,
        title: `Minor supply chain delays noticed in ${symbol} regional distribution hubs`,
        sentiment: "NEUTRAL",
        confidence: "65%",
        sourceDate: "Business Standard • 1 day ago",
        excerpt: "Management confirmed logistics adjustments are underway and full normalization is expected within two weeks.",
      },
    ],
  };
}

export function getPredictionHistoryData(symbol) {
  const basePrice = NIFTY_COMPANIES.find(c => c.symbol === symbol)?.price || 2500;
  return [
    { date: "2026-07-28", symbol, signal: "BUY", initialPrice: Math.round(basePrice * 0.94), targetPrice: Math.round(basePrice * 0.98), actualPrice: Math.round(basePrice * 0.985), accuracy: "98.8%", status: "SUCCESS" },
    { date: "2026-07-14", symbol, signal: "BUY", initialPrice: Math.round(basePrice * 0.90), targetPrice: Math.round(basePrice * 0.95), actualPrice: Math.round(basePrice * 0.948), accuracy: "97.5%", status: "SUCCESS" },
    { date: "2026-06-30", symbol, signal: "STRONG BUY", initialPrice: Math.round(basePrice * 0.86), targetPrice: Math.round(basePrice * 0.91), actualPrice: Math.round(basePrice * 0.915), accuracy: "99.2%", status: "SUCCESS" },
    { date: "2026-06-15", symbol, signal: "BUY", initialPrice: Math.round(basePrice * 0.84), targetPrice: Math.round(basePrice * 0.88), actualPrice: Math.round(basePrice * 0.875), accuracy: "96.4%", status: "SUCCESS" },
  ];
}
