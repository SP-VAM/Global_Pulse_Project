import React from "react";
import { Target, ArrowRight, ShieldCheck, TrendingUp, PieChart } from "lucide-react";
import "./GoalsLanding.css";

export default function GoalsLanding({ onSetGoal }) {
  return (
    <div className="goals-landing card-appear">
      <div className="goals-landing__container">
        {/* Visual Illustration */}
        <div className="goals-landing__illustration">
          <div className="goals-landing__glow" />
          <svg
            className="goals-landing__svg"
            viewBox="0 0 320 260"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id="gRing" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" />
                <stop offset="50%" stopColor="#2f6bff" />
                <stop offset="100%" stopColor="#a855f7" />
              </linearGradient>
              <linearGradient id="gGold" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#f5a524" />
                <stop offset="100%" stopColor="#d97706" />
              </linearGradient>
              <linearGradient id="gGreen" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#2ec27e" />
                <stop offset="100%" stopColor="#059669" />
              </linearGradient>
              <filter id="glowEffect" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="8" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Background Grid Accent */}
            <circle cx="160" cy="130" r="110" stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="4 4" />
            <circle cx="160" cy="130" r="80" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />

            {/* Dual Glowing Ring Concept */}
            <circle
              cx="160"
              cy="130"
              r="75"
              stroke="url(#gRing)"
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray="400"
              strokeDashoffset="110"
              filter="url(#glowEffect)"
              opacity="0.95"
            />
            <circle
              cx="160"
              cy="130"
              r="95"
              stroke="url(#gGold)"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray="500"
              strokeDashoffset="260"
              opacity="0.85"
            />

            {/* Floating Asset Spheres/Badges */}
            <g transform="translate(60, 60)">
              <rect x="0" y="0" width="54" height="26" rx="13" fill="rgba(15, 23, 42, 0.85)" stroke="rgba(245, 165, 36, 0.4)" strokeWidth="1" />
              <circle cx="13" cy="13" r="6" fill="#f5a524" />
              <text x="24" y="17" fill="#f8fafc" fontSize="10" fontWeight="700">Gold</text>
            </g>

            <g transform="translate(205, 50)">
              <rect x="0" y="0" width="60" height="26" rx="13" fill="rgba(15, 23, 42, 0.85)" stroke="rgba(56, 189, 248, 0.4)" strokeWidth="1" />
              <circle cx="13" cy="13" r="6" fill="#38bdf8" />
              <text x="24" y="17" fill="#f8fafc" fontSize="10" fontWeight="700">Stocks</text>
            </g>

            <g transform="translate(195, 180)">
              <rect x="0" y="0" width="62" height="26" rx="13" fill="rgba(15, 23, 42, 0.85)" stroke="rgba(46, 194, 126, 0.4)" strokeWidth="1" />
              <circle cx="13" cy="13" r="6" fill="#2ec27e" />
              <text x="24" y="17" fill="#f8fafc" fontSize="10" fontWeight="700">Crypto</text>
            </g>

            {/* Center Icon */}
            <circle cx="160" cy="130" r="38" fill="rgba(15, 22, 40, 0.95)" stroke="rgba(255, 255, 255, 0.12)" strokeWidth="2" />
            <path
              d="M160 114v32M144 130h32"
              stroke="#38bdf8"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <circle cx="160" cy="130" r="10" stroke="#f5a524" strokeWidth="2" fill="none" />
          </svg>
        </div>

        {/* Text Content */}
        <div className="goals-landing__content">
          <h1 className="goals-landing__title">Set Your Financial Goal</h1>
          <p className="goals-landing__description">
            Build wealth with clarity. Define your target amount, allocate your investments across assets like Gold, Stocks, and Crypto, and track your progress in real-time.
          </p>

          {/* Primary CTA */}
          <button
            className="goals-landing__cta"
            onClick={onSetGoal}
            aria-label="Set Your Goal"
          >
            <span>Set Your Goal</span>
            <ArrowRight size={18} />
          </button>

          {/* Feature Highlights */}
          <div className="goals-landing__features">
            <div className="goals-landing__feature-item">
              <ShieldCheck size={16} className="goals-landing__feature-icon" />
              <span>Smart Tracking</span>
            </div>
            <div className="goals-landing__feature-item">
              <PieChart size={16} className="goals-landing__feature-icon" />
              <span>Asset Allocation</span>
            </div>
            <div className="goals-landing__feature-item">
              <TrendingUp size={16} className="goals-landing__feature-icon" />
              <span>Progress Analytics</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
