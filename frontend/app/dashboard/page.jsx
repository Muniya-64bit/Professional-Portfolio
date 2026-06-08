'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiService } from '../api/apiService';
import { useAuth } from '../context/AuthContext';

/* ── Mock Data ──────────────────────────────────────────────────────────── */
const estates = [
  { id: 1, name: 'Kelani Valley', location: 'Western Province', rank: 1, costPerKg: 285, production: 3840, trend: [-8, 5, 3, -12, 8, -5, -3], delta: -3.2 },
  { id: 2, name: 'Nuwara Eliya', location: 'Central Province',  rank: 2, costPerKg: 298, production: 3210, trend: [2, -4, 6, 1, -7, 3, -2],  delta: -1.8 },
  { id: 3, name: 'Uva Highlands', location: 'Uva Province',    rank: 3, costPerKg: 312, production: 2950, trend: [4, 3, -1, 5, 2, 1, 1],    delta: +1.1 },
  { id: 4, name: 'Ratnapura',    location: 'Sabaragamuwa',      rank: 4, costPerKg: 345, production: 2450, trend: [6, 2, 8, -3, 4, 3, 2],    delta: +2.3 },
];

// const waterData = [
//   { month: 'Jan', intensity: 4.2, target: 4.5 },
//   { month: 'Feb', intensity: 4.0, target: 4.5 },
//   { month: 'Mar', intensity: 4.8, target: 4.5 },
//   { month: 'Apr', intensity: 4.5, target: 4.5 },
//   { month: 'May', intensity: 3.9, target: 4.4 },
//   { month: 'Jun', intensity: 4.1, target: 4.4 },
// ];

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
  const avgWater = 'N/A';
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
          <p style={{ padding: '1rem', color: 'var(--color-text-muted)' }}>See the Water Efficiency tab for full details.</p>
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
  const { token } = useAuth();
  const [waterData, setWaterData] = useState([]);
  const [target, setTarget]       = useState(4.5);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [usage, baseline] = await Promise.all([
          apiService.getWaterUsage(token, 2026),
          apiService.getWaterBaseline(token)
        ]);

        const t = baseline.length > 0
          ? parseFloat((baseline[0].baseline_intensity * (1 - baseline[0].annual_target_pct / 100)).toFixed(3))
          : 4.5;
        setTarget(t);

        const formatted = usage.map(w => ({
          month:     w.month,
          intensity: w.intensity_l_per_kg,
          target:    t,
          status:    w.track_status
        }));
        setWaterData(formatted);
      } catch (err) {
        console.error('Water data failed to load', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  const onTrack = waterData.filter(w => w.status === 'on_track').length;
  const atRisk  = waterData.filter(w => w.status !== 'on_track').length;
  const latest  = waterData.at(-1);
  const worst   = waterData.reduce((a, b) => (b.intensity > a.intensity ? b : a), { intensity: 0 });

  if (loading) return <p style={{ padding: '2rem' }}>Loading water data…</p>;

  return (
    <>
      <div className="kpi-grid">
        <KpiCard icon="💧" iconBg="kpi-icon-teal"  label="Latest Intensity" value={latest?.intensity ?? '—'} unit="L/kg" delta={-0.9} deltaLabel={`vs target ${target} L/kg`} />
        <KpiCard icon="✅" iconBg="kpi-icon-green"  label="Months On Track" value={onTrack} unit="" />
        <KpiCard icon="⚠️" iconBg="kpi-icon-amber"  label="Months At Risk"  value={atRisk}  unit="" />
        <KpiCard icon="🎯" iconBg="kpi-icon-blue"   label="Annual Goal"     value="-2%"    unit="" deltaLabel="reduction vs last year" />
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
              const variance = (w.intensity - w.target).toFixed(2);
              const ok  = w.status === 'on_track';
              const pct = Math.min(100, (w.intensity / 6) * 100);
              return (
                <tr key={w.month}>
                  <td style={{ fontWeight: 600 }}>{w.month}</td>
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

      {worst.intensity > 0 && worst.status !== 'on_track' && (
        <div className="alert alert-info">
          <span>ℹ️</span>
          <span>{worst.month} recorded the highest intensity at {worst.intensity} L/kg. Review factory maintenance logs and irrigation schedules.</span>
        </div>
      )}
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
  const { token, canWrite, isManager } = useAuth();
  const [view, setView]           = useState('month');     // 'month' | 'rotation' | 'employees'
  const [estates, setEstates]     = useState([]);
  const [estateId, setEstateId]   = useState('');
  const [plan, setPlan]           = useState(null);        // current week plan
  const [rotation, setRotation]   = useState(null);
  const [employees, setEmployees] = useState([]);
  const [groups, setGroups]       = useState([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  // Search and sort state
  const [empSearch, setEmpSearch]     = useState('');
  const [empSort, setEmpSort]         = useState({ field: 'full_name', dir: 'asc' });
  const [assignSort, setAssignSort]   = useState({ field: 'block_code', dir: 'asc' });
  const [rotSort, setRotSort]         = useState({ field: 'round', dir: 'asc' });

  // Target editing state
  const [editingTarget, setEditingTarget] = useState(null); // assignment id being edited
  const [targetInputs, setTargetInputs]   = useState({});   // { assignmentId: value }

  // Employee modal state (null = closed, 'add' = add mode, employee obj = edit mode)
  const [empModal, setEmpModal]     = useState(null);
  const [empForm, setEmpForm]       = useState({
    employee_code: '', full_name: '', gender: 'F',
    hire_date: new Date().toISOString().slice(0, 10),
    employment_type: 'permanent', skill_type: 'plucker',
    daily_wage_lkr: '', group_id: '',
  });
  const [empSaving, setEmpSaving]   = useState(false);
  const [empError, setEmpError]     = useState('');

  // Delete confirmation state
  const [deleteTarget, setDeleteTarget] = useState(null); // employee obj
  const [deleting, setDeleting]         = useState(false);

  // Yield recording modal state
  const [yieldModal, setYieldModal]   = useState(false);
  const [yieldInputs, setYieldInputs] = useState({});  // { assignmentId: kg_string }
  const [yieldSaving, setYieldSaving] = useState(false);
  const [yieldError, setYieldError]   = useState('');

  // First day of the current month (YYYY-MM-01)
  const monthStart = (() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1).toLocaleDateString('en-CA');
  })();

  // Load estates on mount
  useEffect(() => {
    if (!token) return;
    apiService.getEstates(token)
      .then(data => {
        setEstates(data);
        if (data.length > 0) setEstateId(data[0].id);
      })
      .catch(() => {});
  }, [token]);

  // Load view data when estate or view tab changes
  useEffect(() => {
    if (!token || !estateId) return;
    setError('');
    setLoading(true);

    const load = async () => {
      try {
        if (view === 'month') {
          const plans = await apiService.getLabourPlans(token, { estateId, monthStart });
          if (plans.length > 0) {
            const detail = await apiService.getLabourPlan(token, plans[0].id);
            setPlan(detail);
          } else {
            setPlan(null);
          }
        } else if (view === 'rotation') {
          const r = await apiService.getRotation(token, estateId);
          setRotation(r.length > 0 ? r[0] : null);
        } else if (view === 'employees') {
          const [emps, grps] = await Promise.all([
            apiService.getEmployees(token, { estateId }),
            apiService.getWorkerGroups(token, estateId),
          ]);
          setEmployees(emps);
          setGroups(grps);
        }
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [token, estateId, view, monthStart]);

  const blankForm = {
    employee_code: '', full_name: '', gender: 'F',
    hire_date: new Date().toISOString().slice(0, 10),
    employment_type: 'permanent', skill_type: 'plucker',
    daily_wage_lkr: '', group_id: '',
  };

  const openAddModal = () => {
    setEmpForm(blankForm);
    setEmpError('');
    setEmpModal('add');
  };

  const openEditModal = (emp) => {
    setEmpForm({
      employee_code:   emp.employee_code,
      full_name:       emp.full_name,
      gender:          emp.gender || 'F',
      hire_date:       emp.hire_date || '',
      employment_type: emp.employment_type || 'permanent',
      skill_type:      emp.skill_type || 'plucker',
      daily_wage_lkr:  emp.daily_wage_lkr || '',
      group_id:        emp.group_id || '',
    });
    setEmpError('');
    setEmpModal(emp);   // store the employee object so we know it's edit mode
  };

  const handleSaveEmployee = async () => {
    if (!empForm.full_name || (empModal === 'add' && !empForm.employee_code)) {
      setEmpError('Employee code and full name are required.');
      return;
    }
    setEmpSaving(true); setEmpError('');
    try {
      if (empModal === 'add') {
        await apiService.createEmployee(token, { ...empForm, estate_id: estateId });
      } else {
        // empModal holds the original employee object
        await apiService.updateEmployee(token, empModal.id, {
          full_name:       empForm.full_name,
          gender:          empForm.gender,
          employment_type: empForm.employment_type,
          skill_type:      empForm.skill_type,
          daily_wage_lkr:  empForm.daily_wage_lkr || null,
          group_id:        empForm.group_id,
        });
      }
      setEmpModal(null);
      const [emps, grps] = await Promise.all([
        apiService.getEmployees(token, { estateId }),
        apiService.getWorkerGroups(token, estateId),
      ]);
      setEmployees(emps);
      setGroups(grps);
    } catch (e) {
      setEmpError(e.message);
    } finally {
      setEmpSaving(false);
    }
  };

  const handleDeleteEmployee = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await apiService.deleteEmployee(token, deleteTarget.id);
      setDeleteTarget(null);
      const [emps, grps] = await Promise.all([
        apiService.getEmployees(token, { estateId }),
        apiService.getWorkerGroups(token, estateId),
      ]);
      setEmployees(emps);
      setGroups(grps);
    } catch (e) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  const openYieldModal = () => {
    const pre = {};
    (plan?.assignments || []).forEach(a => {
      pre[a.id] = a.actual_yield_kg != null ? String(a.actual_yield_kg) : '';
    });
    setYieldInputs(pre);
    setYieldError('');
    setYieldModal(true);
  };

  const handleSaveYield = async () => {
    const yields = Object.entries(yieldInputs)
      .filter(([, v]) => v !== '' && !isNaN(parseFloat(v)))
      .map(([assignment_id, v]) => ({ assignment_id, actual_yield_kg: parseFloat(v) }));
    if (yields.length === 0) {
      setYieldError('Enter at least one actual yield value.');
      return;
    }
    setYieldSaving(true); setYieldError('');
    try {
      await apiService.recordPlanYield(token, plan.id, yields);
      setYieldModal(false);
      // Reload plan to reflect saved actuals
      const updated = await apiService.getLabourPlan(token, plan.id);
      setPlan(updated);
    } catch (e) {
      setYieldError(e.message);
    } finally {
      setYieldSaving(false);
    }
  };

  // ── KPIs derived from plan assignments
  const assignments = plan?.assignments || [];
  const totalWorkers  = assignments.reduce((s, a) => s + (a.group_capacity || 0), 0);
  const totalTarget   = assignments.reduce((s, a) => s + (a.expected_yield_kg || 0), 0);
  const totalActual   = assignments.reduce((s, a) => s + (a.actual_yield_kg || 0), 0);
  const overallEff    = totalTarget > 0 ? ((totalActual / totalTarget) * 100).toFixed(1) : '—';

  // Helper functions for search and sort
  const filterEmployees = (emps) => {
    if (!empSearch) return emps;
    const q = empSearch.toLowerCase();
    return emps.filter(e =>
      e.full_name?.toLowerCase().includes(q) ||
      e.employee_code?.toLowerCase().includes(q) ||
      e.group_code?.toLowerCase().includes(q) ||
      e.skill_type?.toLowerCase().includes(q)
    );
  };

  const sortArray = (arr, { field, dir }) => {
    return [...arr].sort((a, b) => {
      let aVal = a[field];
      let bVal = b[field];
      if (typeof aVal === 'string') {
        aVal = aVal?.toLowerCase() || '';
        bVal = bVal?.toLowerCase() || '';
      }
      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return dir === 'asc' ? cmp : -cmp;
    });
  };

  const toggleSort = (field, setter) => {
    setter(s => ({
      field,
      dir: s.field === field && s.dir === 'asc' ? 'desc' : 'asc'
    }));
  };

  const sortAndFilterEmployees = (emps) => {
    return sortArray(filterEmployees(emps), empSort);
  };

  const filteredEmployees = sortAndFilterEmployees(employees);
  const sortedAssignments = sortArray(assignments, assignSort);
  const sortedRotationRows = rotation ? Object.entries(rotation.matrix).sort(([a], [b]) => {
    const aNum = parseInt(a);
    const bNum = parseInt(b);
    return rotSort.dir === 'asc' ? aNum - bNum : bNum - aNum;
  }) : [];

  const SortHeader = ({ label, field, sort, onSort, style = {} }) => (
    <th style={{
      cursor: 'pointer', userSelect: 'none', position: 'relative',
      backgroundColor: sort.field === field ? 'rgba(var(--color-primary-rgb, 37,99,235),0.08)' : '',
      ...style
    }}
    onClick={() => onSort(field)}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {label}
        {sort.field === field && (
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-primary)' }}>
            {sort.dir === 'asc' ? '↑' : '↓'}
          </span>
        )}
      </div>
    </th>
  );

  const subBtnStyle = (v) => ({
    padding: '6px 16px', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600,
    fontSize: '0.8125rem', transition: 'all 0.15s',
    background: view === v ? 'var(--color-primary)' : 'var(--color-surface-2)',
    color:      view === v ? '#fff' : 'var(--color-text-muted)',
  });

  return (
    <>
      {/* ── Estate selector + sub-nav ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
        <select
          value={estateId}
          onChange={e => setEstateId(e.target.value)}
          disabled={!canWrite}
          style={{
            padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)',
            background: 'var(--color-surface-2)', color: 'var(--color-text)',
            fontSize: '0.875rem', fontWeight: 600,
            cursor: canWrite ? 'pointer' : 'not-allowed', opacity: canWrite ? 1 : 0.7,
          }}
        >
          {estates.length === 0 && <option value="">Loading estates…</option>}
          {estates.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
        </select>

        <div style={{ display: 'flex', gap: 6 }}>
          <button style={subBtnStyle('month')}     onClick={() => setView('month')}>This Month</button>
          <button style={subBtnStyle('rotation')}  onClick={() => setView('rotation')}>Rotation</button>
          <button style={subBtnStyle('employees')} onClick={() => setView('employees')}>Employees</button>
        </div>
      </div>

      {/* ── Error / Loading ── */}
      {error && (
        <div style={{ padding: '12px 16px', borderRadius: 8, background: 'rgba(220,38,38,0.08)',
                      color: 'var(--color-danger)', marginBottom: 'var(--space-4)', fontSize: '0.875rem' }}>
          {error}
        </div>
      )}
      {loading && (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)' }}>
          Loading…
        </div>
      )}

      {/* ── VIEW: This Month ── */}
      {!loading && view === 'month' && (
        <>
          {/* KPI row */}
          <div className="kpi-grid">
            <KpiCard icon="👥" iconBg="kpi-icon-blue"  label="Total Workers"         value={totalWorkers || '—'} unit="" />
            <KpiCard icon="🎯" iconBg="kpi-icon-green" label="Target (kg)"            value={totalTarget ? Math.round(totalTarget).toLocaleString() : '—'} unit="kg" />
            <KpiCard icon="📦" iconBg="kpi-icon-teal"  label="Actual Output (kg)"     value={totalActual ? Math.round(totalActual).toLocaleString() : '—'} unit="kg" />
            <KpiCard icon="⚡" iconBg="kpi-icon-amber" label="Overall Efficiency"      value={overallEff === '—' ? '—' : `${overallEff}%`} unit="" />
          </div>

          {/* Plan meta row */}
          {plan && (
            <div style={{ display: 'flex', gap: 12, marginBottom: 'var(--space-4)', flexWrap: 'wrap' }}>
              <span className="badge badge-neutral">Month of {plan.period_start}</span>
              {plan.cycle_name && (
                <span className="badge badge-neutral">
                  {plan.cycle_name} · Round {plan.current_round}/{plan.total_rounds}
                </span>
              )}
            </div>
          )}

          {/* Assignments table */}
          {!plan ? (
            <div style={{ padding: 48, textAlign: 'center', color: 'var(--color-text-muted)',
                          background: 'var(--color-surface-2)', borderRadius: 12 }}>
              <div style={{ fontSize: '2rem', marginBottom: 8 }}>📋</div>
              <p>No labour plan for this month yet.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <div className="table-header-bar">
                <div>
                  <div className="table-title">Block Assignments — {monthStart}</div>
                  <div className="table-subtitle">
                    Rotation-generated assignments · {assignments.length} blocks · manual overrides shown
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span className="badge badge-neutral">{assignments.length} blocks</span>
                  {(canWrite || isManager) && (
                    <button
                      onClick={openYieldModal}
                      style={{
                        padding: '7px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
                        background: 'var(--color-primary)', color: '#fff', fontWeight: 600,
                        fontSize: '0.8125rem',
                      }}
                    >
                      Record Yield
                    </button>
                  )}
                </div>
              </div>
              <table>
                <thead>
                  <tr>
                    <SortHeader label="Block" field="block_code" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <SortHeader label="Group" field="group_name" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <SortHeader label="Workers" field="group_capacity" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <SortHeader label="Target (kg)" field="expected_yield_kg" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <SortHeader label="Actual (kg)" field="actual_yield_kg" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <th>Efficiency</th>
                    <th>Progress</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedAssignments.map(a => {
                    const exp = a.expected_yield_kg || 0;
                    const act = a.actual_yield_kg   || 0;
                    const eff = exp > 0 ? ((act / exp) * 100) : 0;
                    const pct = exp > 0 ? Math.min(100, (act / exp) * 100) : 0;
                    const effColor = act === 0 ? 'var(--color-text-muted)'
                                   : eff >= 100 ? 'var(--color-success)'
                                   : eff >= 90  ? 'var(--color-warning)'
                                   : 'var(--color-danger)';
                    const barClass = eff >= 100 ? 'progress-green' : eff >= 90 ? 'progress-amber' : 'progress-red';
                    return (
                      <tr key={a.id}>
                        <td style={{ fontWeight: 700, color: 'var(--color-text)' }}>
                          {a.block_code}
                          {a.is_manual_override && (
                            <span title={a.override_reason || 'Manually overridden'}
                                  style={{ marginLeft: 6, fontSize: '0.7rem', color: 'var(--color-warning)', fontWeight: 600 }}>
                              ✎
                            </span>
                          )}
                        </td>
                        <td style={{ fontSize: '0.875rem' }}>
                          <div style={{ fontWeight: 600, color: 'var(--color-text)' }}>{a.group_name || '—'}</div>
                          {a.is_manual_override && a.original_group_name && (
                            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                              was: {a.original_group_name}
                            </div>
                          )}
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span>👤</span>
                            <span style={{ fontWeight: 600 }}>{a.group_capacity || '—'}</span>
                          </div>
                        </td>
                        <td style={{ fontWeight: 700 }}>
                          {editingTarget === a.id ? (
                            <input
                              type="number"
                              min="0"
                              step="0.1"
                              value={targetInputs[a.id] ?? exp}
                              onChange={e => setTargetInputs(p => ({ ...p, [a.id]: parseFloat(e.target.value) || 0 }))}
                              onBlur={() => setEditingTarget(null)}
                              onKeyDown={e => e.key === 'Enter' && setEditingTarget(null)}
                              autoFocus
                              style={{
                                width: '100%', padding: '4px 8px', borderRadius: 4, border: '2px solid var(--color-primary)',
                                background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.9rem',
                                fontWeight: 700
                              }}
                            />
                          ) : (
                            <span
                              onClick={() => {
                                setEditingTarget(a.id);
                                setTargetInputs(p => ({ ...p, [a.id]: exp }));
                              }}
                              style={{ cursor: 'pointer', padding: '4px 8px', borderRadius: 4,
                                       hover: { background: 'var(--color-surface-2)' } }}
                              title="Click to edit"
                            >
                              {exp ? Math.round(exp).toLocaleString() : '—'}
                            </span>
                          )}
                        </td>
                        <td style={{ fontWeight: 700 }}>{act ? Math.round(act).toLocaleString() : '—'}</td>
                        <td style={{ fontWeight: 700, color: effColor }}>
                          {act === 0 ? '—' : `${eff.toFixed(1)}%`}
                        </td>
                        <td style={{ minWidth: 120 }}>
                          <div className="progress-wrap">
                            {pct > 0 && <div className={`progress-bar ${barClass}`} style={{ width: `${pct}%` }} />}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Efficiency Summary (shows once actuals are recorded) ── */}
          {plan && totalActual > 0 && (() => {
            const planEff = totalTarget > 0 ? (totalActual / totalTarget * 100) : 0;
            const kgPerWorker = totalWorkers > 0 ? (totalActual / totalWorkers) : 0;
            const variance = totalActual - totalTarget;
            const effColor = planEff >= 100 ? 'var(--color-success)' : planEff >= 90 ? 'var(--color-warning)' : 'var(--color-danger)';
            const recorded = assignments.filter(a => a.actual_yield_kg != null).length;
            return (
              <div className="section-card" style={{ marginTop: 'var(--space-6)' }}>
                <div className="section-card-header">
                  <div className="section-card-title">
                    <div className="section-card-title-icon">⚡</div>
                    Yield Efficiency Report
                  </div>
                  <span className="badge badge-neutral">{recorded}/{assignments.length} blocks recorded</span>
                </div>
                <div className="section-card-body">
                  {/* Summary stats */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, marginBottom: 24 }}>
                    {[
                      { label: 'Plan Efficiency', value: `${planEff.toFixed(1)}%`, color: effColor },
                      { label: 'Actual Total', value: `${Math.round(totalActual).toLocaleString()} kg`, color: 'var(--color-text)' },
                      { label: 'Expected Total', value: `${Math.round(totalTarget).toLocaleString()} kg`, color: 'var(--color-text-muted)' },
                      { label: 'Variance', value: `${variance >= 0 ? '+' : ''}${Math.round(variance).toLocaleString()} kg`, color: variance >= 0 ? 'var(--color-success)' : 'var(--color-danger)' },
                      { label: 'kg / Worker', value: kgPerWorker > 0 ? `${Math.round(kgPerWorker).toLocaleString()}` : '—', color: 'var(--color-text)' },
                    ].map(({ label, value, color }) => (
                      <div key={label} style={{ padding: '14px 16px', borderRadius: 10, background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 4 }}>{label}</div>
                        <div style={{ fontSize: '1.25rem', fontWeight: 700, color }}>{value}</div>
                      </div>
                    ))}
                  </div>
                  {/* Per-block efficiency bars */}
                  {assignments.filter(a => a.actual_yield_kg != null).map(a => {
                    const exp = a.expected_yield_kg || 0;
                    const act = parseFloat(a.actual_yield_kg);
                    const eff = exp > 0 ? (act / exp * 100) : 0;
                    const pct = Math.min(120, eff);
                    const barClass = eff >= 100 ? 'progress-green' : eff >= 90 ? 'progress-amber' : 'progress-red';
                    const col = eff >= 100 ? 'var(--color-success)' : eff >= 90 ? 'var(--color-warning)' : 'var(--color-danger)';
                    return (
                      <div key={a.id} style={{ marginBottom: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: '0.875rem' }}>
                          <span style={{ fontWeight: 600 }}>{a.block_code} <span style={{ color: 'var(--color-text-muted)', fontWeight: 400, fontSize: '0.8rem' }}>{a.group_name || ''}</span></span>
                          <span style={{ fontWeight: 700, color: col }}>{eff.toFixed(1)}%
                            <span style={{ color: 'var(--color-text-muted)', fontWeight: 400, fontSize: '0.8rem', marginLeft: 8 }}>
                              {Math.round(act).toLocaleString()} / {Math.round(exp).toLocaleString()} kg
                            </span>
                          </span>
                        </div>
                        <div className="progress-wrap" style={{ height: 8 }}>
                          <div className={`progress-bar ${barClass}`} style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}
        </>
      )}

      {/* ── VIEW: Rotation Matrix ── */}
      {!loading && view === 'rotation' && (
        rotation ? (
          <div className="table-wrap">
            <div className="table-header-bar">
              <div>
                <div className="table-title">{rotation.cycle_name}</div>
                <div className="table-subtitle">
                  {rotation.total_rounds}-round cycle · currently on Round {rotation.current_round}
                </div>
              </div>
              <span className="badge badge-neutral">{rotation.total_rounds} rounds</span>
            </div>

            {/* Progress indicator */}
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', gap: 8 }}>
                {Array.from({ length: rotation.total_rounds }, (_, i) => i + 1).map(rn => (
                  <div key={rn} style={{
                    flex: 1, height: 8, borderRadius: 4,
                    background: rn < rotation.current_round  ? 'var(--color-success)'
                              : rn === rotation.current_round ? 'var(--color-primary)'
                              : 'var(--color-surface-2)',
                    transition: 'background 0.3s',
                  }} title={`Round ${rn}${rn === rotation.current_round ? ' ← current' : ''}`} />
                ))}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                Round {rotation.current_round} of {rotation.total_rounds} — {Math.round((rotation.current_round / rotation.total_rounds) * 100)}% through cycle
              </div>
            </div>

            <table>
              <thead>
                <tr>
                  <SortHeader label="Round" field="round" sort={rotSort} onSort={(f) => toggleSort(f, setRotSort)} />
                  {(rotation.matrix[1] || []).map(b => <th key={b.block_code}>{b.block_code}</th>)}
                </tr>
              </thead>
              <tbody>
                {sortedRotationRows.map(([rn, cells]) => (
                  <tr key={rn} style={{
                    background: parseInt(rn) === rotation.current_round
                      ? 'rgba(var(--color-primary-rgb, 37,99,235), 0.06)' : '',
                  }}>
                    <td style={{ fontWeight: 700 }}>
                      Round {rn}
                      {parseInt(rn) === rotation.current_round && (
                        <span className="badge badge-success" style={{ marginLeft: 8, fontSize: '0.65rem' }}>current</span>
                      )}
                    </td>
                    {cells.map(c => (
                      <td key={c.block_code} style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                        <div style={{ fontWeight: 600, color: 'var(--color-text)' }}>{c.group_code}</div>
                        <div style={{ fontSize: '0.7rem' }}>{c.capacity} workers</div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--color-text-muted)',
                        background: 'var(--color-surface-2)', borderRadius: 12 }}>
            <div style={{ fontSize: '2rem', marginBottom: 8 }}>🔄</div>
            <p>No active rotation cycle for this estate.</p>
          </div>
        )
      )}

      {/* ── VIEW: Employees ── */}
      {!loading && view === 'employees' && (
        <>
          {/* Groups summary */}
          {groups.length > 0 && (
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 'var(--space-5)' }}>
              {groups.map(g => (
                <div key={g.id} style={{
                  padding: '12px 16px', borderRadius: 10, background: 'var(--color-surface-2)',
                  border: '1px solid var(--color-border)', minWidth: 160,
                }}>
                  <div style={{ fontWeight: 700, color: 'var(--color-text)', marginBottom: 4 }}>{g.group_code}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{g.group_name}</div>
                  <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--color-primary)' }}>
                      {g.current_headcount}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                      / {g.capacity} capacity
                    </span>
                  </div>
                  {g.supervisor_name && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                      Supervisor: {g.supervisor_name}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="table-wrap">
            <div className="table-header-bar">
              <div>
                <div className="table-title">Field Employees</div>
                <div className="table-subtitle">{employees.length} active employees</div>
              </div>
              {(canWrite || isManager) && (
                <button
                  onClick={openAddModal}
                  style={{
                    padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8125rem',
                  }}
                >
                  + Add Employee
                </button>
              )}
            </div>

            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface-2)' }}>
              <input
                type="text"
                placeholder="Search by name, code, group, or role…"
                value={empSearch}
                onChange={e => setEmpSearch(e.target.value)}
                style={{
                  width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--color-border)',
                  background: 'var(--color-surface)', color: 'var(--color-text)',
                  fontSize: '0.875rem'
                }}
              />
              {empSearch && (
                <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                  {filteredEmployees.length} of {employees.length} employees match
                </div>
              )}
            </div>

            <table>
              <thead>
                <tr>
                  <SortHeader label="Code" field="employee_code" sort={empSort} onSort={(f) => toggleSort(f, setEmpSort)} />
                  <SortHeader label="Name" field="full_name" sort={empSort} onSort={(f) => toggleSort(f, setEmpSort)} />
                  <SortHeader label="Group" field="group_code" sort={empSort} onSort={(f) => toggleSort(f, setEmpSort)} />
                  <SortHeader label="Role" field="skill_type" sort={empSort} onSort={(f) => toggleSort(f, setEmpSort)} />
                  <SortHeader label="Type" field="employment_type" sort={empSort} onSort={(f) => toggleSort(f, setEmpSort)} />
                  <SortHeader label="Wage / day" field="daily_wage_lkr" sort={empSort} onSort={(f) => toggleSort(f, setEmpSort)} />
                  <SortHeader label="Hire Date" field="hire_date" sort={empSort} onSort={(f) => toggleSort(f, setEmpSort)} />
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.length === 0 ? (
                  <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 32 }}>
                    {empSearch ? 'No employees match your search.' : 'No employees found for this estate.'}
                  </td></tr>
                ) : filteredEmployees.map(emp => (
                  <tr key={emp.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>{emp.employee_code}</td>
                    <td style={{ fontWeight: 600 }}>{emp.full_name}</td>
                    <td style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>{emp.group_code || '—'}</td>
                    <td>
                      <span className={`badge ${emp.skill_type === 'supervisor' ? 'badge-warning' : 'badge-neutral'}`}>
                        {emp.skill_type}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>{emp.employment_type}</td>
                    <td style={{ fontWeight: 600 }}>
                      {emp.daily_wage_lkr ? `Rs. ${Number(emp.daily_wage_lkr).toLocaleString()}` : '—'}
                    </td>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>{emp.hire_date}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {canWrite ? (
                          <>
                            <button
                              onClick={() => openEditModal(emp)}
                              style={{
                                padding: '4px 12px', borderRadius: 6, border: '1px solid var(--color-border)',
                                background: 'transparent', color: 'var(--color-text)', cursor: 'pointer',
                                fontSize: '0.75rem', fontWeight: 600,
                              }}
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => setDeleteTarget(emp)}
                              style={{
                                padding: '4px 12px', borderRadius: 6, border: '1px solid rgba(220,38,38,0.3)',
                                background: 'transparent', color: 'var(--color-danger)', cursor: 'pointer',
                                fontSize: '0.75rem', fontWeight: 600,
                              }}
                            >
                              Delete
                            </button>
                          </>
                        ) : (
                          <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>—</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── Add / Edit Employee Modal ── */}
          {empModal !== null && (
            <div style={{
              position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
            }}>
              <div style={{
                background: 'var(--color-surface)', borderRadius: 16, padding: 32,
                width: '100%', maxWidth: 480, boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                maxHeight: '90vh', overflowY: 'auto',
              }}>
                <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 20 }}>
                  {empModal === 'add' ? 'Add New Employee' : `Edit — ${empModal.full_name}`}
                </div>

                {empError && (
                  <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(220,38,38,0.1)',
                                color: 'var(--color-danger)', marginBottom: 16, fontSize: '0.875rem' }}>
                    {empError}
                  </div>
                )}

                {/* Employee Code — readonly on edit */}
                <div style={{ marginBottom: 14 }}>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600,
                                  color: 'var(--color-text-muted)', marginBottom: 4 }}>
                    Employee Code {empModal !== 'add' && <span style={{ color: 'var(--color-text-muted)', fontWeight: 400 }}>(read-only)</span>}
                  </label>
                  <input
                    type="text"
                    value={empForm.employee_code}
                    readOnly={empModal !== 'add'}
                    onChange={e => empModal === 'add' && setEmpForm(p => ({ ...p, employee_code: e.target.value }))}
                    style={{
                      width: '100%', padding: '8px 12px', borderRadius: 8, boxSizing: 'border-box',
                      border: '1px solid var(--color-border)',
                      background: empModal !== 'add' ? 'var(--color-surface-2)' : 'var(--color-surface-2)',
                      color: empModal !== 'add' ? 'var(--color-text-muted)' : 'var(--color-text)',
                      fontSize: '0.875rem', cursor: empModal !== 'add' ? 'not-allowed' : 'text',
                    }}
                  />
                </div>

                {/* Text fields */}
                {[
                  ['full_name',      'Full Name',        'text'],
                  ['hire_date',      'Hire Date',        'date'],
                  ['daily_wage_lkr', 'Daily Wage (LKR)', 'number'],
                ].map(([field, label, type]) => (
                  <div key={field} style={{ marginBottom: 14 }}>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600,
                                    color: 'var(--color-text-muted)', marginBottom: 4 }}>
                      {label}
                    </label>
                    <input
                      type={type}
                      value={empForm[field]}
                      readOnly={field === 'hire_date' && empModal !== 'add'}
                      onChange={e => setEmpForm(p => ({ ...p, [field]: e.target.value }))}
                      style={{
                        width: '100%', padding: '8px 12px', borderRadius: 8, boxSizing: 'border-box',
                        border: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
                        color: 'var(--color-text)', fontSize: '0.875rem',
                      }}
                    />
                  </div>
                ))}

                {/* Select fields */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                  {[
                    ['gender',          'Gender',     [['M','Male'],['F','Female'],['O','Other']]],
                    ['skill_type',      'Skill',      [['plucker','Plucker'],['supervisor','Supervisor'],['general','General'],['driver','Driver']]],
                    ['employment_type', 'Employment', [['permanent','Permanent'],['casual','Casual'],['seasonal','Seasonal']]],
                    ['group_id',        'Group',      [['','— None —'], ...groups.map(g => [g.id, g.group_name])]],
                  ].map(([field, label, opts]) => (
                    <div key={field}>
                      <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600,
                                      color: 'var(--color-text-muted)', marginBottom: 4 }}>
                        {label}
                      </label>
                      <select
                        value={empForm[field]}
                        onChange={e => setEmpForm(p => ({ ...p, [field]: e.target.value }))}
                        style={{
                          width: '100%', padding: '8px 10px', borderRadius: 8,
                          border: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
                          color: 'var(--color-text)', fontSize: '0.8125rem',
                        }}
                      >
                        {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    </div>
                  ))}
                </div>

                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
                  <button
                    onClick={() => { setEmpModal(null); setEmpError(''); }}
                    style={{
                      padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)',
                      background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600,
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveEmployee}
                    disabled={empSaving}
                    style={{
                      padding: '8px 20px', borderRadius: 8, border: 'none',
                      background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontWeight: 600,
                      opacity: empSaving ? 0.7 : 1,
                    }}
                  >
                    {empSaving ? 'Saving…' : empModal === 'add' ? 'Add Employee' : 'Save Changes'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ── Delete Confirmation Modal ── */}
          {deleteTarget && (
            <div style={{
              position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
            }}>
              <div style={{
                background: 'var(--color-surface)', borderRadius: 16, padding: 32,
                width: '100%', maxWidth: 400, boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
              }}>
                <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 8 }}>Delete Employee</div>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: 8 }}>
                  Are you sure you want to deactivate:
                </p>
                <div style={{
                  padding: '10px 14px', borderRadius: 8, background: 'var(--color-surface-2)',
                  marginBottom: 20, border: '1px solid var(--color-border)',
                }}>
                  <div style={{ fontWeight: 700 }}>{deleteTarget.full_name}</div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                    {deleteTarget.employee_code}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                    Group: {deleteTarget.group_code || '—'} · {deleteTarget.skill_type}
                  </div>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: 20 }}>
                  The employee will be marked inactive and removed from their group. Historical assignment records are preserved.
                </p>
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => setDeleteTarget(null)}
                    disabled={deleting}
                    style={{
                      padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)',
                      background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600,
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDeleteEmployee}
                    disabled={deleting}
                    style={{
                      padding: '8px 20px', borderRadius: 8, border: 'none',
                      background: 'var(--color-danger)', color: '#fff', cursor: 'pointer', fontWeight: 600,
                      opacity: deleting ? 0.7 : 1,
                    }}
                  >
                    {deleting ? 'Deleting…' : 'Yes, Deactivate'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Record Yield Modal (top-level so it works from any sub-view) ── */}
      {yieldModal && plan && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div style={{
            background: 'var(--color-surface)', borderRadius: 16, padding: 32,
            width: '100%', maxWidth: 560, boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
            maxHeight: '90vh', overflowY: 'auto',
          }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 4 }}>
              Record Actual Yield
            </div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginBottom: 20 }}>
              {plan.period_start} · {plan.estate_name} — enter harvested kg per block
            </div>

            {yieldError && (
              <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(220,38,38,0.1)',
                            color: 'var(--color-danger)', marginBottom: 16, fontSize: '0.875rem' }}>
                {yieldError}
              </div>
            )}

            <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 20 }}>
              <thead>
                <tr>
                  {['Block', 'Group', 'Expected (kg)', 'Actual (kg)'].map(h => (
                    <th key={h} style={{
                      textAlign: 'left', padding: '6px 8px', fontSize: '0.75rem',
                      color: 'var(--color-text-muted)', borderBottom: '1px solid var(--color-border)',
                      fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em',
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {plan.assignments.map(a => (
                  <tr key={a.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '10px 8px', fontWeight: 700, fontSize: '0.9rem' }}>{a.block_code}</td>
                    <td style={{ padding: '10px 8px', fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                      {a.group_name || '—'}
                    </td>
                    <td style={{ padding: '10px 8px', fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                      {a.expected_yield_kg != null ? Math.round(a.expected_yield_kg).toLocaleString() : '—'}
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <input
                        type="number"
                        min="0"
                        step="0.1"
                        placeholder="e.g. 24500"
                        value={yieldInputs[a.id] ?? ''}
                        onChange={e => setYieldInputs(prev => ({ ...prev, [a.id]: e.target.value }))}
                        style={{
                          width: '100%', padding: '7px 10px', borderRadius: 6, boxSizing: 'border-box',
                          border: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
                          color: 'var(--color-text)', fontSize: '0.875rem',
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button
                onClick={() => { setYieldModal(false); setYieldError(''); }}
                disabled={yieldSaving}
                style={{
                  padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)',
                  background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveYield}
                disabled={yieldSaving}
                style={{
                  padding: '8px 24px', borderRadius: 8, border: 'none',
                  background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontWeight: 600,
                  opacity: yieldSaving ? 0.7 : 1,
                }}
              >
                {yieldSaving ? 'Saving…' : 'Save Yield'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ── Tab: Yield Predictions ──────────────────────────────────────────────── */
function YieldPredictionTab() {
  const { token } = useAuth();
  const [estates, setEstates] = useState([]);
  const [estateId, setEstateId] = useState('');
  const [year, setYear] = useState(2026);
  const [month, setMonth] = useState(6);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Load estates on mount
  useEffect(() => {
    if (!token) return;
    apiService.getEstates(token)
      .then(data => {
        setEstates(data);
        if (data.length > 0) {
          setEstateId(data[0].id);
        }
      })
      .catch(err => setError('Failed to load estates: ' + err.message));
  }, [token]);

  // Load predictions when estate/month changes
  useEffect(() => {
    if (!token || !estateId) {
      setPredictions([]);
      return;
    }
    setLoading(true);
    setError('');
    const params = { estateId, year, month };
    apiService.getPredictions(token, params)
      .then(data => {
        if (Array.isArray(data)) {
          setPredictions(data);
        } else {
          setPredictions([]);
          setError('Invalid response format');
        }
      })
      .catch(e => {
        setError('Error loading predictions: ' + (e.message || 'Unknown error'));
        setPredictions([]);
      })
      .finally(() => setLoading(false));
  }, [token, estateId, year, month]);

  const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const estate = estates.find(e => e.id === estateId);

  // Sort by predicted yield
  const sortedPredictions = [...predictions].sort((a, b) =>
    (b.predicted_yield_kg || 0) - (a.predicted_yield_kg || 0)
  );

  // Calculate summary stats
  const totalPredicted = predictions.reduce((sum, p) => sum + (p.predicted_yield_kg || 0), 0);
  const avgPredicted = predictions.length > 0 ? totalPredicted / predictions.length : 0;
  const maxPredicted = predictions.length > 0 ? Math.max(...predictions.map(p => p.predicted_yield_kg || 0)) : 0;
  const minPredicted = predictions.length > 0 ? Math.min(...predictions.map(p => p.predicted_yield_kg || 0)) : 0;

  const totalConfidenceLow = predictions.reduce((sum, p) => sum + (p.confidence_low || 0), 0);
  const totalConfidenceHigh = predictions.reduce((sum, p) => sum + (p.confidence_high || 0), 0);
  const avgConfidenceRange = totalPredicted > 0
    ? Math.round(((totalConfidenceHigh - totalConfidenceLow) / totalPredicted) * 100)
    : 0;

  return (
    <>
      {/* ── Controls ── */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: 'var(--space-6)' }}>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Estate
          </div>
          <select value={estateId} onChange={e => setEstateId(e.target.value)} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', fontSize: '0.9375rem' }}>
            {estates.length === 0 && <option value="">Loading…</option>}
            {estates.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
        </div>

        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Month
          </div>
          <select value={month} onChange={e => setMonth(parseInt(e.target.value))} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', fontSize: '0.9375rem' }}>
            {MONTH_NAMES.map((name, idx) => <option key={idx} value={idx + 1}>{name}</option>)}
          </select>
        </div>

        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Year
          </div>
          <input type="number" value={year} onChange={e => setYear(parseInt(e.target.value))} min="2020" max="2030" style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', fontSize: '0.9375rem', width: 80 }} />
        </div>
      </div>

      {/* ── Error ── */}
      {error && (
        <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(220,38,38,0.08)', color: 'var(--color-danger)', marginBottom: 20, fontSize: '0.875rem', border: '1px solid rgba(220,38,38,0.2)' }}>
          {error}
        </div>
      )}

      {/* ── Summary Cards ── */}
      {!loading && predictions.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-4)', marginBottom: 'var(--space-6)' }}>
          <div style={{ padding: '16px', borderRadius: 10, background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Total Predicted</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--color-primary)' }}>{(totalPredicted / 1000).toFixed(1)}t</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>{predictions.length} blocks</div>
          </div>

          <div style={{ padding: '16px', borderRadius: 10, background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Average Per Block</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--color-primary)' }}>{(avgPredicted / 1000).toFixed(2)}t</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>Mean yield</div>
          </div>

          <div style={{ padding: '16px', borderRadius: 10, background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Range</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--color-success)' }}>{(maxPredicted / 1000).toFixed(2)}t</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>Max: {(maxPredicted / 1000).toFixed(2)}t</div>
          </div>

          <div style={{ padding: '16px', borderRadius: 10, background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Confidence Range</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--color-primary)' }}>±{avgConfidenceRange}%</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>Low to High</div>
          </div>
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div style={{ padding: 48, textAlign: 'center', background: 'var(--color-surface-2)', borderRadius: 14, border: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 12 }}>🔮</div>
          <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: 6 }}>Predicting yields…</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>ML model generating forecasts</div>
        </div>
      )}

      {/* ── Charts ── */}
      {!loading && predictions.length > 0 && (
        <>
          {/* Bar Chart: Predicted Yield by Block */}
          <div style={{ marginBottom: 'var(--space-6)' }}>
            <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-text)', marginBottom: 'var(--space-4)' }}>
              📊 Predicted Yield by Block
            </div>
            <div style={{
              background: 'var(--color-surface-2)',
              borderRadius: 10,
              border: '1px solid var(--color-border)',
              padding: '20px',
              minHeight: 300,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'flex-end',
            }}>
              {/* Simplified Bar Chart */}
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 250, justifyContent: 'space-around' }}>
                {sortedPredictions.slice(0, 12).map(pred => {
                  const maxYield = Math.max(...sortedPredictions.map(p => p.predicted_yield_kg || 0));
                  const barHeight = (pred.predicted_yield_kg / maxYield) * 220;
                  const color = pred.predicted_yield_kg > maxYield * 0.7 ? 'var(--color-success)' : 'var(--color-primary)';
                  return (
                    <div key={pred.block_id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flex: 1 }}>
                      <div title={`${(pred.predicted_yield_kg / 1000).toFixed(2)}t`}
                        style={{
                          width: '100%',
                          height: barHeight,
                          background: color,
                          borderRadius: '4px 4px 0 0',
                          opacity: 0.8,
                          transition: 'opacity 0.2s',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={e => e.target.style.opacity = 1}
                        onMouseLeave={e => e.target.style.opacity = 0.8}
                      />
                      <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>
                        {pred.block_code}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 12, textAlign: 'center' }}>
                Top 12 blocks by predicted yield (in tonnes)
              </div>
            </div>
          </div>

          {/* Confidence Range Visualization */}
          <div style={{ marginBottom: 'var(--space-6)' }}>
            <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-text)', marginBottom: 'var(--space-4)' }}>
              📈 Confidence Ranges (Low to High Estimate)
            </div>
            <div style={{
              background: 'var(--color-surface-2)',
              borderRadius: 10,
              border: '1px solid var(--color-border)',
              padding: '20px',
            }}>
              {sortedPredictions.slice(0, 8).map(pred => {
                const pred_kg = pred.predicted_yield_kg || 0;
                const low_kg = pred.confidence_low || 0;
                const high_kg = pred.confidence_high || 0;
                const maxEstimate = Math.max(...sortedPredictions.map(p => p.confidence_high || 0));

                const predPercent = (pred_kg / maxEstimate) * 100;
                const lowPercent = (low_kg / maxEstimate) * 100;
                const highPercent = (high_kg / maxEstimate) * 100;

                return (
                  <div key={pred.block_id} style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>{pred.block_code}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                        {(pred_kg / 1000).toFixed(2)}t
                      </span>
                    </div>
                    <div style={{ position: 'relative', height: 24, background: 'var(--color-surface-3)', borderRadius: 4, overflow: 'hidden' }}>
                      {/* Low estimate */}
                      <div style={{
                        position: 'absolute',
                        left: 0,
                        width: `${lowPercent}%`,
                        height: '100%',
                        background: 'rgba(34,197,94,0.3)',
                        borderRadius: 4,
                      }} />
                      {/* Predicted */}
                      <div style={{
                        position: 'absolute',
                        left: 0,
                        width: `${predPercent}%`,
                        height: '100%',
                        background: 'var(--color-primary)',
                        borderRadius: 4,
                      }} />
                      {/* High estimate */}
                      <div style={{
                        position: 'absolute',
                        left: `${predPercent}%`,
                        width: `${highPercent - predPercent}%`,
                        height: '100%',
                        background: 'rgba(34,197,94,0.2)',
                        borderRadius: 4,
                      }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                      <span>{(low_kg / 1000).toFixed(2)}t</span>
                      <span>{(high_kg / 1000).toFixed(2)}t</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* ── Predictions Table ── */}
      {!loading && predictions.length > 0 && (
        <div className="table-wrap">
          <div className="table-header-bar">
            <div>
              <div className="table-title">Block Yield Predictions</div>
              <div className="table-subtitle">{MONTH_NAMES[month - 1]} {year} · {estate?.name}</div>
            </div>
            <span className="badge badge-neutral">{predictions.length} blocks</span>
          </div>

          <table>
            <thead>
              <tr>
                <th>Block</th>
                <th>Predicted Yield (kg)</th>
                <th>Confidence Range</th>
                <th>Low Estimate</th>
                <th>High Estimate</th>
              </tr>
            </thead>
            <tbody>
              {sortedPredictions.map(pred => {
                const pred_kg = pred.predicted_yield_kg || 0;
                const low_kg = pred.confidence_low || 0;
                const high_kg = pred.confidence_high || 0;
                const rangePct = low_kg && high_kg ? Math.round(((high_kg - low_kg) / pred_kg) * 100) : 0;
                return (
                  <tr key={pred.block_id}>
                    <td style={{ fontWeight: 600 }}>{pred.block_code}</td>
                    <td style={{ fontWeight: 700, fontSize: '1rem' }}>
                      {(pred_kg / 1000).toFixed(2)}t
                    </td>
                    <td style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--color-primary)' }}>
                      ±{rangePct}%
                    </td>
                    <td style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
                      {(low_kg / 1000).toFixed(2)}t
                    </td>
                    <td style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
                      {(high_kg / 1000).toFixed(2)}t
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Empty State ── */}
      {!loading && predictions.length === 0 && !error && (
        <div style={{ padding: 48, textAlign: 'center', background: 'var(--color-surface-2)', borderRadius: 14, border: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 10 }}>📊</div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>No predictions for {MONTH_NAMES[month - 1]} {year}</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            Try a different month or estate, or ensure labour plans have been generated
          </div>
        </div>
      )}
    </>
  );
}

/* ── Tab: Reports ─────────────────────────────────────────────────────── */
function ReportTab() {
  const { token, canWrite } = useAuth();
  const [estates, setEstates]         = useState([]);
  const [estateId, setEstateId]       = useState('');
  const [reportMonth, setReportMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });
  const [generating, setGenerating]   = useState(false);
  const [error, setError]             = useState('');
  const [done, setDone]               = useState(false);

  useEffect(() => {
    if (!token) return;
    apiService.getEstates(token)
      .then(data => { setEstates(data); if (data.length > 0) setEstateId(data[0].id); })
      .catch(() => {});
  }, [token]);

  const handleGenerate = async () => {
    if (!estateId || !reportMonth) return;
    const [year, month] = reportMonth.split('-').map(Number);
    setGenerating(true); setError(''); setDone(false);
    try {
      await apiService.downloadPdfReport(token, estateId, year, month);
      setDone(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const sel = {
    padding: '9px 14px', borderRadius: 8,
    border: '1px solid var(--color-border)',
    background: 'var(--color-surface-2)', color: 'var(--color-text)',
    fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer',
  };

  const MONTH_NAMES = ['January','February','March','April','May','June',
                       'July','August','September','October','November','December'];
  const [yr, mo]    = reportMonth ? reportMonth.split('-').map(Number) : [null, null];
  const estate      = estates.find(e => e.id === estateId);

  return (
    <div style={{ maxWidth: 720 }}>

      {/* ── Controls ── */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end',
                    marginBottom: 'var(--space-6)' }}>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)',
                        marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Estate
          </div>
          <select
            value={estateId}
            onChange={e => { setEstateId(e.target.value); setDone(false); }}
            disabled={!canWrite}
            style={{ ...sel, cursor: canWrite ? 'pointer' : 'not-allowed', opacity: canWrite ? 1 : 0.7 }}
          >
            {estates.length === 0 && <option value="">Loading…</option>}
            {estates.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
        </div>

        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)',
                        marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Period
          </div>
          <input
            type="month"
            value={reportMonth}
            onChange={e => { setReportMonth(e.target.value); setDone(false); }}
            style={sel}
          />
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating || !estateId}
          style={{
            padding: '10px 28px', borderRadius: 8, border: 'none', cursor: 'pointer',
            background: generating ? '#6b7280' : 'var(--color-primary)',
            color: '#fff', fontWeight: 700, fontSize: '0.9rem',
            display: 'flex', alignItems: 'center', gap: 8,
            opacity: !estateId ? 0.5 : 1, alignSelf: 'flex-end',
          }}
        >
          {generating ? (
            <>
              <span style={{ display: 'inline-block', width: 14, height: 14,
                             border: '2px solid rgba(255,255,255,0.4)',
                             borderTopColor: '#fff', borderRadius: '50%',
                             animation: 'spin 0.8s linear infinite' }} />
              Generating PDF…
            </>
          ) : '⬇  Download PDF Report'}
        </button>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      {/* ── Error ── */}
      {error && (
        <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(220,38,38,0.08)',
                      color: 'var(--color-danger)', marginBottom: 20, fontSize: '0.875rem',
                      border: '1px solid rgba(220,38,38,0.2)' }}>
          {error}
        </div>
      )}

      {/* ── Success ── */}
      {done && (
        <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(22,163,74,0.08)',
                      color: 'var(--color-success)', marginBottom: 20, fontSize: '0.875rem',
                      border: '1px solid rgba(22,163,74,0.2)', fontWeight: 600 }}>
          PDF downloaded — check your downloads folder.
        </div>
      )}

      {/* ── Report preview card ── */}
      {estate && yr && mo && (
        <div style={{ background: 'var(--color-surface-2)', borderRadius: 14,
                      border: '1px solid var(--color-border)', overflow: 'hidden',
                      marginBottom: 'var(--space-6)' }}>
          {/* gradient header */}
          <div style={{
            background: 'linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%)',
            padding: '22px 24px', color: '#fff',
          }}>
            <div style={{ fontSize: '0.75rem', opacity: 0.65, textTransform: 'uppercase',
                          letterSpacing: '0.1em', marginBottom: 6 }}>
              Estate Performance Report
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 2 }}>
              {estate.name}
            </div>
            <div style={{ opacity: 0.75, fontSize: '0.9rem' }}>
              {estate.region || ''}{estate.region ? ' · ' : ''}{MONTH_NAMES[mo - 1]} {yr}
            </div>
          </div>

        </div>
      )}

      {/* ── Loading overlay card ── */}
      {generating && (
        <div style={{ padding: 40, textAlign: 'center', background: 'var(--color-surface-2)',
                      borderRadius: 14, border: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>📄</div>
          <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: 6 }}>
            Building your report…
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            Fetching data, rendering charts and assembling PDF. This takes a few seconds.
          </div>
        </div>
      )}

      {/* ── Idle state ── */}
      {!generating && !estate && (
        <div style={{ padding: 48, textAlign: 'center', background: 'var(--color-surface-2)',
                      borderRadius: 14, border: '1px solid var(--color-border)',
                      color: 'var(--color-text-muted)' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: 10 }}>📄</div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Select an estate and period</div>
          <div style={{ fontSize: '0.875rem' }}>then click Download PDF Report</div>
        </div>
      )}
    </div>
  );
}

/* ── Nav Items Config ─────────────────────────────────────────────────── */
const navItems = [
  { id: 'overview',    icon: '🏠', label: 'Overview' },
  { id: 'roi',         icon: '📊', label: 'ROI Calculator' },
  { id: 'water',       icon: '💧', label: 'Water Efficiency' },
  { id: 'fertilizer',  icon: '🌱', label: 'Fertilizer Rotation' },
  { id: 'labour',      icon: '👥', label: 'Labour Planner' },
  { id: 'predictions', icon: '🔮', label: 'Yield Predictions' },
  { id: 'reports',     icon: '📄', label: 'Reports' },
];

const tabTitles = {
  overview:   { title: 'Overview',           sub: 'Estate-wide summary for June 2026' },
  roi:        { title: 'ROI Calculator',      sub: 'Cost-per-kg analysis across all estates' },
  water:      { title: 'Water Efficiency',    sub: 'Monthly factory water intensity tracking' },
  fertilizer: { title: 'Fertilizer Rotation', sub: 'Block-level application schedule & alerts' },
  labour:     { title: 'Labour Planner',      sub: 'Monthly worker allocation & production targets' },
  predictions: { title: 'Yield Predictions',  sub: 'ML model forecasts for each block & month' },
  reports:    { title: 'Estate Reports',      sub: 'Generate detailed per-estate performance reports' },
};

/* ── Main Dashboard ───────────────────────────────────────────────────── */
export default function DashboardPage() {
  const { user, isAuthenticated, loading, logout } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    // Wait until auth has finished restoring/verifying the stored token
    // before deciding the user is unauthenticated — otherwise a refresh
    // redirects to login before the localStorage token is loaded.
    if (!loading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [loading, isAuthenticated, router]);

  if (loading || !isAuthenticated) {
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
          <img src="/logo.png" alt="KVPL Logo" className="dash-sidebar-logo-mark" style={{ width: '40px', height: '40px', objectFit: 'contain' }} />
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
        </nav>

        
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
            <button
              onClick={logout}
              title="Sign out"
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '7px 14px', borderRadius: 8,
                border: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
                color: 'var(--color-danger)', fontWeight: 600, fontSize: '0.8125rem',
                cursor: 'pointer',
              }}
            >
               Sign Out
            </button>
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
          {activeTab === 'predictions' && <YieldPredictionTab />}
          {activeTab === 'reports'     && <ReportTab />}
        </main>
      </div>
    </div>
  );
}
