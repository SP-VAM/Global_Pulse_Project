// Compact Abstract UI Visualizations for GlobalPulse Feature Cards
// High-performance SVG graphics designed for dense, elegant 4-column card layouts.

export function WalletVisual() {
  return (
    <div className="abstract-visual-container abstract-visual-container--compact">
      <svg viewBox="0 0 240 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="abstract-svg">
        <defs>
          <linearGradient id="walletGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2f6bff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#4f83ff" stopOpacity="0.25" />
          </linearGradient>
          <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#2f6bff" stopOpacity="0.1" />
            <stop offset="50%" stopColor="#00f0ff" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#2f6bff" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        <rect x="10" y="10" width="220" height="60" rx="8" fill="rgba(20, 26, 42, 0.45)" stroke="rgba(255, 255, 255, 0.1)" strokeWidth="1" />
        <rect x="25" y="20" width="110" height="40" rx="6" fill="url(#walletGrad)" stroke="rgba(255, 255, 255, 0.15)" />
        <rect x="40" y="30" width="70" height="4" rx="2" fill="#ffffff" opacity="0.9" />
        <rect x="40" y="40" width="45" height="3" rx="1.5" fill="#8ba7ff" opacity="0.6" />

        <circle cx="180" cy="40" r="16" fill="rgba(47, 107, 255, 0.2)" stroke="#00f0ff" strokeWidth="1.2" />
        <path d="M172 40 H188 M180 32 V48" stroke="#00f0ff" strokeWidth="1.5" strokeLinecap="round" />

        <path d="M25 55 Q90 35 150 50 T215 30" fill="none" stroke="url(#lineGrad)" strokeWidth="2" />
      </svg>
    </div>
  );
}

export function InvestmentVisual() {
  return (
    <div className="abstract-visual-container abstract-visual-container--compact">
      <svg viewBox="0 0 240 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="abstract-svg">
        <defs>
          <linearGradient id="areaGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#2f6bff" stopOpacity="0.0" />
          </linearGradient>
          <linearGradient id="trendGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#2f6bff" />
            <stop offset="100%" stopColor="#00f0ff" />
          </linearGradient>
        </defs>

        <line x1="20" y1="25" x2="220" y2="25" stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
        <line x1="20" y1="50" x2="220" y2="50" stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />

        <path d="M 20 60 Q 70 55, 110 40 T 170 28 T 220 15 V 65 H 20 Z" fill="url(#areaGrad)" />
        <path d="M 20 60 Q 70 55, 110 40 T 170 28 T 220 15" fill="none" stroke="url(#trendGrad)" strokeWidth="2.5" strokeLinecap="round" />

        <circle cx="110" cy="40" r="3.5" fill="#2f6bff" stroke="#ffffff" strokeWidth="1.5" />
        <circle cx="170" cy="28" r="3.5" fill="#00f0ff" stroke="#ffffff" strokeWidth="1.5" />
        <circle cx="220" cy="15" r="4.5" fill="#00f0ff" />
      </svg>
    </div>
  );
}

export function EducationVisual() {
  return (
    <div className="abstract-visual-container abstract-visual-container--compact">
      <svg viewBox="0 0 240 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="abstract-svg">
        <defs>
          <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#4f83ff" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#0e1324" stopOpacity="0.8" />
          </linearGradient>
        </defs>

        <rect x="20" y="15" width="160" height="50" rx="6" fill="url(#cardGrad)" stroke="rgba(255, 255, 255, 0.08)" />
        <rect x="35" y="25" width="130" height="45" rx="6" fill="rgba(20, 28, 48, 0.6)" stroke="rgba(47, 107, 255, 0.3)" />

        <rect x="48" y="36" width="70" height="4" rx="2" fill="#ffffff" opacity="0.9" />
        <rect x="48" y="46" width="90" height="3" rx="1.5" fill="#6b8bff" opacity="0.6" />

        <polygon points="195,25 208,18 220,25 220,40 208,47 195,40" fill="rgba(0, 240, 255, 0.15)" stroke="#00f0ff" strokeWidth="1.2" />
        <circle cx="208" cy="32.5" r="3" fill="#00f0ff" />
      </svg>
    </div>
  );
}

export function GoalVisual() {
  return (
    <div className="abstract-visual-container abstract-visual-container--compact">
      <svg viewBox="0 0 240 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="abstract-svg">
        <defs>
          <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f0ff" />
            <stop offset="100%" stopColor="#2f6bff" />
          </linearGradient>
        </defs>

        <circle cx="60" cy="40" r="26" fill="none" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="5" />
        <circle
          cx="60"
          cy="40"
          r="26"
          fill="none"
          stroke="url(#ringGrad)"
          strokeWidth="5"
          strokeDasharray="163"
          strokeDashoffset="40"
          strokeLinecap="round"
          transform="rotate(-90 60 40)"
        />
        <text x="60" y="44" textAnchor="middle" fill="#ffffff" fontSize="11" fontFamily="Inter, sans-serif" fontWeight="800">75%</text>

        <rect x="120" y="22" width="90" height="18" rx="4" fill="rgba(20, 28, 48, 0.7)" stroke="rgba(0, 240, 255, 0.3)" />
        <circle cx="130" cy="31" r="3.5" fill="#00f0ff" />
        <rect x="142" y="29" width="50" height="4" rx="2" fill="#ffffff" opacity="0.8" />

        <rect x="120" y="44" width="90" height="18" rx="4" fill="rgba(20, 28, 48, 0.7)" stroke="rgba(255, 255, 255, 0.1)" />
        <circle cx="130" cy="53" r="3.5" fill="#2f6bff" />
        <rect x="142" y="51" width="38" height="4" rx="2" fill="#8ba7ff" opacity="0.6" />
      </svg>
    </div>
  );
}
