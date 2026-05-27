'use client';

import { useAuth } from '../context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

/* ── Mock Data ──────────────────────────────────────────────────────────── */
const estates = [
  { id: 1, name: 'Kelani Valley', location: 'Western Province', rank: 1, costPerKg: 285, production: 3840, trend: [-8, 5, 3, -12, 8, -5, -3], delta: -3.2 },
  { id: 2, name: 'Nuwara Eliya', location: 'Central Province',  rank: 2, costPerKg: 298, production: 3210, trend: [2, -4, 6, 1, -7, 3, -2],  delta: -1.8 },
  { id: 3, name: 'Uva Highlands', location: 'Uva Province',    rank: 3, costPerKg: 312, production: 2950, trend: [4, 3, -1, 5, 2, 1, 1],    delta: +1.1 },
  { id: 4, name: 'Ratnapura',    location: 'Sabaragamuwa',      rank: 4, costPerKg: 345, production: 2450, trend: [6, 2, 8, -3, 4, 3, 2],    delta: +2.3 },
];

const waterData = [
  { month: 'Jan', intensity: 4.2, target: 4.5 },
  { month: 'Feb', intensity: 4.0, target: 4.5 },
  { month: 'Mar', intensity: 4.8, target: 4.5 },
  { month: 'Apr', intensity: 4.5, target: 4.5 },
  { month: 'May', intensity: 3.9, target: 4.4 },
  { month: 'Jun', intensity: 4.1, target: 4.4 },
];

const fertilizerBlocks = [
  { block: 'A1', estate: 'Kelani Valley', daysSince: 28, recommended: 'Urea 25kg', status: 'due' },
  { block: 'A2', estate: 'Kelani Valley', daysSince: 52, recommended: 'NPK 20kg',  status: 'overdue' },
  { block: 'A3', estate: 'Kelani Valley', daysSince: 12, recommended: 'MOP 15kg',  status: 'ok' },
  { block: 'B1', estate: 'Nuwara Eliya',  daysSince: 61, recommended: 'Urea 30kg', status: 'overdue' },
  { block: 'B2', estate: 'Nuwara Eliya',  daysSince: 5,  recommended: 'NPK 25kg',  status: 'ok' },
  { block: 'B3', estate: 'Nuwara Eliya',  daysSince: 33, recommended: 'Urea 20kg', status: 'due' },
  { block: 'C1', estate: 'Uva Highlands', daysSince: 44, recommended: 'NPK 20kg',  status: 'due' },
  { block: 'C2', estate: 'Uva Highlands', daysSince: 8,  recommended: 'MOP 18kg',  status: 'ok' },
  { block: 'D1', estate: 'Ratnapura',     daysSince: 70, recommended: 'Urea 35kg', status: 'overdue' },
  { block: 'D2', estate: 'Ratnapura',     daysSince: 18, recommended: 'NPK 22kg',  status: 'ok' },
  { block: 'D3', estate: 'Ratnapura',     daysSince: 38, recommended: 'Urea 28kg', status: 'due' },
];

const labourData = [
  { block: 'A1', estate: 'Kelani Valley', workers: 14, target: 550, actual: 532, efficiency: 96.7 },
  { block: 'A2', estate: 'Kelani Valley', workers: 10, target: 400, actual: 418, efficiency: 104.5 },
  { block: 'A3', estate: 'Kelani Valley', workers: 8,  target: 320, actual: 295, efficiency: 92.2 },
  { block: 'B1', estate: 'Nuwara Eliya',  workers: 12, target: 480, actual: 471, efficiency: 98.1 },
  { block: 'B2', estate: 'Nuwara Eliya',  workers: 9,  target: 360, actual: 382, efficiency: 106.1 },
  { block: 'B3', estate: 'Nuwara Eliya',  workers: 7,  target: 280, actual: 260, efficiency: 92.9 },
  { block: 'C1', estate: 'Uva Highlands', workers: 11, target: 440, actual: 445, efficiency: 101.1 },
  { block: 'C2', estate: 'Uva Highlands', workers: 8,  target: 320, actual: 308, efficiency: 96.3 },
  { block: 'D1', estate: 'Ratnapura',     workers: 13, target: 520, actual: 493, efficiency: 94.8 },
  { block: 'D2', estate: 'Ratnapura',     workers: 10, target: 400, actual: 415, efficiency: 103.8 },
  { block: 'D3', estate: 'Ratnapura',     workers: 6,  target: 240, actual: 231, efficiency: 96.3 },
];

/* ── Helper Components ────────────────────────────────────────────────── */
function Sparkline({ data, height = 28 }) {
  const max = Math.max(...data.map(Math.abs));
  const baseline = Math.max(...data);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height }}>
      {data.map((v, i) => {
        const barH = Math.max(3, (Math.abs(v) / (max || 1)) * height);
        const isLast = i === data.length - 1;
        const color = v < 0 ? '#16a34a' : v > 0 ? '#dc2626' : '#9ca3af';
        return (
          <div
            key={i}
            style={{
              flex: 1,
              height: barH,
              borderRadius: '2px',
              background: isLast ? color : (v < 0 ? '#bbf7d0' : v > 0 ? '#fecaca' : '#e5e7eb'),
              transition: 'height 0.3s ease',
              minHeight: 3,
            }}
          />
        );
      })}
    </div>
  );
}

function KpiCard({ icon, iconBg, label, value, unit, delta, deltaLabel }) {
  const isPos = delta < 0; // lower cost/intensity = positive
  const isNeg = delta > 0;
  return (
    <div className="kpi-card">
      <div className="kpi-header">
        <div className={`kpi-icon-wrap ${iconBg}`}>{icon}</div>
        {delta !== undefined && (
          <span className={`kpi-delta ${isPos ? 'kpi-delta-up' : isNeg ? 'kpi-delta-down' : 'kpi-delta-neutral'}`}>
            {isPos ? '↓' : isNeg ? '↑' : '→'} {Math.abs(delta)}%
          </span>
        )}
      </div>
      <div className="kpi-value">{value}<span style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--color-text-muted)', marginLeft: 4 }}>{unit}</span></div>
      <div className="kpi-label">{label}</div>
      {deltaLabel && <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{deltaLabel}</div>}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    ok:      { cls: 'badge-success', label: 'OK' },
    due:     { cls: 'badge-warning', label: 'Due Soon' },
    overdue: { cls: 'badge-danger',  label: 'Overdue' },
  };
  const { cls, label } = map[status] || map.ok;
  return <span className={`badge ${cls}`}>{label}</span>;
}

/* ── Tab: Overview ────────────────────────────────────────────────────── */
function OverviewTab() {
  const totalProd = labourData.reduce((s, r) => s + r.actual, 0);
  const avgCost = Math.round(estates.reduce((s, e) => s + e.costPerKg, 0) / estates.length);
  const activeWorkers = labourData.reduce((s, r) => s + r.workers, 0);
  const avgWater = (waterData.reduce((s, w) => s + w.intensity, 0) / waterData.length).toFixed(1);

  return (
    <>
      {/* KPI Cards */}
      <div className="kpi-grid">
        <KpiCard icon="🌿" iconBg="kpi-icon-green"  label="Total Production (Jun)" value={totalProd.toLocaleString()} unit="kg" delta={-8.3} deltaLabel="vs last month" />
        <KpiCard icon="💧" iconBg="kpi-icon-teal"   label="Avg Water Intensity"    value={avgWater}   unit="L/kg" delta={-2.1} deltaLabel="vs target 4.5 L/kg" />
        <KpiCard icon="👥" iconBg="kpi-icon-blue"   label="Active Workers"         value={activeWorkers} unit="" delta={-0} deltaLabel="+5 vs last week" />
        <KpiCard icon="💰" iconBg="kpi-icon-amber"  label="Avg Cost / kg"          value={`Rs. ${avgCost}`} unit="" delta={+2.5} deltaLabel="vs last quarter" />
      </div>

      {/* Two column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 'var(--space-6)' }}>

        {/* Estate Rankings mini table */}
        <div className="section-card">
          <div className="section-card-header">
            <div className="section-card-title">
              <div className="section-card-title-icon">📊</div>
              Estate Rankings
            </div>
            <span className="badge badge-neutral">by Cost/kg</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Estate</th>
                <th>Cost/kg</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              {estates.map(e => (
                <tr key={e.id}>
                  <td>
                    <div className={`rank-badge rank-${e.rank}`}>{e.rank}</div>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--color-text)', fontSize: '0.9rem' }}>{e.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{e.location}</div>
                  </td>
                  <td style={{ fontWeight: 700 }}>Rs. {e.costPerKg}</td>
                  <td><Sparkline data={e.trend} height={24} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Water efficiency quick view */}
        <div className="section-card">
          <div className="section-card-header">
            <div className="section-card-title">
              <div className="section-card-title-icon">💧</div>
              Water Efficiency (2026)
            </div>
            <span className="badge badge-success">On Track</span>
          </div>
          <div className="section-card-body">
            {waterData.map(w => {
              const pct = Math.min(100, (w.intensity / 6) * 100);
              const ok = w.intensity <= w.target;
              return (
                <div key={w.month} className="water-row">
                  <div className="water-month">{w.month}</div>
                  <div className="water-bar-wrap">
                    <div className="progress-wrap">
                      <div
                        className={`progress-bar ${ok ? 'progress-green' : 'progress-amber'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                  <div className="water-value" style={{ color: ok ? 'var(--color-success)' : 'var(--color-warning)' }}>
                    {w.intensity} L
                  </div>
                  <span className={`badge ${ok ? 'badge-success' : 'badge-warning'}`} style={{ width: 80, justifyContent: 'center' }}>
                    {ok ? 'On Track' : 'At Risk'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Fertilizer alerts */}
      <div className="section-card" style={{ marginTop: 'var(--space-6)' }}>
        <div className="section-card-header">
          <div className="section-card-title">
            <div className="section-card-title-icon">🌱</div>
            Fertilizer Alerts
          </div>
          <span className="badge badge-danger">
            {fertilizerBlocks.filter(b => b.status === 'overdue').length} Overdue
          </span>
        </div>
        <div className="section-card-body">
          <div className="alert alert-warning" style={{ marginBottom: 'var(--space-4)' }}>
            <span>⚠️</span>
            <span><strong>{fertilizerBlocks.filter(b => b.status === 'overdue').length} blocks</strong> are overdue for fertilizer application. Immediate action recommended.</span>
          </div>
          <div className="block-grid">
            {fertilizerBlocks.filter(b => b.status !== 'ok').map(b => (
              <div key={b.block} className={`block-card status-${b.status}`}>
                <div className="block-name">{b.block}</div>
                <div className="block-estate">{b.estate}</div>
                <div className="block-days">{b.daysSince}</div>
                <div className="block-days-label">days since last</div>
                <StatusBadge status={b.status} />
                <div style={{ marginTop: 'var(--space-3)', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                  Rec: {b.recommended}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

/* ── Tab: ROI ─────────────────────────────────────────────────────────── */
function ROITab() {
  return (
    <>
      <div className="kpi-grid">
        <KpiCard icon="🏆" iconBg="kpi-icon-green"  label="Best Cost/kg (Kelani)" value="Rs. 285" unit="" delta={-3.2} />
        <KpiCard icon="📦" iconBg="kpi-icon-teal"   label="Total Production (Jun)" value="12,450"  unit="kg" delta={-8.3} />
        <KpiCard icon="📈" iconBg="kpi-icon-blue"   label="Avg Cost / kg (All)"    value="Rs. 310" unit="" delta={+0.5} />
        <KpiCard icon="🏭" iconBg="kpi-icon-amber"  label="Highest Cost (Ratnapura)" value="Rs. 345" unit="" delta={+2.3} />
      </div>

      <div className="table-wrap">
        <div className="table-header-bar">
          <div>
            <div className="table-title">Estate ROI Rankings</div>
            <div className="table-subtitle">Sorted by cost-per-kg · June 2026</div>
          </div>
          <span className="badge badge-neutral">4 estates</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Estate</th>
              <th>Location</th>
              <th>Cost / kg</th>
              <th>Production (kg)</th>
              <th>MoM Δ</th>
              <th>7-Day Trend</th>
            </tr>
          </thead>
          <tbody>
            {estates.map(e => (
              <tr key={e.id}>
                <td><div className={`rank-badge rank-${e.rank}`}>{e.rank}</div></td>
                <td style={{ fontWeight: 600, color: 'var(--color-text)' }}>{e.name}</td>
                <td>{e.location}</td>
                <td style={{ fontWeight: 700, fontSize: '1.05rem' }}>Rs. {e.costPerKg}</td>
                <td>{e.production.toLocaleString()}</td>
                <td>
                  <span className={e.delta < 0 ? 'trend-up' : 'trend-down'} style={{ fontWeight: 600 }}>
                    {e.delta > 0 ? '↑' : '↓'} {Math.abs(e.delta)}%
                  </span>
                </td>
                <td style={{ minWidth: 80 }}><Sparkline data={e.trend} height={24} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Simple horizontal bar chart */}
      <div className="section-card" style={{ marginTop: 'var(--space-6)' }}>
        <div className="section-card-header">
          <div className="section-card-title">
            <div className="section-card-title-icon">📊</div>
            Cost Per kg Comparison
          </div>
        </div>
        <div className="section-card-body">
          {estates.map(e => {
            const maxCost = 400;
            const pct = (e.costPerKg / maxCost) * 100;
            const colors = ['progress-green', 'progress-green', 'progress-amber', 'progress-red'];
            return (
              <div key={e.id} style={{ marginBottom: 'var(--space-5)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-2)', fontSize: '0.9rem' }}>
                  <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{e.name}</span>
                  <span style={{ fontWeight: 700 }}>Rs. {e.costPerKg}</span>
                </div>
                <div className="progress-wrap" style={{ height: 12 }}>
                  <div className={`progress-bar ${colors[e.rank - 1]}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

/* ── Tab: Water ───────────────────────────────────────────────────────── */
function WaterTab() {
  const onTrack = waterData.filter(w => w.intensity <= w.target).length;
  const atRisk = waterData.filter(w => w.intensity > w.target).length;
  return (
    <>
      <div className="kpi-grid">
        <KpiCard icon="💧" iconBg="kpi-icon-teal"  label="Jun Intensity" value="4.1" unit="L/kg" delta={-0.9} deltaLabel="vs target 4.4 L/kg" />
        <KpiCard icon="✅" iconBg="kpi-icon-green"  label="Months On Track" value={onTrack} unit="" />
        <KpiCard icon="⚠️" iconBg="kpi-icon-amber"  label="Months At Risk"  value={atRisk} unit="" />
        <KpiCard icon="🎯" iconBg="kpi-icon-blue"  label="Annual Goal"     value="-2%" unit="" deltaLabel="reduction vs last year" />
      </div>

      <div className="table-wrap" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="table-header-bar">
          <div>
            <div className="table-title">Monthly Water Intensity</div>
            <div className="table-subtitle">Factory water use per kg tea produced · 2026</div>
          </div>
          <span className="badge badge-success">{onTrack}/{waterData.length} On Track</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Month</th>
              <th>Actual (L/kg)</th>
              <th>Target (L/kg)</th>
              <th>Variance</th>
              <th>Usage Bar</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {waterData.map(w => {
              const variance = (w.intensity - w.target).toFixed(1);
              const ok = w.intensity <= w.target;
              const pct = Math.min(100, (w.intensity / 6) * 100);
              return (
                <tr key={w.month}>
                  <td style={{ fontWeight: 600, color: 'var(--color-text)' }}>{w.month}</td>
                  <td style={{ fontWeight: 700, fontSize: '1.05rem', color: ok ? 'var(--color-success)' : 'var(--color-warning)' }}>
                    {w.intensity}
                  </td>
                  <td>{w.target}</td>
                  <td style={{ fontWeight: 600, color: variance > 0 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                    {variance > 0 ? '+' : ''}{variance}
                  </td>
                  <td style={{ minWidth: 140 }}>
                    <div className="progress-wrap">
                      <div className={`progress-bar ${ok ? 'progress-green' : 'progress-amber'}`} style={{ width: `${pct}%` }} />
                    </div>
                  </td>
                  <td><span className={`badge ${ok ? 'badge-success' : 'badge-warning'}`}>{ok ? 'On Track' : 'At Risk'}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="alert alert-info">
        <span>ℹ️</span>
        <span>March recorded the highest intensity at 4.8 L/kg. Review factory maintenance logs and irrigation schedules to identify root causes.</span>
      </div>
    </>
  );
}

/* ── Tab: Fertilizer ──────────────────────────────────────────────────── */
function FertilizerTab() {
  const overdueCount = fertilizerBlocks.filter(b => b.status === 'overdue').length;
  const dueCount = fertilizerBlocks.filter(b => b.status === 'due').length;
  return (
    <>
      <div className="kpi-grid">
        <KpiCard icon="🌱" iconBg="kpi-icon-green" label="Total Blocks Tracked" value={fertilizerBlocks.length} unit="" />
        <KpiCard icon="✅" iconBg="kpi-icon-green" label="OK — No Action"   value={fertilizerBlocks.filter(b => b.status === 'ok').length} unit="" />
        <KpiCard icon="⚠️" iconBg="kpi-icon-amber" label="Due This Week"    value={dueCount}    unit="" />
        <KpiCard icon="🚨" iconBg="kpi-icon-amber" label="Overdue"          value={overdueCount} unit="" delta={overdueCount > 0 ? overdueCount : undefined} />
      </div>

      {overdueCount > 0 && (
        <div className="alert alert-danger" style={{ marginBottom: 'var(--space-6)' }}>
          <span>🚨</span>
          <span><strong>{overdueCount} blocks</strong> are overdue for fertilizer application. Delays can reduce yield and soil quality. Apply immediately.</span>
        </div>
      )}

      <div className="section-card">
        <div className="section-card-header">
          <div className="section-card-title">
            <div className="section-card-title-icon">🌱</div>
            Block Rotation Status
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <span className="badge badge-success">OK</span>
            <span className="badge badge-warning">Due</span>
            <span className="badge badge-danger">Overdue</span>
          </div>
        </div>
        <div className="section-card-body">
          <div className="block-grid">
            {fertilizerBlocks.map(b => (
              <div key={b.block} className={`block-card status-${b.status}`}>
                <div className="block-name">{b.block}</div>
                <div className="block-estate">{b.estate}</div>
                <div className="block-days">{b.daysSince}</div>
                <div className="block-days-label">days since last</div>
                <StatusBadge status={b.status} />
                <div style={{ marginTop: 'var(--space-3)', fontSize: '0.75rem', color: 'var(--color-primary-light)', fontWeight: 600 }}>
                  → {b.recommended}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

/* ── Tab: Labour ──────────────────────────────────────────────────────── */
function LabourTab() {
  const totalWorkers = labourData.reduce((s, r) => s + r.workers, 0);
  const totalTarget = labourData.reduce((s, r) => s + r.target, 0);
  const totalActual = labourData.reduce((s, r) => s + r.actual, 0);
  const overallEff = ((totalActual / totalTarget) * 100).toFixed(1);

  return (
    <>
      <div className="kpi-grid">
        <KpiCard icon="👥" iconBg="kpi-icon-blue"  label="Total Active Workers"    value={totalWorkers} unit="" />
        <KpiCard icon="🎯" iconBg="kpi-icon-green" label="Production Target (kg)"  value={totalTarget.toLocaleString()} unit="kg" />
        <KpiCard icon="📦" iconBg="kpi-icon-teal"  label="Actual Output (kg)"      value={totalActual.toLocaleString()} unit="kg" />
        <KpiCard icon="⚡" iconBg="kpi-icon-amber" label="Overall Efficiency"       value={`${overallEff}%`} unit="" delta={overallEff >= 100 ? -0.5 : 0} />
      </div>

      <div className="table-wrap">
        <div className="table-header-bar">
          <div>
            <div className="table-title">Weekly Labour Allocation</div>
            <div className="table-subtitle">Block-level worker distribution & production tracking · Week 22</div>
          </div>
          <span className="badge badge-neutral">11 blocks</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Block</th>
              <th>Estate</th>
              <th>Workers</th>
              <th>Target (kg)</th>
              <th>Actual (kg)</th>
              <th>Efficiency</th>
              <th>Progress</th>
            </tr>
          </thead>
          <tbody>
            {labourData.map(r => {
              const eff = r.efficiency;
              const pct = Math.min(100, (r.actual / r.target) * 100);
              const effColor = eff >= 100 ? 'var(--color-success)' : eff >= 90 ? 'var(--color-warning)' : 'var(--color-danger)';
              const barClass = eff >= 100 ? 'progress-green' : eff >= 90 ? 'progress-amber' : 'progress-red';
              return (
                <tr key={r.block}>
                  <td style={{ fontWeight: 700, color: 'var(--color-text)' }}>{r.block}</td>
                  <td style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>{r.estate}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span>👤</span>
                      <span style={{ fontWeight: 600 }}>{r.workers}</span>
                    </div>
                  </td>
                  <td>{r.target}</td>
                  <td style={{ fontWeight: 700 }}>{r.actual}</td>
                  <td style={{ fontWeight: 700, color: effColor }}>{eff}%</td>
                  <td style={{ minWidth: 120 }}>
                    <div className="progress-wrap">
                      <div className={`progress-bar ${barClass}`} style={{ width: `${pct}%` }} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

/* ── Nav Items Config ─────────────────────────────────────────────────── */
const navItems = [
  { id: 'overview',    icon: '🏠', label: 'Overview' },
  { id: 'roi',         icon: '📊', label: 'ROI Calculator' },
  { id: 'water',       icon: '💧', label: 'Water Efficiency' },
  { id: 'fertilizer',  icon: '🌱', label: 'Fertilizer Rotation' },
  { id: 'labour',      icon: '👥', label: 'Labour Planner' },
];

const tabTitles = {
  overview:   { title: 'Overview',           sub: 'Estate-wide summary for June 2026' },
  roi:        { title: 'ROI Calculator',      sub: 'Cost-per-kg analysis across all estates' },
  water:      { title: 'Water Efficiency',    sub: 'Monthly factory water intensity tracking' },
  fertilizer: { title: 'Fertilizer Rotation', sub: 'Block-level application schedule & alerts' },
  labour:     { title: 'Labour Planner',      sub: 'Weekly worker allocation & production targets' },
};

/* ── Main Dashboard ───────────────────────────────────────────────────── */
export default function DashboardPage() {
  const { user, isAuthenticated, logout } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 'var(--space-4)' }}>🌿</div>
          <p>Loading dashboard…</p>
        </div>
      </div>
    );
  }

  const userInitials = (user?.full_name || user?.email || 'U').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  const { title, sub } = tabTitles[activeTab];

  return (
    <div className="dash-layout">
      {/* ── Sidebar ──────────────────────────────────────────── */}
      <aside className="dash-sidebar">
        <div className="dash-sidebar-logo">
          <div className="dash-sidebar-logo-mark">🌿</div>
          <div className="dash-sidebar-brand">
            KVPL
            <small>Plantation System</small>
          </div>
        </div>

        <nav className="dash-nav">
          <div className="dash-nav-label">Main Menu</div>
          {navItems.map(item => (
            <button
              key={item.id}
              className={`dash-nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <span className="dash-nav-icon">{item.icon}</span>
              {item.label}
              {item.id === 'fertilizer' && (
                <span className="dash-nav-badge">
                  {fertilizerBlocks.filter(b => b.status === 'overdue').length}
                </span>
              )}
            </button>
          ))}

          <div className="dash-nav-label" style={{ marginTop: 'var(--space-4)' }}>Estates</div>
          {estates.map(e => (
            <div key={e.id} className="dash-nav-item" style={{ cursor: 'default', fontSize: '0.875rem' }}>
              <span className="dash-nav-icon" style={{ fontSize: '0.875rem' }}>🏡</span>
              {e.name}
              <span className="dash-nav-badge" style={{ background: 'rgba(255,255,255,0.1)' }}>#{e.rank}</span>
            </div>
          ))}
        </nav>

        <div className="dash-sidebar-footer">
          <button
            className="dash-nav-item"
            onClick={logout}
            style={{ color: 'rgba(255,100,100,0.8)' }}
          >
            <span className="dash-nav-icon">🚪</span>
            Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main Area ────────────────────────────────────────── */}
      <div className="dash-main">
        {/* Top Bar */}
        <header className="dash-topbar">
          <div className="dash-topbar-left">
            <div className="dash-breadcrumb">
              KVPL &rsaquo; <strong>{title}</strong>
            </div>
          </div>
          <div className="dash-topbar-right">
            <span className="tag" style={{ fontSize: '0.75rem' }}>June 2026</span>
            <div className="dash-user-pill">
              <div className="dash-avatar">{userInitials}</div>
              <span>{user?.full_name || user?.email}</span>
              {user?.role && (
                <span className="badge badge-neutral" style={{ fontSize: '0.6875rem' }}>{user.role}</span>
              )}
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="dash-content">
          <div style={{ marginBottom: 'var(--space-6)' }}>
            <h1 className="dash-page-title">{title}</h1>
            <p className="dash-page-subtitle">{sub}</p>
          </div>

          {activeTab === 'overview'    && <OverviewTab />}
          {activeTab === 'roi'         && <ROITab />}
          {activeTab === 'water'       && <WaterTab />}
          {activeTab === 'fertilizer'  && <FertilizerTab />}
          {activeTab === 'labour'      && <LabourTab />}
        </main>
      </div>
    </div>
  );
}
