'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiService } from '../api/apiService';
import { useAuth } from '../context/AuthContext';
import { DataEntryModal } from '../components/DataEntryModal';
import { CSVImportModal } from '../components/CSVImportModal';

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
  const { token } = useAuth();
  const [estates, setEstates] = useState([]);
  const [summary, setSummary] = useState(null);
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showCSVImport, setShowCSVImport] = useState(null); // 'costs' | 'yield' | null

  // Load data on mount and when modal closes
  const loadROIData = async () => {
    setLoading(true);
    setError('');
    try {
      const [estatesData, summaryData, rankingsData] = await Promise.all([
        apiService.getROIEstates(token),
        apiService.getROISummary(token),
        apiService.getROIRankings(token),
      ]);
      setEstates(estatesData);
      setSummary(summaryData);
      setRankings(rankingsData);
    } catch (err) {
      console.error('Failed to load ROI data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadROIData();
    }
  }, [token]);

  const handleModalClose = () => {
    setShowModal(false);
  };

  const handleDataSaved = () => {
    // Refresh ROI data when new data is saved
    loadROIData();
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
        <div style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>⏳</div>
        <p>Loading ROI data…</p>
      </div>
    );
  }

  return (
    <>
      <div className="kpi-grid">
        <KpiCard 
          icon="🏆" 
          iconBg="kpi-icon-green"  
          label="Best Cost/kg" 
          value={summary?.best_cost_per_kg ? `Rs. ${summary.best_cost_per_kg}` : '—'} 
          unit="" 
        />
        <KpiCard 
          icon="📦" 
          iconBg="kpi-icon-teal"   
          label="Total Estates" 
          value={summary?.total_estates || '—'}  
          unit="" 
        />
        <KpiCard 
          icon="📈" 
          iconBg="kpi-icon-blue"   
          label="Avg Cost / kg" 
          value={summary?.avg_cost_per_kg ? `Rs. ${summary.avg_cost_per_kg}` : '—'} 
          unit="" 
        />
        <KpiCard 
          icon="⚠️" 
          iconBg="kpi-icon-amber"  
          label="Flagged Records" 
          value={summary?.flagged_count || '0'} 
          unit="" 
        />
      </div>

      <div className="table-wrap">
        <div className="table-header-bar">
          <div>
            <div className="table-title">Estate ROI Rankings</div>
            <div className="table-subtitle">
              Sorted by cost-per-kg · {summary?.month ? ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][summary.month-1] : '—'} {summary?.year || '—'}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setShowModal(true)}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                border: 'none',
                background: 'var(--color-primary)',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.875rem',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => {
                e.target.style.opacity = '0.9';
              }}
              onMouseOut={(e) => {
                e.target.style.opacity = '1';
              }}
            >
              + Add Monthly Data
            </button>
            <button
              onClick={() => setShowCSVImport('costs')}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                border: '1px solid var(--color-border)',
                background: 'transparent',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.875rem',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => {
                e.target.style.background = 'var(--color-surface-2)';
              }}
              onMouseOut={(e) => {
                e.target.style.background = 'transparent';
              }}
            >
              📥 Import Costs CSV
            </button>
            <button
              onClick={() => setShowCSVImport('yield')}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                border: '1px solid var(--color-border)',
                background: 'transparent',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.875rem',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => {
                e.target.style.background = 'var(--color-surface-2)';
              }}
              onMouseOut={(e) => {
                e.target.style.background = 'transparent';
              }}
            >
              📥 Import Yield CSV
            </button>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Estate</th>
              <th>Region</th>
              <th>Cost / kg</th>
              <th>Yield (kg)</th>
              <th>Total Cost</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rankings.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                  No ROI data available. Add input costs and yield records to populate rankings.
                </td>
              </tr>
            ) : (
              rankings.map(e => (
                <tr key={e.estate_id || e.name}>
                  <td>
                    <div className={`rank-badge rank-${e.rank || 1}`}>
                      {e.rank || '—'}
                    </div>
                  </td>
                  <td style={{ fontWeight: '600', color: 'var(--color-text)' }}>{e.estate_name || e.name}</td>
                  <td>{e.region || '—'}</td>
                  <td style={{ fontWeight: '700', fontSize: '1.05rem' }}>
                    {e.cost_per_kg ? `Rs. ${e.cost_per_kg.toFixed(2)}` : '—'}
                  </td>
                  <td>{e.yield_kg ? e.yield_kg.toLocaleString() : '—'}</td>
                  <td>
                    {e.total_cost ? `Rs. ${e.total_cost.toLocaleString()}` : '—'}
                  </td>
                  <td>
                    {e.is_flagged ? (
                      <span 
                        className="badge badge-warning"
                        title={e.flag_reason}
                        style={{ cursor: 'help' }}
                      >
                        ⚠️ Flagged
                      </span>
                    ) : (
                      <span className="badge badge-success">✓ OK</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Cost Per kg Comparison */}
      {rankings.length > 0 && (
        <div className="section-card" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-card-header">
            <div className="section-card-title">
              <div className="section-card-title-icon">📊</div>
              Cost Per kg Comparison
            </div>
          </div>
          <div className="section-card-body">
            {rankings.map(e => {
              const maxCost = summary?.worst_cost_per_kg || 400;
              const costPerKg = e.cost_per_kg || 0;
              const pct = maxCost > 0 ? (costPerKg / maxCost) * 100 : 0;
              const colors = [
                'progress-green',
                'progress-green',
                'progress-amber',
                'progress-red',
              ];
              const colorIndex = Math.min((e.rank || 1) - 1, 3);
              return (
                <div key={e.estate_id || e.name} style={{ marginBottom: 'var(--space-5)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-2)', fontSize: '0.9rem' }}>
                    <span style={{ fontWeight: '600', color: 'var(--color-text)' }}>
                      {e.estate_name || e.name}
                    </span>
                    <span style={{ fontWeight: '700' }}>
                      Rs. {costPerKg.toFixed(2)}
                    </span>
                  </div>
                  <div className="progress-wrap" style={{ height: 12 }}>
                    <div 
                      className={`progress-bar ${colors[colorIndex]}`} 
                      style={{ width: `${Math.min(pct, 100)}%` }} 
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Data Entry Modal */}
      <DataEntryModal
        isOpen={showModal}
        onClose={handleModalClose}
        estates={estates}
        token={token}
        onSuccess={handleDataSaved}
        apiService={apiService}
      />

      {/* CSV Import Modals */}
      <CSVImportModal
        isOpen={showCSVImport === 'costs'}
        onClose={() => setShowCSVImport(null)}
        recordType="costs"
        token={token}
        apiService={apiService}
        onSuccess={handleDataSaved}
        estates={estates}
      />

      <CSVImportModal
        isOpen={showCSVImport === 'yield'}
        onClose={() => setShowCSVImport(null)}
        recordType="yield"
        token={token}
        apiService={apiService}
        onSuccess={handleDataSaved}
        estates={estates}
      />
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
  const { token } = useAuth();
  const [view, setView]           = useState('week');      // 'week' | 'rotation' | 'employees'
  const [estates, setEstates]     = useState([]);
  const [estateId, setEstateId]   = useState('');
  const [plan, setPlan]           = useState(null);        // current week plan
  const [rotation, setRotation]   = useState(null);
  const [employees, setEmployees] = useState([]);
  const [groups, setGroups]       = useState([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

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

  // Plan creation modal state
  const [planCreateModal, setPlanCreateModal] = useState(false);
  const [planCreateBlocks, setPlanCreateBlocks] = useState([]); // [{...block, groupId:'', expectedYield:''}]
  const [planCreateLoading, setPlanCreateLoading] = useState(false);
  const [planCreateError, setPlanCreateError] = useState('');

  // First day of the current month (YYYY-MM-01)
  const monthStart = (() => {
    const d = new Date();
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff)).toISOString().slice(0, 10);
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
          const [plans, grps] = await Promise.all([
            apiService.getLabourPlans(token, { estateId, monthStart }),
            apiService.getWorkerGroups(token, estateId),
          ]);
          setGroups(grps);
          if (plans.length > 0) {
            const detail = await apiService.getLabourPlan(token, plans[0].id);
            setPlan(detail);
          } else {
            setPlan(null);
          }
        } else if (view === 'rotation') {
          const [rotData, plans] = await Promise.all([
            apiService.getRotation(token, estateId),
            apiService.getLabourPlans(token, { estateId, monthStart }),
          ]);
          setRotation(rotData.length > 0 ? rotData[0] : null);
          if (plans.length > 0) {
            const detail = await apiService.getLabourPlan(token, plans[0].id);
            setPlan(detail);
          } else {
            setPlan(null);
          }
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
  }, [token, estateId, view, weekStart]);

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
      const emps = await apiService.getEmployees(token, { estateId });
      setEmployees(emps);
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
      const emps = await apiService.getEmployees(token, { estateId });
      setEmployees(emps);
    } catch (e) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  // ── KPIs derived from plan assignments
  const assignments = plan?.assignments || [];
  const totalWorkers  = assignments.reduce((s, a) => s + (a.group_capacity || 0), 0);
  const totalTarget   = assignments.reduce((s, a) => s + (a.expected_yield_kg || 0), 0);
  const totalActual   = assignments.reduce((s, a) => s + (a.actual_yield_kg || 0), 0);
  const overallEff    = totalTarget > 0 ? ((totalActual / totalTarget) * 100).toFixed(1) : '—';

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
          style={{
            padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)',
            background: 'var(--color-surface-2)', color: 'var(--color-text)',
            fontSize: '0.875rem', fontWeight: 600, cursor: 'pointer',
          }}
        >
          {estates.length === 0 && <option value="">Loading estates…</option>}
          {estates.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
        </select>

        <div style={{ display: 'flex', gap: 6 }}>
          <button style={subBtnStyle('week')}      onClick={() => setView('week')}>This Week</button>
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

      {/* ── VIEW: This Week ── */}
      {!loading && view === 'week' && (
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
              <span className="badge badge-neutral">Week starting {plan.week_start}</span>
              <span className={`badge ${plan.status === 'published' ? 'badge-success' : plan.status === 'completed' ? 'badge-neutral' : 'badge-warning'}`}>
                {plan.status}
              </span>
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
              <button onClick={async () => {
                setPlanCreateError('');
                setPlanCreateLoading(true);
                try {
                  const [blocks, grps] = await Promise.all([
                    apiService.getBlocks(token, estateId),
                    apiService.getWorkerGroups(token, estateId),
                  ]);
                  setGroups(grps);
                  setPlanCreateBlocks(blocks.map(b => ({ ...b, groupId: '', expectedYield: '' })));
                  setPlanCreateModal(true);
                } catch (e) {
                  setError(e.message);
                } finally {
                  setPlanCreateLoading(false);
                }
              }} disabled={loading || planCreateLoading} style={{ marginTop: 16, padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.875rem' }}>
                {planCreateLoading ? 'Loading...' : '+ Create Plan'}
              </button>
            </div>
          ) : (
            <div className="table-wrap">
              <div className="table-header-bar">
                <div>
                  <div className="table-title">Block Assignments — {weekStart}</div>
                  <div className="table-subtitle">
                    Rotation-generated assignments · {assignments.length} blocks · manual overrides shown
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="badge badge-neutral">{assignments.length} blocks</span>
                  <button onClick={async () => {
                    setPlanCreateError('');
                    setPlanCreateLoading(true);
                    try {
                      const [blocks, grps] = await Promise.all([
                        apiService.getBlocks(token, estateId),
                        apiService.getWorkerGroups(token, estateId),
                      ]);
                      setGroups(grps);
                      // Only show blocks not already in the plan
                      const assignedCodes = new Set(assignments.map(a => a.block_code));
                      const unassigned = blocks.filter(b => !assignedCodes.has(b.block_code));
                      setPlanCreateBlocks(unassigned.map(b => ({ ...b, groupId: '', expectedYield: '' })));
                      setPlanCreateModal(true);
                    } catch (e) { setError(e.message); }
                    finally { setPlanCreateLoading(false); }
                  }} disabled={planCreateLoading} style={{ padding: '5px 14px', borderRadius: 7, border: '1.5px dashed var(--color-primary)', background: 'transparent', color: 'var(--color-primary)', fontWeight: 600, fontSize: '0.8rem', cursor: 'pointer' }}>
                    {planCreateLoading ? '…' : '+ Add Blocks'}
                  </button>
                </div>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Block</th>
                    <th>Group</th>
                    <th>Workers</th>
                    <th>Target (kg)</th>
                    <th>Actual (kg)</th>
                    <th>Efficiency</th>
                    <th>Progress</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedAssignments.length === 0 && (
                    <tr>
                      <td colSpan={8} style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                        No block assignments yet.
                        <button onClick={async () => {
                          setPlanCreateError('');
                          setPlanCreateLoading(true);
                          try {
                            const [blocks, grps] = await Promise.all([
                              apiService.getBlocks(token, estateId),
                              apiService.getWorkerGroups(token, estateId),
                            ]);
                            setGroups(grps);
                            setPlanCreateBlocks(blocks.map(b => ({ ...b, groupId: '', expectedYield: '' })));
                            setPlanCreateModal(true);
                          } catch (e) { setError(e.message); }
                          finally { setPlanCreateLoading(false); }
                        }} style={{ marginLeft: 12, padding: '4px 14px', borderRadius: 6, border: 'none', background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8rem', cursor: 'pointer' }}>
                          + Add Blocks
                        </button>
                      </td>
                    </tr>
                  )}
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
                          {a.is_manual_override && a.original_group_name && (
                            <span title={a.override_reason || 'Manually overridden'}
                                  style={{ marginLeft: 6, fontSize: '0.7rem', color: 'var(--color-warning)', fontWeight: 600 }}>
                              ✎
                            </span>
                          )}
                        </td>
                        <td style={{ fontSize: '0.875rem' }}>
                          {a.group_name ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <div style={{ fontWeight: 600, color: 'var(--color-text)' }}>{a.group_name}</div>
                              {a.is_manual_override && a.original_group_name && (
                                <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                                  (was: {a.original_group_name})
                                </div>
                              )}
                              {(canWrite || isManager) && (
                                <button
                                  onClick={async () => {
                                    setSavingTarget(true);
                                    try {
                                      await apiService.removeGroupFromAssignment(token, a.id);
                                      const updated = await apiService.getLabourPlan(token, plan.id);
                                      setPlan(updated);
                                      setError('');
                                    } catch (err) { setError(err.message); }
                                    finally { setSavingTarget(false); }
                                  }}
                                  disabled={savingTarget}
                                  style={{ padding: '2px 8px', borderRadius: 4, border: '1px solid rgba(220,38,38,0.4)', background: 'transparent', color: 'var(--color-danger)', cursor: 'pointer', fontSize: '0.7rem', fontWeight: 600, whiteSpace: 'nowrap' }}
                                >
                                  Remove
                                </button>
                              )}
                            </div>
                          ) : (canWrite || isManager) && (
                            addingGroup === a.id ? (
                              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                                <select
                                  autoFocus
                                  defaultValue=""
                                  disabled={savingTarget}
                                  onChange={async (e) => {
                                    if (!e.target.value) return;
                                    setSavingTarget(true);
                                    try {
                                      await apiService.changeGroupAssignment(token, a.id, e.target.value);
                                      const updated = await apiService.getLabourPlan(token, plan.id);
                                      setPlan(updated);
                                      setAddingGroup(null);
                                      setError('');
                                    } catch (err) { setError(err.message); }
                                    finally { setSavingTarget(false); }
                                  }}
                                  style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid var(--color-primary)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.8125rem', minWidth: 120 }}
                                >
                                  <option value="">Select group…</option>
                                  {groups
                                    .filter(g => !assignments.some(ax => ax.worker_group_id && String(ax.worker_group_id) === String(g.id)))
                                    .map(g => <option key={g.id} value={g.id}>{g.group_name}</option>)
                                  }
                                </select>
                                <button onClick={() => setAddingGroup(null)} style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '0.75rem' }}>✕</button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setAddingGroup(a.id)}
                                style={{ padding: '4px 12px', borderRadius: 6, border: '1.5px dashed var(--color-warning)', background: 'transparent', color: 'var(--color-warning)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                              >
                                + Add Group
                              </button>
                            )
                          )}
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span>👤</span>
                            <span style={{ fontWeight: 600 }}>{a.group_capacity || '—'}</span>
                          </div>
                        </td>
                        <td>{exp ? Math.round(exp).toLocaleString() : '—'}</td>
                        <td style={{ fontWeight: 700 }}>{act ? Math.round(act).toLocaleString() : '—'}</td>
                        <td style={{ fontWeight: 700, color: effColor }}>
                          {act === 0 ? '—' : `${eff.toFixed(1)}%`}
                        </td>
                        <td style={{ minWidth: 120 }}>
                          <div className="progress-wrap">
                            {pct > 0 && <div className={`progress-bar ${barClass}`} style={{ width: `${pct}%` }} />}
                          </div>
                        </td>
                        <td>
                          <span className={`badge ${
                            a.status === 'completed'   ? 'badge-success' :
                            a.status === 'in_progress' ? 'badge-warning' :
                            a.status === 'cancelled'   ? 'badge-danger'  : 'badge-neutral'
                          }`}>{a.status}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
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
                  <th>Round</th>
                  {(rotation.matrix[1] || []).map(b => <th key={b.block_code}>{b.block_code}</th>)}
                </tr>
              </thead>
              <tbody>
                {sortedRotationRows.map(([rn, cells]) => {
                  const isCurrent = parseInt(rn) === rotation.current_round;
                  // For the current round, build actual assignment lookup from plan
                  const actualByBlock = isCurrent && plan
                    ? Object.fromEntries((plan.assignments || []).map(a => [a.block_code, a]))
                    : null;
                  return (
                    <tr key={rn} style={{
                      background: isCurrent ? 'rgba(var(--color-primary-rgb, 37,99,235), 0.06)' : '',
                    }}>
                      <td style={{ fontWeight: 700 }}>
                        Round {rn}
                        {isCurrent && (
                          <span className="badge badge-success" style={{ marginLeft: 8, fontSize: '0.65rem' }}>current</span>
                        )}
                      </td>
                      {cells.map(c => {
                        const actual = actualByBlock?.[c.block_code];
                        const changed = actual && actual.group_code !== c.group_code;
                        return (
                          <td key={c.block_code} style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                            {actual ? (
                              <>
                                <div style={{ fontWeight: 600, color: 'var(--color-text)' }}>
                                  {actual.group_code || <span style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>—</span>}
                                </div>
                                <div style={{ fontSize: '0.7rem' }}>{actual.group_capacity ?? c.capacity} workers</div>
                              </>
                            ) : (
                              <>
                                <div style={{ fontWeight: 600, color: 'var(--color-text)' }}>{c.group_code}</div>
                                <div style={{ fontSize: '0.7rem' }}>{c.capacity} workers</div>
                              </>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
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
              <button
                onClick={openAddModal}
                style={{
                  padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
                  background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8125rem',
                }}
              >
                + Add Employee
              </button>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Group</th>
                  <th>Role</th>
                  <th>Type</th>
                  <th>Wage / day</th>
                  <th>Hire Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {employees.length === 0 ? (
                  <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 32 }}>
                    No employees found for this estate.
                  </td></tr>
                ) : employees.map(emp => (
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

      {/* ── Plan Creation Modal ── */}
      {planCreateModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--color-surface)', borderRadius: 14, padding: 0, width: '90%', maxWidth: 820, maxHeight: '88vh', display: 'flex', flexDirection: 'column', boxShadow: '0 8px 40px rgba(0,0,0,0.35)' }}>
            {/* Header */}
            <div style={{ padding: '20px 24px 16px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--color-text)' }}>{plan ? 'Add Blocks to Plan' : 'Create Labour Plan'}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: 2 }}>{monthStart} — assign groups and set expected yields for each block</div>
              </div>
              <button onClick={() => setPlanCreateModal(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '1.2rem', color: 'var(--color-text-muted)', padding: '4px 8px' }}>✕</button>
            </div>

            {/* Block table */}
            <div style={{ overflowY: 'auto', flex: 1, padding: '0 24px' }}>
              {planCreateBlocks.length === 0 ? (
                <p style={{ color: 'var(--color-text-muted)', padding: '32px 0', textAlign: 'center' }}>No blocks found for this estate.</p>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
                      <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600, color: 'var(--color-text-muted)' }}>Block</th>
                      <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600, color: 'var(--color-text-muted)' }}>State</th>
                      <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600, color: 'var(--color-text-muted)' }}>Area (ha)</th>
                      <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600, color: 'var(--color-text-muted)' }}>Worker Group</th>
                      <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600, color: 'var(--color-text-muted)' }}>Expected Yield (kg)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {planCreateBlocks.map((b, idx) => (
                      <tr key={b.id} style={{ borderBottom: '1px solid var(--color-border)', background: idx % 2 === 0 ? 'transparent' : 'var(--color-surface-2)' }}>
                        <td style={{ padding: '10px 8px', fontWeight: 700 }}>{b.block_code}</td>
                        <td style={{ padding: '10px 8px' }}>
                          <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: '0.75rem', background: 'var(--color-surface-2)', color: 'var(--color-text-muted)' }}>{b.state || 'active'}</span>
                        </td>
                        <td style={{ padding: '10px 8px', color: 'var(--color-text-muted)' }}>{b.area_hectares ?? '—'}</td>
                        <td style={{ padding: '10px 8px' }}>
                          <select
                            value={b.groupId}
                            onChange={e => setPlanCreateBlocks(prev => prev.map((x, i) => i === idx ? { ...x, groupId: e.target.value } : x))}
                            style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.8125rem', minWidth: 140 }}
                          >
                            <option value="">— Unassigned —</option>
                            {groups
                              .filter(g => !planCreateBlocks.some((x, i) => i !== idx && x.groupId && String(x.groupId) === String(g.id)))
                              .map(g => <option key={g.id} value={g.id}>{g.group_name}</option>)
                            }
                          </select>
                        </td>
                        <td style={{ padding: '10px 8px' }}>
                          <input
                            type="number"
                            min="0"
                            placeholder="0"
                            value={b.expectedYield}
                            onChange={e => setPlanCreateBlocks(prev => prev.map((x, i) => i === idx ? { ...x, expectedYield: e.target.value } : x))}
                            style={{ width: 100, padding: '4px 8px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.8125rem' }}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Footer */}
            {planCreateError && <div style={{ padding: '8px 24px', color: 'var(--color-danger)', fontSize: '0.8rem' }}>{planCreateError}</div>}
            <div style={{ padding: '16px 24px', borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button onClick={() => setPlanCreateModal(false)} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text)', cursor: 'pointer', fontWeight: 500 }}>Cancel</button>
              <button
                disabled={planCreateLoading || planCreateBlocks.length === 0}
                onClick={async () => {
                  setPlanCreateLoading(true);
                  setPlanCreateError('');
                  try {
                    let updatedPlan;
                    if (plan) {
                      // Add blocks to existing plan
                      for (const b of planCreateBlocks) {
                        await apiService.addAssignmentToPlan(token, plan.id, {
                          block_id: b.id,
                          worker_group_id: b.groupId || null,
                          expected_yield_kg: b.expectedYield ? parseFloat(b.expectedYield) : 0,
                        });
                      }
                      updatedPlan = await apiService.getLabourPlan(token, plan.id);
                    } else {
                      // Create new plan with all blocks
                      const assignmentList = planCreateBlocks.map(b => ({
                        block_id: b.id,
                        worker_group_id: b.groupId || null,
                        expected_yield_kg: b.expectedYield ? parseFloat(b.expectedYield) : 0,
                      }));
                      const result = await apiService.createManualPlan(token, {
                        estate_id: estateId,
                        period_start: monthStart,
                        assignments: assignmentList,
                        status: 'draft',
                        notes: 'Manual plan creation',
                      });
                      updatedPlan = await apiService.getLabourPlan(token, result.plan_id);
                    }
                    setPlan(updatedPlan);
                    setPlanCreateModal(false);
                    setError('');
                  } catch (e) {
                    setPlanCreateError(e.message);
                  } finally {
                    setPlanCreateLoading(false);
                  }
                }}
                style={{ padding: '8px 24px', borderRadius: 8, border: 'none', background: 'var(--color-primary)', color: '#fff', fontWeight: 600, cursor: planCreateLoading ? 'not-allowed' : 'pointer', opacity: planCreateLoading ? 0.7 : 1 }}
              >
                {planCreateLoading ? (plan ? 'Adding…' : 'Creating…') : (plan ? 'Add Blocks' : 'Create Plan')}
              </button>
            </div>
          </div>
        </div>
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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
      <aside className={`dash-sidebar${sidebarCollapsed ? ' collapsed' : ''}`}>
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
              title={sidebarCollapsed ? item.label : undefined}
            >
              <span className="dash-nav-icon">{item.icon}</span>
              <span className="dash-nav-item-label">{item.label}</span>
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

        <button
          className="dash-sidebar-toggle"
          onClick={() => setSidebarCollapsed(c => !c)}
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? '›' : '‹'}
        </button>
      </aside>

      {/* ── Main Area ────────────────────────────────────────── */}
      <div className={`dash-main${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
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
