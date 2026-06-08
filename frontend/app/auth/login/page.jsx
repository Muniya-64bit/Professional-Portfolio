'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';
import styles from '../auth.module.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.authPage}>
      {/* ── Left Branding Panel ──────────────────────────── */}
      <div className={styles.authBrand}>
        <div className={styles.authBrandDecor1} />
        <div className={styles.authBrandDecor2} />
        <div className={styles.authBrandContent}>
          <img src="/logo.png" alt="KVPL Logo" className={styles.authBrandLogo} style={{ width: '48px', height: '48px', objectFit: 'contain' }} />
          <h1 className={styles.authBrandTitle}>KVPL System</h1>
          <p className={styles.authBrandSub}>
            Sri Lanka's leading tea plantation resource optimization platform.
            Drive smarter decisions across all your estates.
          </p>
          <div className={styles.authBrandFeatures}>
            {[
              { icon: '📊', text: 'Real-time ROI & cost-per-kg tracking' },
              { icon: '💧', text: 'Water intensity monitoring & alerts' },
              { icon: '🌱', text: 'Smart fertilizer rotation schedules' },
              { icon: '👥', text: 'Labour allocation & yield planning' },
            ].map(f => (
              <div key={f.text} className={styles.authBrandFeature}>
                <span className={styles.authBrandFeatureIcon}>{f.icon}</span>
                {f.text}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Right Form Panel ─────────────────────────────── */}
      <div className={styles.authForm}>
        <div className={styles.authCard}>
          <Link href="/" className={styles.backLink}>
            ← Back to home
          </Link>

          <div className={styles.authCardHeader}>
            <h2 className={styles.authCardTitle}>Welcome back</h2>
            <p className={styles.authCardSub}>Sign in to your KVPL dashboard</p>
          </div>

          {error && (
            <div className={styles.errorAlert}>
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className={styles.formGroup}>
              <label htmlFor="email" className={styles.formLabel}>Email address</label>
              <input
                id="email"
                type="email"
                className={styles.formInput}
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="manager@plantation.com"
                required
                disabled={isLoading}
              />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="password" className={styles.formLabel}>Password</label>
              <input
                id="password"
                type="password"
                className={styles.formInput}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={isLoading}
              />
            </div>

            <button type="submit" className={styles.submitBtn} disabled={isLoading}>
              {isLoading ? 'Signing in…' : 'Sign in →'}
            </button>
          </form>

          <div className={styles.authFooterText}>
            Don&apos;t have an account?{' '}
            <Link href="/auth/signup" className={styles.authLink}>Create one</Link>
          </div>

        </div>
      </div>
    </div>
  );
}
