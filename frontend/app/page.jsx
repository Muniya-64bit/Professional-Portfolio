'use client';

const modules = [
  {
    icon: '📊',
    title: 'ROI Calculator',
    desc: 'Track cost-per-kg metrics and identify high-performing estates with real-time trend analysis.',
    features: ['Estate ranking & benchmarking', 'Trend sparkline charts', 'Outlier cost highlighting'],
  },
  {
    icon: '💧',
    title: 'Water Efficiency',
    desc: 'Monitor factory water intensity vs targets with smart status indicators and reduction goals.',
    features: ['Monthly intensity tracking', 'On Track / At Risk alerts', '2% annual reduction target'],
  },
  {
    icon: '🌱',
    title: 'Fertilizer Rotation',
    desc: 'Optimize block-level fertilizer applications with action-based recommendations.',
    features: ['Last application tracking', 'Smart dosage recommendations', 'Block rotation scheduler'],
  },
  {
    icon: '👥',
    title: 'Labour Planner',
    desc: 'Weekly worker allocation across blocks with live kg production target tracking.',
    features: ['Worker pool management', 'Per-block allocation view', 'Production target vs actual'],
  },
];

const steps = [
  { num: '01', title: 'Connect Your Estates', desc: 'Link your plantation blocks and configure your estate hierarchy in minutes.' },
  { num: '02', title: 'Input Field Data', desc: 'Log daily production figures, water usage, fertilizer applications, and labour records.' },
  { num: '03', title: 'Optimize Operations', desc: 'Get instant insights, recommendations, and ROI trends to drive better decisions.' },
];

export default function Home() {
  return (
    <main>
      {/* ─── Navigation ─────────────────────────────────────── */}
      <header className="site-header">
        <div className="container">
          <nav className="site-nav">
            <a href="/" className="site-logo">
              <img src="/logo.png" alt="KVPL Logo" className="logo-mark" style={{ width: '32px', height: '32px', objectFit: 'contain' }} />
              <span>KVPL</span>
            </a>

            <div className="nav-links">
              <a href="#modules">Modules</a>
              <a href="#how-it-works">How it works</a>
              <a href="#stats">Results</a>
            </div>

            <div className="nav-actions">
              <a href="/auth/login" className="btn btn-secondary btn-sm">Login</a>
              <a href="/auth/signup" className="btn btn-primary btn-sm">Get Started</a>
            </div>
          </nav>
        </div>
      </header>

      {/* ─── Hero ────────────────────────────────────────────── */}
      <section className="hero">
        <div className="container" style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ marginBottom: 'var(--space-5)' }}>
            <span className="tag" style={{ background: 'rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.9)', border: '1px solid rgba(255,255,255,0.25)' }}>
              🇱🇰 Built for Sri Lankan Tea Estates
            </span>
          </div>
          <h1 style={{ color: 'white', maxWidth: '820px', margin: '0 auto var(--space-6)' }}>
            Smarter Operations for<br />Sri Lankan Tea Plantations
          </h1>
          <p style={{ maxWidth: '600px', margin: '0 auto', fontSize: '1.2rem', color: 'rgba(255,255,255,0.85)' }}>
            One platform to track ROI, manage water efficiency, schedule fertilizer rotations,
            and allocate labour — all from a single dashboard.
          </p>
          <div className="hero-actions">
            <a href="/auth/signup" className="btn-hero-primary">
              Start Free →
            </a>
            <a href="/auth/login" className="btn-hero-outline">
              Sign In
            </a>
          </div>

          {/* Mini trust strip */}
          <div style={{ marginTop: 'var(--space-12)', color: 'rgba(255,255,255,0.55)', fontSize: '0.875rem' }}>
            Trusted across 4 estates · 11 managed blocks · 500+ daily data points
          </div>
        </div>
      </section>

      {/* ─── Stats Bar ───────────────────────────────────────── */}
      <section className="stats-bar" id="stats">
        <div className="container">
          <div className="stats-bar-grid">
            {[
              { num: '4', label: 'Sri Lankan Estates' },
              { num: '11', label: 'Managed Tea Blocks' },
              { num: '500+', label: 'Data Points Daily' },
              { num: '2%', label: 'Annual Water Reduction' },
            ].map(s => (
              <div key={s.label} className="stat-item-bar">
                <div className="stat-number">{s.num}</div>
                <div className="stat-label">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Modules ─────────────────────────────────────────── */}
      <section className="section" id="modules">
        <div className="container">
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-12)' }}>
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <span className="tag">4 Powerful Modules</span>
            </div>
            <h2>Everything Your Plantation Needs</h2>
            <p style={{ fontSize: '1.1rem', maxWidth: '540px', margin: '0 auto' }}>
              Integrated tools designed specifically for the operational challenges
              of Sri Lankan tea cultivation.
            </p>
          </div>

          <div className="grid grid-2">
            {modules.map(m => (
              <div key={m.title} className="card animate-fade-in-up">
                <div className="feature-icon">{m.icon}</div>
                <h3>{m.title}</h3>
                <p style={{ marginBottom: 'var(--space-4)' }}>{m.desc}</p>
                <ul className="feature-list">
                  {m.features.map(f => (
                    <li key={f} className="feature-list-item">{f}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── How It Works ────────────────────────────────────── */}
      <section
        className="section"
        id="how-it-works"
        style={{ background: 'var(--forest-50)', borderTop: '1px solid var(--color-border)', borderBottom: '1px solid var(--color-border)' }}
      >
        <div className="container">
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-12)' }}>
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <span className="tag">Simple Setup</span>
            </div>
            <h2>Up and Running in Minutes</h2>
            <p style={{ maxWidth: '480px', margin: '0 auto' }}>
              No complex onboarding. Just connect, log, and start optimizing.
            </p>
          </div>

          <div className="grid grid-3" style={{ textAlign: 'center' }}>
            {steps.map(s => (
              <div key={s.num} style={{ padding: 'var(--space-6)' }}>
                <div className="step-number">{s.num}</div>
                <h3 style={{ marginBottom: 'var(--space-3)' }}>{s.title}</h3>
                <p style={{ maxWidth: '260px', margin: '0 auto' }}>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─────────────────────────────────────────────── */}
      <section className="section" style={{ background: 'var(--color-primary)', color: 'white' }}>
        <div className="container" style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <span style={{ background: 'rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.9)', padding: '0.25rem 0.875rem', borderRadius: 'var(--radius-full)', fontSize: '0.8125rem', fontWeight: 600, border: '1px solid rgba(255,255,255,0.2)' }}>
              Free Access
            </span>
          </div>
          <h2 style={{ color: 'white', marginBottom: 'var(--space-5)', maxWidth: '600px', margin: '0 auto var(--space-5)' }}>
            Ready to Optimize Your Estate Operations?
          </h2>
          <p style={{ color: 'rgba(255,255,255,0.75)', fontSize: '1.1rem', marginBottom: 'var(--space-8)', maxWidth: '480px', margin: '0 auto var(--space-8)' }}>
            Login to access your dashboard and start making data-driven decisions today.
          </p>
          <div className="hero-actions" style={{ marginTop: 0 }}>
            <a href="/auth/signup" className="btn-hero-primary">Create Account →</a>
            <a href="/auth/login" className="btn-hero-outline">Login</a>
          </div>
        </div>
      </section>

      {/* ─── Footer ──────────────────────────────────────────── */}
      <footer className="site-footer">
        <div className="container">
          <div className="footer-grid">
            <div>
              <div className="footer-brand">
                <div className="logo-mark">🌿</div>
                KVPL System
              </div>
              <p className="footer-desc">
                Empowering Sri Lankan tea estates with intelligent resource optimization,
                data-driven insights, and operational efficiency tools.
              </p>
            </div>

            <div>
              <div className="footer-col-title">Platform</div>
              <div className="footer-links">
                <a href="#modules">ROI Calculator</a>
                <a href="#modules">Water Efficiency</a>
                <a href="#modules">Fertilizer Rotation</a>
                <a href="#modules">Labour Planner</a>
              </div>
            </div>

            <div>
              <div className="footer-col-title">Account</div>
              <div className="footer-links">
                <a href="/auth/login">Login</a>
                <a href="/auth/signup">Sign Up</a>
                <a href="/dashboard">Dashboard</a>
              </div>
            </div>
          </div>

          <div className="footer-bottom">
            © 2026 KVPL System. Optimizing tea plantation operations across Sri Lanka.
          </div>
        </div>
      </footer>
    </main>
  );
}
