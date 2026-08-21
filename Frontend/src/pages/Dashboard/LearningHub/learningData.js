/**
 * ============================================================================
 * LEARNING HUB DATA SOURCE
 * ============================================================================
 * Contains 16 structured financial learning modules mapped with content-specific
 * local image assets and embedded YouTube video URLs with exact video durations.
 */
 
// Specific financial topic image assets
import riskImg from "./assets/risk.png";
import recessionImg from "./assets/recession.png";
import inflationImg from "./assets/inflation.png";
import stockMarketImg from "./assets/stock-market.png";
import gdpImg from "./assets/gdp.png";
import optionsImg from "./assets/options.png";
 
// Numerical learning asset fallbacks
import learning7 from "./assets/learning7.png";
import learning8 from "./assets/learning8.png";
import learning9 from "./assets/learning9.png";
import learning10 from "./assets/learning10.png";
import learning11 from "./assets/learning11.png";
import learning12 from "./assets/learning12.png";
import learning13 from "./assets/learning13.png";
import learning14 from "./assets/learning14.png";
import learning15 from "./assets/learning15.png";
 
/**
 * Array of 16 learning course objects for the 4x4 matrix grid.
 */
const learningData = [
  // --------------------------------------------------------------------------
  // ROW 1: MARKETS & ASSET ALLOCATION
  // --------------------------------------------------------------------------
  {
    id: 1,
    title: "Stock Market Basics",
    level: "Beginner",
    tag: "INTRO",
    duration: "48 min",
    durationSeconds: 2888,
    category: "Markets",
    ccAvailable: true,
    image: stockMarketImg,
    videoId: "oAv_drK8VAo",
    video: "https://youtu.be/oAv_drK8VAo?si=2EsP940ZVv-bmqag",
    embedUrl: "https://www.youtube.com/embed/oAv_drK8VAo?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Learn the fundamentals of stock exchanges, equity valuation, and trading."
  },
  {
    id: 2,
    title: "Advanced Risk Management",
    level: "Advanced",
    tag: "HEDGES · CAPITAL",
    duration: "1.3 hrs",
    durationSeconds: 4847,
    category: "Markets",
    ccAvailable: true,
    image: riskImg,
    videoId: "qN0-ltRAcV4",
    video: "https://youtu.be/qN0-ltRAcV4?si=zeYOrYsMFUtbnTWB",
    embedUrl: "https://www.youtube.com/embed/qN0-ltRAcV4?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Professional techniques for managing investment risk and capital preservation."
  },
  {
    id: 3,
    title: "Commodities & Hard Assets",
    level: "Advanced",
    tag: "HARD ASSETS",
    duration: "56 min",
    durationSeconds: 3385,
    category: "Markets",
    ccAvailable: true,
    image: learning12,
    videoId: "Fte-qredO_w",
    video: "https://youtu.be/Fte-qredO_w?si=DpXPiMHfo3j7Hh3v",
    embedUrl: "https://www.youtube.com/embed/Fte-qredO_w?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Crude oil, gold, agricultural futures, and supply chain dynamics."
  },
  {
    id: 4,
    title: "Forex Trading Mastery",
    level: "Intermediate",
    tag: "FX",
    duration: "7.2 hrs",
    durationSeconds: 26034,
    category: "Markets",
    ccAvailable: true,
    image: learning11,
    videoId: "16HQyH7mlgc",
    video: "https://youtu.be/16HQyH7mlgc?si=i3mBUt8G4R8cwBlL",
    embedUrl: "https://www.youtube.com/embed/16HQyH7mlgc?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Foreign exchange market structure, currency pairs, and macro drivers."
  },

  // --------------------------------------------------------------------------
  // ROW 2: MACROECONOMICS & POLICY
  // --------------------------------------------------------------------------
  {
    id: 5,
    title: "Understanding Inflation",
    level: "Beginner",
    tag: "BEGINNER",
    duration: "45 min",
    durationSeconds: 2727,
    category: "Macroeconomics",
    ccAvailable: true,
    image: inflationImg,
    videoId: "Fr8ua_1-9Zg",
    video: "https://youtu.be/Fr8ua_1-9Zg?si=W0gl6OJT0kJW_B6g",
    embedUrl: "https://www.youtube.com/embed/Fr8ua_1-9Zg?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Understand how purchasing power changes and why prices rise over time."
  },
  {
    id: 6,
    title: "What is GDP?",
    level: "Beginner",
    tag: "CONCEPT",
    duration: "1.1 hrs",
    durationSeconds: 3834,
    category: "Macroeconomics",
    ccAvailable: true,
    image: gdpImg,
    videoId: "2xXoiV1Whoo",
    video: "https://youtu.be/2xXoiV1Whoo?si=QrhsWs6gtRI1NKWS",
    embedUrl: "https://www.youtube.com/embed/2xXoiV1Whoo?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Learn how Gross Domestic Product measures national economic output and growth."
  },
  {
    id: 7,
    title: "Central Bank & Interest Rates",
    level: "Intermediate",
    tag: "POLICY",
    duration: "1.6 hrs",
    durationSeconds: 5653,
    category: "Macroeconomics",
    ccAvailable: true,
    image: learning8,
    videoId: "9xzQIXnkVj4",
    video: "https://youtu.be/9xzQIXnkVj4?si=q0fcLkYboo9B66iI",
    embedUrl: "https://www.youtube.com/embed/9xzQIXnkVj4?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Analyze interest rate decisions, central bank balance sheets, and monetary policy."
  },
  {
    id: 8,
    title: "Economic Recessions & Yields",
    level: "Advanced",
    tag: "CASE STUDY",
    duration: "48 min",
    durationSeconds: 2903,
    category: "Macroeconomics",
    ccAvailable: true,
    image: recessionImg,
    videoId: "H9DngtHhDlI",
    video: "https://youtu.be/H9DngtHhDlI?si=9rsp4RPM4WgHemh5",
    embedUrl: "https://www.youtube.com/embed/H9DngtHhDlI?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Understand recession cycles, yield curve inversion, and market behavior."
  },

  // --------------------------------------------------------------------------
  // ROW 3: DERIVATIVES & TRADING STRATEGIES
  // --------------------------------------------------------------------------
  {
    id: 9,
    title: "Intro to Futures & Options",
    level: "Beginner",
    tag: "INTRO",
    duration: "48 min",
    durationSeconds: 2888,
    category: "Derivatives",
    ccAvailable: true,
    image: learning15,
    videoId: "oAv_drK8VAo",
    video: "https://youtu.be/oAv_drK8VAo?si=2EsP940ZVv-bmqag",
    embedUrl: "https://www.youtube.com/embed/oAv_drK8VAo?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Introduction to derivative contracts, leverage, and basic hedging concepts."
  },
  {
    id: 10,
    title: "Option Greeks Explained",
    level: "Intermediate",
    tag: "EXPERT",
    duration: "35 min",
    durationSeconds: 2071,
    category: "Derivatives",
    ccAvailable: true,
    image: optionsImg,
    videoId: "Ca66fN3oP1U",
    video: "https://youtu.be/Ca66fN3oP1U?si=Q5QqZ0XgrJWc7xPN",
    embedUrl: "https://www.youtube.com/embed/Ca66fN3oP1U?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Master Delta, Gamma, Theta, Vega and implied volatility dynamics."
  },
  {
    id: 11,
    title: "Algo Trading & Backtesting",
    level: "Intermediate",
    tag: "TECH",
    duration: "38 min",
    durationSeconds: 2298,
    category: "Derivatives",
    ccAvailable: true,
    image: learning7,
    videoId: "bh8oQq3KY1k",
    video: "https://youtu.be/bh8oQq3KY1k?si=_1K5x88c4yQQBkvH",
    embedUrl: "https://www.youtube.com/embed/bh8oQq3KY1k?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Algorithmic strategies, quantitative backtesting, and automated execution."
  },
  {
    id: 12,
    title: "Derivatives & Portfolio Hedging",
    level: "Advanced",
    tag: "STRATEGY",
    duration: "1.3 hrs",
    durationSeconds: 4847,
    category: "Derivatives",
    ccAvailable: true,
    image: riskImg,
    videoId: "qN0-ltRAcV4",
    video: "https://youtu.be/qN0-ltRAcV4?si=zeYOrYsMFUtbnTWB",
    embedUrl: "https://www.youtube.com/embed/qN0-ltRAcV4?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Tail-risk protection, drawdown mitigation, and options hedging."
  },

  // --------------------------------------------------------------------------
  // ROW 4: DEFI & CRYPTO ASSETS
  // --------------------------------------------------------------------------
  {
    id: 13,
    title: "Crypto & Web3 Fundamentals",
    level: "Beginner",
    tag: "BEGINNER",
    duration: "29 min",
    durationSeconds: 1717,
    category: "DeFi & Crypto",
    ccAvailable: true,
    image: learning10,
    videoId: "W5AbWzMe8vs",
    video: "https://youtu.be/W5AbWzMe8vs?si=CZ7BMoaC2CAcYCatU",
    embedUrl: "https://www.youtube.com/embed/W5AbWzMe8vs?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Understand digital assets, asset allocation, and cryptocurrency basics."
  },
  {
    id: 14,
    title: "DeFi Protocols & Staking",
    level: "Intermediate",
    tag: "DEFI",
    duration: "29 min",
    durationSeconds: 1717,
    category: "DeFi & Crypto",
    ccAvailable: true,
    image: learning14,
    videoId: "W5AbWzMe8vs",
    video: "https://youtu.be/W5AbWzMe8vs?si=CZ7BMoaC2CAcYCatU",
    embedUrl: "https://www.youtube.com/embed/W5AbWzMe8vs?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Decentralized exchanges, liquidity pools, yield farming, and staking."
  },
  {
    id: 15,
    title: "Blockchain Economics & Architecture",
    level: "Advanced",
    tag: "CRYPTO",
    duration: "1.3 hrs",
    durationSeconds: 4678,
    category: "DeFi & Crypto",
    ccAvailable: true,
    image: learning9,
    videoId: "_eGNSuTBc60",
    video: "https://youtu.be/_eGNSuTBc60?si=5Rjsvul6l6klBQbS",
    embedUrl: "https://www.youtube.com/embed/_eGNSuTBc60?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Decentralized finance, tokenomics, and distributed ledger mechanics."
  },
  {
    id: 16,
    title: "Smart Contract Risk Analysis",
    level: "Advanced",
    tag: "SECURITY",
    duration: "35 min",
    durationSeconds: 2071,
    category: "DeFi & Crypto",
    ccAvailable: true,
    image: learning13,
    videoId: "Ca66fN3oP1U",
    video: "https://youtu.be/Ca66fN3oP1U?si=Q5QqZ0XgrJWc7xPN",
    embedUrl: "https://www.youtube.com/embed/Ca66fN3oP1U?autoplay=1&cc_load_policy=1&enablejsapi=1",
    description: "Auditing smart contracts, protocol security, and decentralized governance."
  }
];
 
export default learningData;