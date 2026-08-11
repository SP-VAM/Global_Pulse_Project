import { useState, useEffect, useRef } from 'react';
import { ArrowRight, Zap, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import SignUp from '../auth/SignUp/SignUp';
import Logo from '../../components/common/Logo/Logo';
import FinancialGalaxyCanvas from './FinancialGalaxyCanvas';
import {
  WalletVisual,
  InvestmentVisual,
  EducationVisual,
  GoalVisual,
} from './AbstractVisuals';
import './LandingGalaxy.css';

function AnimatedCounter({ value, label }) {
  const [displayValue, setDisplayValue] = useState('0');
  const ref = useRef(null);
  const animFrameRef = useRef(null);

  const parseValue = (valStr) => {
    let prefix = '';
    let suffix = '';
    let clean = valStr;

    if (clean.startsWith('$')) {
      prefix = '$';
      clean = clean.slice(1);
    }
    if (clean.endsWith('+')) {
      suffix = '+' + suffix;
      clean = clean.slice(0, -1);
    }
    if (clean.endsWith('M') || clean.endsWith('%')) {
      suffix = clean.slice(-1) + suffix;
      clean = clean.slice(0, -1);
    }

    const hasComma = clean.includes(',');
    const target = parseInt(clean.replace(/,/g, ''), 10) || 0;
    return { prefix, target, suffix, hasComma };
  };

  const animate = () => {
    const { prefix, target, suffix, hasComma } = parseValue(value);
    const duration = 1500;
    let start = null;

    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
    }

    const step = (timestamp) => {
      if (!start) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(ease * target);

      const formatted = hasComma ? current.toLocaleString('en-US') : current.toString();
      setDisplayValue(`${prefix}${formatted}${suffix}`);

      if (progress < 1) {
        animFrameRef.current = requestAnimationFrame(step);
      } else {
        const finalFormatted = hasComma ? target.toLocaleString('en-US') : target.toString();
        setDisplayValue(`${prefix}${finalFormatted}${suffix}`);
      }
    };

    animFrameRef.current = requestAnimationFrame(step);
  };

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          animate();
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(node);

    return () => {
      observer.disconnect();
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [value]);

  return (
    <article ref={ref} className="gp-stat-panel" onMouseEnter={animate}>
      <span className="gp-stat-value">{displayValue}</span>
      <span className="gp-stat-label">{label}</span>
    </article>
  );
}

export default function Landing() {
  const navigate = useNavigate();
  const [showSignUpModal, setShowSignUpModal] = useState(false);
  const [activeJourneyStep, setActiveJourneyStep] = useState(0);

  const openModal = () => setShowSignUpModal(true);
  const closeModal = () => setShowSignUpModal(false);

  useEffect(() => {
    const handleScroll = () => {
      const journeyElem = document.getElementById('journey-section');
      if (journeyElem) {
        const rect = journeyElem.getBoundingClientRect();
        const elemHeight = rect.height;
        const visiblePx = Math.min(Math.max(-rect.top + window.innerHeight / 2, 0), elemHeight);
        const step = Math.min(Math.floor((visiblePx / elemHeight) * 5), 4);
        setActiveJourneyStep(step);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const featureList = [
    {
      Visual: WalletVisual,
      title: 'Expense Tracking',
      text: 'Track daily expenses and build a long-term portfolio automatically.',
    },
    {
      Visual: InvestmentVisual,
      title: 'Smart Investments',
      text: 'Personalized AI investment suggestions tailored to your risk tolerance.',
    },
    {
      Visual: EducationVisual,
      title: 'Financial Education',
      text: 'Bite-sized interactive lessons on budgeting, investing, and wealth building.',
    },
    {
      Visual: GoalVisual,
      title: 'Goal Tracking',
      text: 'Set targets, track progress visually, and hit key financial milestones.',
    },
  ];

  const journeyList = [
    {
      num: '01',
      title: 'Sign Up',
      desc: 'Create your account in under 2 minutes with secure profile integration.',
    },
    {
      num: '02',
      title: 'Track & Learn',
      desc: 'Understand cash flows and access tailored AI insights.',
    },
    {
      num: '03',
      title: 'Invest Wisely',
      desc: 'Define targets and emergency funds with smart progress tracking.',
    },
    {
      num: '04',
      title: 'Set Goals',
      desc: 'Get AI-driven portfolio suggestions aligned with your risk profile.',
    },
    {
      num: '05',
      title: 'Grow Wealth',
      desc: 'Watch your wealth scale and celebrate key financial milestones.',
    },
  ];

  const articleList = [
    {
      tag: 'Budgeting',
      title: '5 Rules for a Bulletproof Monthly Budget',
      text: 'Learn the proven framework that helps thousands save 20% of income monthly.',
      time: '4 min read',
    },
    {
      tag: 'Investing',
      title: 'Index Funds Vs. Individual Stocks: Beginner Guide',
      text: 'Understand key differences, risks, and returns for your first investment.',
      time: '5 min read',
    },
    {
      tag: 'Quick Cash',
      title: '7 Side Hustles You Can Start This Weekend',
      text: 'Practical, low-investment ideas to generate extra income with existing skills.',
      time: '6 min read',
    },
  ];

  return (
    <div className="landing-galaxy">
      {/* 3D WebGL Background Canvas with Cursor Star Trail */}
      <FinancialGalaxyCanvas />

      {/* SignUp Modal */}
      {showSignUpModal && <SignUp isModal={true} onClose={closeModal} />}

      {/* Dashboard-Aligned Glass Navbar */}
      <header className="gp-dashboard-nav">
        <div className="gp-nav-left">
          <Logo to="/" size="md" />
        </div>
        <div className="gp-nav-right">
          <button className="gp-nav-btn-login" onClick={() => navigate('/login')}>
            Log in
          </button>
          <button className="gp-nav-btn-signup" onClick={openModal}>
            Sign up
          </button>
        </div>
      </header>

      {/* Main Content Sections */}
      <main className="landing-content">
        {/* HERO SECTION — CENTERED */}
        <section className="gp-hero-centered">
          <h1 className="gp-hero-title-centered">
            Understand Global Events Before They Move <span>Indian Markets</span>
          </h1>
          <p className="gp-hero-subhead-centered">
            GlobalPulse automatically detects important global events, analyzes their financial
            ripple effects, connects them with Indian markets, and explains everything in simple
            language using AI.
          </p>

          <div className="gp-hero-cta-wrap">
            <button className="gp-hero-cta-btn" onClick={openModal}>
              Get Started Free <ArrowRight size={18} />
            </button>
          </div>

          {/* Dynamic HUD Signal Badges */}
          <div className="gp-hud-badges">
            <div className="gp-hud-badge gp-hud-badge--europe">
              <span className="gp-hud-dot" />
              <strong>EUROPE</strong>
              <small>Economic Signal Detected</small>
            </div>
            <div className="gp-hud-badge gp-hud-badge--india">
              <span className="gp-hud-dot gp-hud-dot--pulse" />
              <strong>
                INDIA <Zap size={12} fill="#00f0ff" stroke="none" />
              </strong>
              <small>Nifty 50 Ripple Impact</small>
            </div>
            <div className="gp-hud-badge gp-hud-badge--china">
              <span className="gp-hud-dot" />
              <strong>CHINA</strong>
              <small>Supply & Demand Shift</small>
            </div>
          </div>
        </section>

        {/* COMPACT FEATURES SECTION */}
        <section className="gp-section gp-section--centered">
          <h2 className="gp-section-heading">
            Everything You Need to Grow <em>Your Wealth</em>
          </h2>
          <p className="gp-section-subhead">
            From tracking daily expenses to building a long-term portfolio, we have you covered.
          </p>

          <div className="gp-features-grid-compact">
            {featureList.map(({ Visual, title, text }) => (
              <article key={title} className="gp-feature-card-compact">
                <Visual />
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        {/* ANIMATED JOURNEY TIMELINE DECK */}
        <section id="journey-section" className="gp-section gp-section--centered">
          <h2 className="gp-section-heading">
            From First Dollar to Financial <em>Freedom</em>
          </h2>
          <p className="gp-section-subhead">
            Follow a clear path designed to help you build wealth step by step — no finance degree
            required.
          </p>

          <div className="gp-journey-deck">
            {journeyList.map(({ num, title, desc }, idx) => {
              const isActive = idx <= activeJourneyStep;
              return (
                <div
                  key={num}
                  className={`gp-journey-card-step ${isActive ? 'is-active' : ''}`}
                >
                  <div className="gp-journey-step-badge">{num}</div>
                  <div className="gp-journey-step-content">
                    <h3>{title}</h3>
                    <p>{desc}</p>
                  </div>
                  {isActive && <CheckCircle2 size={18} className="gp-journey-check" />}
                </div>
              );
            })}
          </div>
        </section>

        {/* STATISTICS SECTION */}
        <section className="gp-section gp-section--centered">
          <h2 className="gp-section-heading">
            Trusted by <em>Thousands of Savers</em>
          </h2>
          <div className="gp-stats-grid">
            <AnimatedCounter value="2,400+" label="Active Users" />
            <AnimatedCounter value="$12M+" label="Tracked Transactions" />
            <AnimatedCounter value="94%" label="Goal Achievement Rate" />
            <AnimatedCounter value="35%" label="Avg. Savings Increase" />
          </div>
        </section>

        {/* LEARN & EARN ARTICLES SECTION */}
        <section className="gp-section gp-section--centered">
          <h2 className="gp-section-heading">
            Financial Education That Actually <em>Helps</em>
          </h2>
          <div className="gp-articles-grid">
            {articleList.map(({ tag, title, text, time }) => (
              <article key={title} className="gp-article-card">
                <span className="gp-article-tag">{tag}</span>
                <h3>{title}</h3>
                <p>{text}</p>
                <span className="gp-article-readtime">{time}</span>
              </article>
            ))}
          </div>
        </section>

        {/* FINAL CTA SECTION */}
        <section className="gp-section">
          <div className="gp-final-cta-card">
            <h2>Ready to Take Control of Your Finances?</h2>
            <p>
              Join thousands of users who are already building smarter financial habits. It takes
              less than 2 minutes to get started.
            </p>
            <div className="gp-cta-buttons">
              <button className="gp-hero-cta-btn" onClick={openModal}>
                Create Free Account <ArrowRight size={18} />
              </button>
              <button className="gp-nav-btn-login" onClick={() => navigate('/login')}>
                Log in
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
