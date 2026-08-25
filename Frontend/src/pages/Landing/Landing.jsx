import { useState, useEffect, useRef } from 'react';
import { ArrowRight, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import SignUp from '../auth/SignUp/SignUp';
import Logo from '../../components/common/Logo/Logo';
import Footer from '../../components/layout/Footer/Footer';
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

  const openModal = () => setShowSignUpModal(true);
  const closeModal = () => setShowSignUpModal(false);

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
    },
    {
      tag: 'Investing',
      title: 'Index Funds Vs. Individual Stocks: Beginner Guide',
      text: 'Understand key differences, risks, and returns for your first investment.',
    },
    {
      tag: 'Quick Cash',
      title: '7 Side Hustles You Can Start This Weekend',
      text: 'Practical, low-investment ideas to generate extra income with existing skills.',
    },
  ];

  return (
    <div className="landing-galaxy">
      <FinancialGalaxyCanvas />

      {showSignUpModal && <SignUp isModal={true} onClose={closeModal} />}

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

      <main className="gp-landing-main">
        <section className="gp-hero">
          <div className="gp-hero-badge">
            <Zap size={14} className="gp-zap-icon" /> AI-POWERED PERSONAL FINANCE
          </div>

          <h1 className="gp-hero-title">
            Master Your Money, <br />
            <span className="gp-gradient-text">Build Your Future.</span>
          </h1>

          <p className="gp-hero-subtitle">
            Track expenses, discover personalized investment opportunities, and hit your financial
            goals faster with real-time AI guidance.
          </p>

          <div className="gp-hero-actions">
            <button className="gp-hero-cta-btn" onClick={openModal}>
              Start Your Journey <ArrowRight size={18} />
            </button>
          </div>
        </section>

        <section className="gp-section gp-section--centered">
          <h2 className="gp-section-heading">
            Everything You Need to <em>Succeed</em>
          </h2>
          <p className="gp-section-sub">
            Powerful financial tools wrapped in an intuitive, beautifully designed interface.
          </p>

          <div className="gp-features-grid">
            {featureList.map(({ Visual, title, text }) => (
              <article key={title} className="gp-feature-card">
                <div className="gp-feature-visual-wrap">
                  <Visual />
                </div>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="journey-section" className="gp-section gp-section--centered">
          <h2 className="gp-section-heading">
            From First Dollar to <em>Financial Freedom</em>
          </h2>
          <p className="gp-section-sub">
            Your step-by-step roadmap to taking complete control of your financial destiny.
          </p>

          <div className="gp-journey-deck">
            {journeyList.map(({ num, title, desc }) => (
              <div key={num} className="gp-journey-card-step">
                <div className="gp-journey-step-badge">{num}</div>
                <div className="gp-journey-step-content">
                  <h3>{title}</h3>
                  <p>{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

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

        <section className="gp-section gp-section--centered">
          <h2 className="gp-section-heading">
            Financial Education That Actually <em>Helps</em>
          </h2>
          <div className="gp-articles-grid">
            {articleList.map(({ tag, title, text }) => (
              <article key={title} className="gp-article-card">
                <span className="gp-article-tag">{tag}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

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

      {/* Landing Page Footer */}
      <Footer />
    </div>
  );
}
