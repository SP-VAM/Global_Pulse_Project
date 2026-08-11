import { useState } from "react";
import {
  Zap,
  Sparkles,
  Check,
  X,
  Shield,
  TrendingUp,
  Cpu,
  Lock,
  Globe,
  Award,
  Clock,
  Users,
  Star,
  Send,
  CheckCircle,
  ArrowRight,
} from "lucide-react";

import traderDashboardImg from "../../../assets/images/trader_dashboard.png";
import "./Upgrade.css";

export default function Upgrade() {
  const [rating, setRating] = useState(5);
  const [hoverRating, setHoverRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [activePlan, setActivePlan] = useState("pro");

  const handleSubmitReview = (e) => {
    e.preventDefault();
    if (reviewText.trim()) {
      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        setReviewText("");
      }, 4000);
    }
  };

  return (
    <div className="upgrade-container">
      <div className="upgrade-bg-glow" />

      {/* Header Section */}
      <header className="upgrade-header">
        <div className="upgrade-badge">
          <Zap size={14} className="upgrade-badge-icon" />
          <span>GLOBALPULSE PRO</span>
        </div>
        <h1 className="upgrade-title">
          Elevate Your Trading & Investing{" "}
          <span className="upgrade-title-highlight">to Professional Levels</span>
        </h1>
        <p className="upgrade-subtitle">
          Get institutional-grade real-time signals, AI market predictions, unlimited watchlist tracking, and dedicated portfolio insights.
        </p>
      </header>

      {/* Main 3-Column Grid */}
      <div className="upgrade-main-grid">
        {/* Starter Plan */}
        <div className="upgrade-card plan-card">
          <div>
            <div className="plan-header-row">
              <div>
                <h3 className="plan-title">Starter</h3>
                <p className="plan-description">Essential market tracking</p>
              </div>
              <div className="plan-emblem">
                <Shield size={20} />
              </div>
            </div>

            <div className="plan-price-box">
              <span className="plan-currency">₹</span>
              <span className="plan-price">0</span>
              <span className="plan-period">/month</span>
            </div>

            <ul className="plan-features">
              <li className="feature-item">
                <span className="feature-icon check">
                  <Check size={12} />
                </span>
                <span>Live Indian & Global Indices</span>
              </li>
              <li className="feature-item">
                <span className="feature-icon check">
                  <Check size={12} />
                </span>
                <span>Up to 5 Watchlist Stocks</span>
              </li>
              <li className="feature-item">
                <span className="feature-icon check">
                  <Check size={12} />
                </span>
                <span>Basic Company Cards</span>
              </li>
              <li className="feature-item disabled">
                <span className="feature-icon cross">
                  <X size={12} />
                </span>
                <span>AI Market Predictions</span>
              </li>
              <li className="feature-item disabled">
                <span className="feature-icon cross">
                  <X size={12} />
                </span>
                <span>Advanced Technical Signals</span>
              </li>
            </ul>
          </div>

          <button
            className="plan-btn btn-current"
            onClick={() => setActivePlan("free")}
          >
            {activePlan === "free" ? "Current Plan" : "Downgrade to Starter"}
          </button>
        </div>

        {/* Pro Plan (Featured) */}
        <div className="upgrade-card plan-card plan-featured">
          <span className="popular-badge">MOST POPULAR</span>
          <div>
            <div className="plan-header-row">
              <div>
                <h3 className="plan-title">Pro Tier</h3>
                <p className="plan-description">Full access for serious traders</p>
              </div>
              <div className="plan-emblem">
                <Zap size={20} />
              </div>
            </div>

            <div className="plan-price-box">
              <span className="plan-currency">₹</span>
              <span className="plan-price">799</span>
              <span className="plan-period">/month</span>
            </div>

            <ul className="plan-features">
              <li className="feature-item">
                <span className="feature-icon active-check">
                  <Check size={12} />
                </span>
                <span className="highlight-text">All 50 Constituents Real-time Data</span>
              </li>
              <li className="feature-item">
                <span className="feature-icon active-check">
                  <Check size={12} />
                </span>
                <span className="highlight-text">AI Market Sentiment Signals</span>
              </li>
              <li className="feature-item">
                <span className="feature-icon active-check">
                  <Check size={12} />
                </span>
                <span>Unlimited Watchlists & Alerts</span>
              </li>
              <li className="feature-item">
                <span className="feature-icon active-check">
                  <Check size={12} />
                </span>
                <span>Expense & Goal Tracking Sync</span>
              </li>
              <li className="feature-item">
                <span className="feature-icon active-check">
                  <Check size={12} />
                </span>
                <span>Priority Customer Support</span>
              </li>
            </ul>
          </div>

          <button
            className={`plan-btn ${activePlan === "pro" ? "btn-current" : "btn-pro"}`}
            onClick={() => setActivePlan("pro")}
          >
            {activePlan === "pro" ? "Active Plan" : "Upgrade to Pro"}
          </button>
        </div>

        {/* Column 3: Stacked Feature Highlights */}
        <div className="upgrade-highlights-column">
          <div className="highlight-card">
            <div className="highlight-icon-box">
              <TrendingUp size={20} />
            </div>
            <div className="highlight-content">
              <h4>99.9% Real-Time Accuracy</h4>
              <p>Sub-millisecond data feeds direct from NSE & BSE servers.</p>
            </div>
          </div>

          <div className="highlight-card">
            <div className="highlight-icon-box">
              <Cpu size={20} />
            </div>
            <div className="highlight-content">
              <h4>AI Pattern Recognition</h4>
              <p>Predictive analytics for breakout stocks and sector rotation.</p>
            </div>
          </div>

          <div className="highlight-card">
            <div className="highlight-icon-box">
              <Lock size={20} />
            </div>
            <div className="highlight-content">
              <h4>Institutional Security</h4>
              <p>256-bit encryption with 2FA protection for portfolio data.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Trusted Logos Section */}
      <section className="upgrade-trusted-section">
        <h4 className="trusted-title">TRUSTED BY INVESTORS FROM LEADING FIRMS</h4>
        <div className="trusted-logos">
          <div className="logo-item">
            <Globe size={18} /> ZERODHA
          </div>
          <div className="logo-item">
            <TrendingUp size={18} /> GROWW
          </div>
          <div className="logo-item">
            <Shield size={18} /> ANGEL ONE
          </div>
          <div className="logo-item">
            <Zap size={18} /> UPSTOX
          </div>
          <div className="logo-item">
            <Award size={18} /> ICICI DIRECT
          </div>
        </div>
      </section>

      {/* Testimonial & Benefits Section */}
      <section className="upgrade-testimonial-section">
        <div className="testimonial-image-wrapper">
          <img
            src={traderDashboardImg}
            alt="GlobalPulse Pro Dashboard"
            className="testimonial-img"
          />
          <div className="floating-quote-card">
            <div className="quote-stars">
              {[...Array(5)].map((_, i) => (
                <Star key={i} size={14} fill="#f59e0b" stroke="#f59e0b" />
              ))}
            </div>
            <p className="quote-text">
              "GlobalPulse Pro transformed how I track Nifty 50 swings. The real-time signals paid for the subscription in week one!"
            </p>
            <div className="quote-user">
              <div className="user-avatar">RS</div>
              <div className="user-info">
                <span className="user-name">Rajesh Sharma</span>
                <span className="user-role">Full-Time Swing Trader</span>
              </div>
            </div>
          </div>
        </div>

        <div className="testimonial-benefits">
          <h3 className="benefits-title">Why 15,000+ traders upgraded to Pro</h3>

          <div className="benefit-item">
            <div className="benefit-icon-box">
              <Award size={20} />
            </div>
            <div className="benefit-info">
              <h4>Institutional Analytics</h4>
              <p>
                Access heatmaps, momentum scores, and institutional order flow metrics previously restricted to hedge funds.
              </p>
            </div>
          </div>

          <div className="benefit-item">
            <div className="benefit-icon-box">
              <Clock size={20} />
            </div>
            <div className="benefit-info">
              <h4>Instant Mobile & Desktop Alerts</h4>
              <p>
                Set custom trigger conditions and receive instant push and Telegram notifications.
              </p>
            </div>
          </div>

          <div className="benefit-item">
            <div className="benefit-icon-box">
              <Users size={20} />
            </div>
            <div className="benefit-info">
              <h4>Exclusive VIP Community</h4>
              <p>
                Join live daily market breakdown sessions with seasoned analysts and community discussions.
              </p>
            </div>
          </div>

          <a href="#testimonials" className="stories-link">
            Read all customer stories <ArrowRight size={16} className="arrow-icon" />
          </a>
        </div>
      </section>

      {/* Interactive Review Form Section */}
      <section className="upgrade-review-form-section">
        <h3 className="review-form-title">Share Your Feedback</h3>

        <div className="review-stars-interactive">
          {[1, 2, 3, 4, 5].map((star) => {
            const isFilled = star <= (hoverRating || rating);
            return (
              <button
                key={star}
                type="button"
                className={`star-btn ${isFilled ? "active" : ""}`}
                onClick={() => setRating(star)}
                onMouseEnter={() => setHoverRating(star)}
                onMouseLeave={() => setHoverRating(0)}
                aria-label={`Rate ${star} stars`}
              >
                <Star
                  className="star-icon"
                  size={26}
                  fill={isFilled ? "#cbd5e1" : "none"}
                  stroke={isFilled ? "#cbd5e1" : "#475569"}
                />
              </button>
            );
          })}
        </div>

        {submitted ? (
          <div className="review-submitted-msg">
            <CheckCircle size={20} color="#00b4d8" />
            <span>Thank you! Your feedback has been submitted successfully.</span>
          </div>
        ) : (
          <form className="review-form" onSubmit={handleSubmitReview}>
            <div className="textarea-wrapper">
              <textarea
                className="review-textarea"
                placeholder="Tell us what features you'd like to see in Pro..."
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value.slice(0, 300))}
                maxLength={300}
                required
              />
              <span className="char-counter">{reviewText.length}/300</span>
            </div>

            <label className="anonymous-checkbox-label">
              <input
                type="checkbox"
                className="anonymous-checkbox"
                checked={isAnonymous}
                onChange={(e) => setIsAnonymous(e.target.checked)}
              />
              <span className="checkbox-custom" />
              <span className="checkbox-text">Submit anonymously</span>
            </label>

            <button type="submit" className="review-submit-btn">
              <span>Submit Review</span>
              <Send size={16} className="send-icon" />
            </button>
          </form>
        )}
      </section>
    </div>
  );
}
