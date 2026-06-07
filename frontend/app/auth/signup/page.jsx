'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';
import styles from '../auth.module.css';

export default function Signup() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { signup } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!fullName.trim()) { setError('Full name is required'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters long'); return; }
    if (!/[A-Z]/.test(password)) { setError('Password must contain at least one uppercase letter'); return; }
    if (!/[a-z]/.test(password)) { setError('Password must contain at least one lowercase letter'); return; }
    if (!/\d/.test(password)) { setError('Password must contain at least one digit'); return; }
    if (!/[!@#$%^&*()_+\-=\[\]{};:'",.<>?]/.test(password)) { setError('Password must contain at least one special character'); return; }
    if (password !== confirmPassword) { setError('Passwords do not match'); return; }
    setIsLoading(true);
    try {
      await signup(email, password, fullName);
      router.push('/dashboard');
    } catch (err) {
      setError(err.message || 'Sign up failed. Please try again.');
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
          <div className={styles.authBrandLogo}>🌿</div>
          <h1 className={styles.authBrandTitle}>Join KVPL</h1>
          <p className={styles.authBrandSub}>
            Create your account to start optimizing your tea plantation operations
            with data-driven insights and smart scheduling.
          </p>
          <div className={styles.authBrandFeatures}>
            {[
              { icon: '🚀', text: 'Set up in under 5 minutes' },
              { icon: '📊', text: 'Instant access to all 4 modules' },
              { icon: '🔒', text: 'Secure, role-based access control' },
              { icon: '📱', text: 'Works on desktop & mobile' },
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
            <h2 className={styles.authCardTitle}>Create account</h2>
            <p className={styles.authCardSub}>Get started with KVPL System today</p>
          </div>

          {error && (
            <div className={styles.errorAlert}>
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className={styles.formGroup}>
              <label htmlFor="fullName" className={styles.formLabel}>Full name</label>
              <input
                id="fullName"
                type="text"
                className={styles.formInput}
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                placeholder="Kamal Perera"
                required
                disabled={isLoading}
              />
            </div>

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
              <span className={styles.formHint}>
                Minimum 8 characters with uppercase, lowercase, number & special character
              </span>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="confirmPassword" className={styles.formLabel}>Confirm password</label>
              <input
                id="confirmPassword"
                type="password"
                className={styles.formInput}
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={isLoading}
              />
            </div>

            <button type="submit" className={styles.submitBtn} disabled={isLoading}>
              {isLoading ? 'Creating account…' : 'Create account →'}
            </button>
          </form>

          <div className={styles.authFooterText}>
            Already have an account?{' '}
            <Link href="/auth/login" className={styles.authLink}>Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
