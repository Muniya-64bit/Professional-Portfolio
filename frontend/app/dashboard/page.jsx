'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiService } from '../api/apiService';
import { CSVImportModal } from '../components/CSVImportModal';
import { DataEntryModal } from '../components/DataEntryModal';
import { useAuth } from '../context/AuthContext';

/* ── Mock Data ──────────────────────────────────────────────────────────── */
const estates = [
  { id: 1, name: 'Kelani Valley', location: 'Western Province', rank: 1, costPerKg: 285, production: 3840, trend: [-8, 5, 3, -12, 8, -5, -3], delta: -3.2 },
  { id: 2, name: 'Nuwara Eliya', location: 'Central Province',  rank: 2, costPerKg: 298, production: 3210, trend: [2, -4, 6, 1, -7, 3, -2],  delta: -1.8 },
  { id: 3, name: 'Uva Highlands', location: 'Uva Province',    rank: 3, costPerKg: 312, production: 2950, trend: [4, 3, -1, 5, 2, 1, 1],    delta: +1.1 },
  { id: 4, name: 'Ratnapura',    location: 'Sabaragamuwa',      rank: 4, costPerKg: 345, production: 2450, trend: [6, 2, 8, -3, 4, 3, 2],    delta: +2.3 },
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

/* ── Current period constants ─────────────────────────────────────────── */
const _now = new Date();
const CURRENT_YEAR         = _now.getFullYear();
const CURRENT_MONTH        = _now.getMonth() + 1;
const CURRENT_PERIOD_LABEL = _now.toLocaleString('default', { month: 'long', year: 'numeric' });

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
  const { token } = useAuth();
  const [summary, setSummary]     = useState(null);
  const [rankings, setRankings]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState('');
  const [fertAlerts, setFertAlerts] = useState([]);

  useEffect(() => {
    if (!token) return;
    setLoading(true); setError('');
    Promise.all([
      apiService.getROISummary(token, { year: CURRENT_YEAR, month: CURRENT_MONTH }),
      apiService.getROIRankings(token, { year: CURRENT_YEAR, month: CURRENT_MONTH }),
    ]).then(([s, r]) => {
      setSummary(s);
      setRankings(Array.isArray(r) ? r : (r?.rankings ?? []));
    }).catch(e => setError(e.message))
      .finally(() => setLoading(false));

    apiService.getFertilizerAlerts(token).catch(() => []).then(data => setFertAlerts(Array.isArray(data) ? data : []));
  }, [token]);

  const flagged  = rankings.filter(e => e.is_flagged).length;
  const avgCost  = summary?.avg_cost_per_kg ?? null;

  const fertOverdue = fertAlerts.filter(a => a.status === 'overdue');
  const fertDue = fertAlerts.filter(a => a.status === 'due');
  const fertAttention = [...fertOverdue, ...fertDue];

  const fertStatusMap = { pending: 'ok', due: 'due', overdue: 'overdue' };

  return (
    <>
      {error && (
        <div className="alert alert-warning" style={{ marginBottom: 'var(--space-4)' }}>
          <span>⚠️</span><span>{error}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="kpi-grid">
        <KpiCard icon="📊" iconBg="kpi-icon-green"
          label={`Estates Tracked (${CURRENT_PERIOD_LABEL})`}
          value={loading ? '…' : (summary?.total_estates ?? '—')} unit="" />
        <KpiCard icon="💧" iconBg="kpi-icon-teal"
          label="Water Efficiency"
          value="See tab" unit="" />
        <KpiCard icon="🚨" iconBg="kpi-icon-amber"
          label="Flagged Estates"
          value={loading ? '…' : flagged} unit=""
          deltaLabel={flagged > 0 ? 'High cost per kg — review ROI tab' : 'All estates within range'} />
        <KpiCard icon="💰" iconBg="kpi-icon-amber"
          label="Avg Cost / kg"
          value={loading ? '…' : (avgCost ? `Rs. ${avgCost.toFixed(2)}` : '—')} unit=""
          deltaLabel={`Best: Rs. ${summary?.best_cost_per_kg?.toFixed(2) ?? '—'}  ·  Worst: Rs. ${summary?.worst_cost_per_kg?.toFixed(2) ?? '—'}`} />
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
            <span className="badge badge-neutral">by Cost/kg — {CURRENT_PERIOD_LABEL}</span>
          </div>
          {loading ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>Loading…</div>
          ) : rankings.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
              No ROI data for this period. Enter cost data in the ROI Calculator tab.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Estate</th>
                  <th>Region</th>
                  <th>Cost/kg</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((e, i) => (
                  <tr key={e.estate_name}>
                    <td><div className={`rank-badge rank-${i + 1}`}>{i + 1}</div></td>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--color-text)', fontSize: '0.9rem' }}>{e.estate_name}</div>
                    </td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{e.region || '—'}</td>
                    <td style={{ fontWeight: 700 }}>
                      {e.cost_per_kg ? `Rs. ${Number(e.cost_per_kg).toFixed(2)}` : '—'}
                      {e.is_flagged && <span className="badge badge-danger" style={{ marginLeft: 6, fontSize: '0.65rem' }}>Flagged</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Water efficiency quick view */}
        <div className="section-card">
          <div className="section-card-header">
            <div className="section-card-title">
              <div className="section-card-title-icon">💧</div>
              Water Efficiency
            </div>
          </div>
          <div className="section-card-body">
            <p style={{ padding: '1rem', color: 'var(--color-text-muted)' }}>
              See the <strong>Water Efficiency</strong> tab for monthly intensity tracking and targets.
            </p>
          </div>
        </div>
      </div>

      {/* Fertilizer quick view */}
      <div className="section-card" style={{ marginTop: 'var(--space-6)' }}>
        <div className="section-card-header">
          <div className="section-card-title">
            <div className="section-card-title-icon">🌱</div>
            Fertilizer Rotation
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {fertOverdue.length > 0 && <span className="badge badge-danger">{fertOverdue.length} Overdue</span>}
            {fertDue.length > 0 && <span className="badge badge-warning">{fertDue.length} Due</span>}
            {fertAttention.length === 0 && fertAlerts.length > 0 && <span className="badge badge-success">All Clear</span>}
          </div>
        </div>
        <div className="section-card-body">
          {fertAttention.length === 0 ? (
            <p style={{ padding: '0.5rem 0', color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
              {fertAlerts.length > 0 ? 'No overdue or due blocks — all on schedule.' : 'No schedule data yet. Generate a plan in the Fertilizer Rotation tab.'}
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {fertAttention.map(a => {
                const isOverdue = a.status === 'overdue';
                const accentColor = isOverdue ? 'var(--color-danger)' : 'var(--color-warning)';
                const bgColor = isOverdue ? 'rgba(220,38,38,0.04)' : 'rgba(245,158,11,0.04)';
                const days = Math.abs(a.days_overdue ?? 0);
                return (
                  <div key={a.id} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 14px',
                    borderRadius: 8,
                    background: bgColor,
                    border: `1px solid ${isOverdue ? 'rgba(220,38,38,0.15)' : 'rgba(245,158,11,0.15)'}`,
                    borderLeft: `3px solid ${accentColor}`,
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                        <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--color-text)' }}>{a.block_code}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{a.estate}</span>
                      </div>
                      <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                        {a.fertilizer}{a.total_kg_needed ? ` · ${Number(a.total_kg_needed).toFixed(0)} kg needed` : ''}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: '0.9rem', color: accentColor }}>
                        {isOverdue ? `${days} days overdue` : days === 0 ? 'Due' : `Due in ${days} days`}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 2 }}>{a.due_date}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
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
  const [estateMonthlyData, setEstateMonthlyData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showCSVImport, setShowCSVImport] = useState(null);
  const [hoveredPointIndex, setHoveredPointIndex] = useState(null);
  
  // Selected filters
  const [selectedEstateId, setSelectedEstateId] = useState('');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);

  // Generate year options (last 5 years)
  const yearOptions = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);
  const monthOptions = Array.from({ length: 12 }, (_, i) => ({
    value: i + 1,
    label: new Date(2000, i, 1).toLocaleString('default', { month: 'long' })
  }));

  // Load all data
  const loadROIData = async () => {
    setLoading(true);
    setError('');
    try {
      const [estatesData] = await Promise.all([
        apiService.getROIEstates(token),
      ]);
      setEstates(estatesData);
      if (estatesData.length > 0 && !selectedEstateId) {
        setSelectedEstateId(estatesData[0].id);
      }
    } catch (err) {
      console.error('Failed to load ROI data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Load data for selected filters
  const loadFilteredData = async () => {
    if (!selectedEstateId || !selectedYear || !selectedMonth) return;
    
    try {
      const [summaryData, rankingsData, trendData] = await Promise.all([
        apiService.getROISummary(token, { year: selectedYear, month: selectedMonth }),
        apiService.getROIRankings(token, { year: selectedYear, month: selectedMonth }),
        apiService.getROIEstateTrend(token, selectedEstateId, selectedYear),
      ]);
      setSummary(summaryData);
      setRankings(rankingsData);
      setEstateMonthlyData(trendData);
    } catch (err) {
      console.error('Failed to load filtered ROI data:', err);
      setError(err.message);
    }
  };

  useEffect(() => {
    if (token) {
      loadROIData();
    }
  }, [token]);

  useEffect(() => {
    if (token && selectedEstateId && selectedYear && selectedMonth) {
      loadFilteredData();
    }
  }, [token, selectedEstateId, selectedYear, selectedMonth]);

  const handleModalClose = () => {
    setShowModal(false);
  };

  const handleDataSaved = () => {
    loadROIData();
    loadFilteredData();
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
        <div style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>⏳</div>
        <p>Loading ROI data…</p>
      </div>
    );
  }

  // Simple line graph for estate ROI over the year
  const maxCost = Math.max(...estateMonthlyData.map(d => d.cost_per_kg), 1);
  const graphHeight = 200;

  return (
    <>
      {/* Filter Controls */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '0.875rem', fontWeight: '600', color: 'var(--color-text-muted)' }}>
            Estate:
          </label>
          <select
            value={selectedEstateId}
            onChange={e => setSelectedEstateId(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface-2)',
              color: 'var(--color-text)',
              fontSize: '0.875rem',
              fontWeight: '600',
              cursor: 'pointer',
              minWidth: '180px'
            }}
          >
            <option value="">Select Estate</option>
            {estates.map(estate => (
              <option key={estate.id} value={estate.id}>{estate.name}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '0.875rem', fontWeight: '600', color: 'var(--color-text-muted)' }}>
            Year:
          </label>
          <select
            value={selectedYear}
            onChange={e => setSelectedYear(parseInt(e.target.value))}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface-2)',
              color: 'var(--color-text)',
              fontSize: '0.875rem',
              fontWeight: '600',
              cursor: 'pointer',
              minWidth: '120px'
            }}
          >
            {yearOptions.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '0.875rem', fontWeight: '600', color: 'var(--color-text-muted)' }}>
            Month:
          </label>
          <select
            value={selectedMonth}
            onChange={e => setSelectedMonth(parseInt(e.target.value))}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface-2)',
              color: 'var(--color-text)',
              fontSize: '0.875rem',
              fontWeight: '600',
              cursor: 'pointer',
              minWidth: '140px'
            }}
          >
            {monthOptions.map(m => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Cards */}
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

      {/* Estate ROI Graph */}
      {estateMonthlyData.length > 0 && (
        <div className="section-card" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-card-header">
            <div className="section-card-title">
              <div className="section-card-title-icon">📈</div>
              {estates.find(e => e.id === selectedEstateId)?.name || 'Estate'} - ROI Trend {selectedYear}
            </div>
          </div>
          <div className="section-card-body" style={{ paddingBottom: '2rem' }}>
            <svg
              width="100%"
              height={graphHeight}
              style={{ minHeight: graphHeight }}
              viewBox={`0 0 1200 ${graphHeight}`}
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Grid lines */}
              {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
                const y = graphHeight * (1 - pct);
                const cost = maxCost * pct;
                return (
                  <g key={`grid-${i}`}>
                    <line x1="50" y1={y} x2="1200" y2={y} stroke="var(--color-border)" strokeDasharray="4" strokeWidth="1" opacity="0.3" />
                    <text x="20" y={y + 5} fontSize="12" fill="var(--color-text-muted)" textAnchor="end">
                      {cost.toFixed(0)}
                    </text>
                  </g>
                );
              })}

              {/* Line chart */}
              <polyline
                points={estateMonthlyData.map((d, i) => {
                  const x = 100 + (i / 11) * 1100;
                  const y = graphHeight * (1 - (d.cost_per_kg / maxCost));
                  return `${x},${y}`;
                }).join(' ')}
                fill="none"
                stroke="var(--color-primary)"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Data points with hover detection */}
              {estateMonthlyData.map((d, i) => {
                const x = 100 + (i / 11) * 1100;
                const y = graphHeight * (1 - (d.cost_per_kg / maxCost));
                const isSelected = i === selectedMonth - 1;
                const isHovered = i === hoveredPointIndex;
                return (
                  <g key={`point-${i}`}>
                    {/* Invisible larger circle for better hit detection */}
                    <circle
                      cx={x}
                      cy={y}
                      r="12"
                      fill="transparent"
                      pointerEvents="all"
                      onMouseEnter={() => setHoveredPointIndex(i)}
                      onMouseLeave={() => setHoveredPointIndex(null)}
                      style={{ cursor: 'pointer' }}
                    />
                    {/* Visible data point */}
                    <circle
                      cx={x}
                      cy={y}
                      r={isHovered ? 6 : isSelected ? 5 : 3}
                      fill={isHovered || isSelected ? '#3b82f6' : '#e5e7eb'}
                      stroke="#3b82f6"
                      strokeWidth="2"
                      pointerEvents="none"
                    />
                    {/* Tooltip */}
                    {isHovered && (
                      <>
                        <rect
                          x={Math.max(x - 50, 10)}
                          y={y - 40}
                          width="100"
                          height="28"
                          fill="#ffffff"
                          stroke="#3b82f6"
                          strokeWidth="1"
                          rx="4"
                          opacity="0.95"
                          pointerEvents="none"
                        />
                        <text
                          x={Math.max(x - 50, 10) + 50}
                          y={y - 18}
                          fontSize="12"
                          fontWeight="600"
                          fill="#1f2937"
                          textAnchor="middle"
                          pointerEvents="none"
                        >
                          {d.cost_per_kg.toFixed(2)}
                        </text>
                      </>
                    )}
                  </g>
                );
              })}

              {/* Month labels */}
              {monthOptions.map((m, i) => {
                const x = 100 + (i / 11) * 1100;
                return (
                  <text key={`label-${i}`} x={x} y={graphHeight - 10} fontSize="12" fill="var(--color-text-muted)" textAnchor="middle">
                    {m.label.slice(0, 3)}
                  </text>
                );
              })}
            </svg>
          </div>
        </div>
      )}

      {/* Estate Rankings for Selected Month */}
      <div className="table-wrap" style={{ marginTop: 'var(--space-6)' }}>
        <div className="table-header-bar">
          <div>
            <div className="table-title">Estate ROI Rankings</div>
            <div className="table-subtitle">
              For {monthOptions.find(m => m.value === selectedMonth)?.label} {selectedYear}
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
              rankings.map((e, idx) => (
                <tr key={idx}>
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


function WaterEditForm({ token, row, onClose, onSaved }) {
  const [waterM3, setWaterM3] = useState('');
  const [yieldKg, setYieldKg] = useState('');
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState('');

  const inputStyle = {
    width: '100%', padding: '8px 12px', borderRadius: 8, boxSizing: 'border-box',
    border: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
    color: 'var(--color-text)', fontSize: '0.875rem', marginBottom: 14
  };

  const handleSave = async () => {
  setSaving(true); setError('');
  try {
    await apiService.updateWaterUsage(token, row.id, {
      water_m3: waterM3 ? parseFloat(waterM3) : row.water_m3,
      yield_kg: yieldKg ? parseFloat(yieldKg) : row.yield_kg,
    });
      onSaved();
    } catch(e) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <>
      {error && <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(220,38,38,0.1)', color: 'var(--color-danger)', marginBottom: 16, fontSize: '0.875rem' }}>{error}</div>}
      <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem', marginBottom: 16 }}>Current intensity: <strong>{row.intensity} L/kg</strong>. Leave a field blank to keep the existing value.</p>

      <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 }}>New Water Used (m³)</label>
      <input type="number" placeholder="Leave blank to keep current" value={waterM3} onChange={e => setWaterM3(e.target.value)} style={inputStyle} />

      <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 }}>New Yield (kg)</label>
      <input type="number" placeholder="Leave blank to keep current" value={yieldKg} onChange={e => setYieldKg(e.target.value)} style={inputStyle} />

      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
        <button onClick={onClose} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600 }}>Cancel</button>
        <button onClick={handleSave} disabled={saving} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontWeight: 600, opacity: saving ? 0.7 : 1 }}>
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </div>
    </>
  );
}

function WaterLogForm({ token, onClose, onSaved }) {
  const [estates, setEstates] = useState([]);
  const [factoryId, setFactoryId] = useState('');
  const [month, setMonth] = useState('');
  const [waterM3, setWaterM3] = useState('');
  const [yieldKg, setYieldKg] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    apiService.getWaterEstates(token).then(data => {
      setEstates(data);
      if (data.length > 0) setFactoryId(data[0].factory_id);
    });
  }, [token]);

  const monthOptions = [
    {v:1,l:'January'},{v:2,l:'February'},{v:3,l:'March'},{v:4,l:'April'},
    {v:5,l:'May'},{v:6,l:'June'},{v:7,l:'July'},{v:8,l:'August'},
    {v:9,l:'September'},{v:10,l:'October'},{v:11,l:'November'},{v:12,l:'December'}
  ];

  const handleSave = async () => {
    if (!factoryId || !month || !waterM3 || !yieldKg) {
      setError('All fields are required.'); return;
    }
    setSaving(true); setError('');
    try {
      await apiService.addWaterUsage(token, {
        factory_id: factoryId,
        year: 2026,
        month: parseInt(month),
        water_m3: parseFloat(waterM3),
        yield_kg: parseFloat(yieldKg),
        track_status: 'on_track'
      });
      onSaved();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const inputStyle = {
    width: '100%', padding: '8px 12px', borderRadius: 8, boxSizing: 'border-box',
    border: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
    color: 'var(--color-text)', fontSize: '0.875rem', marginBottom: 14
  };

  return (
    <>
      {error && <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(220,38,38,0.1)', color: 'var(--color-danger)', marginBottom: 16, fontSize: '0.875rem' }}>{error}</div>}

      <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 }}>Estate</label>
      <select value={factoryId} onChange={e => setFactoryId(e.target.value)} style={inputStyle}>
        {estates.map(e => <option key={e.factory_id} value={e.factory_id}>{e.estate}</option>)}
      </select>

      <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 }}>Month</label>
      <select value={month} onChange={e => setMonth(e.target.value)} style={inputStyle}>
        <option value="">Select month…</option>
        {monthOptions.map(m => <option key={m.v} value={m.v}>{m.l}</option>)}
      </select>

      <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 }}>Water Used (m³)</label>
      <input type="number" placeholder="e.g. 7200" value={waterM3} onChange={e => setWaterM3(e.target.value)} style={inputStyle} />

      <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 }}>Yield (kg)</label>
      <input type="number" placeholder="e.g. 2400000" value={yieldKg} onChange={e => setYieldKg(e.target.value)} style={inputStyle} />

      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
        <button onClick={onClose} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600 }}>Cancel</button>
        <button onClick={handleSave} disabled={saving} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontWeight: 600, opacity: saving ? 0.7 : 1 }}>
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </>
  );
}


/* ── Tab: Water ───────────────────────────────────────────────────────── */
function WaterTab() {
  const { token } = useAuth();
  const [waterData, setWaterData] = useState([]);
  const [target, setTarget]       = useState(4.5);
  const [targetPct, setTargetPct] = useState(null);
  const [loading, setLoading]     = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editRow, setEditRow] = useState(null);
  const [deleteRow, setDeleteRow] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [usage, baseline] = await Promise.all([
          apiService.getWaterUsage(token, CURRENT_YEAR),
          apiService.getWaterBaseline(token)
        ]);

        const t = baseline.length > 0
          ? parseFloat((baseline[0].baseline_intensity * (1 - baseline[0].annual_target_pct / 100)).toFixed(3))
          : 4.5;
        setTarget(t);
        if (baseline.length > 0) setTargetPct(baseline[0].annual_target_pct);

        const formatted = usage.map(w => ({
          month:     w.month,
          estate:    w.estate,
          id:        w.id, //
          intensity: w.intensity_l_per_kg,
          water_m3:  w.water_m3,          
          yield_kg:  w.yield_kg, 
          target:    t,
          status:    w.intensity_l_per_kg <= t ? 'on_track' : 'at_risk'
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
        <KpiCard icon="💧" iconBg="kpi-icon-teal"  label="Latest Intensity" value={latest?.intensity ?? '—'} unit="L/kg" deltaLabel={`target ${target} L/kg`} />
        <KpiCard icon="✅" iconBg="kpi-icon-green"  label="Months On Track" value={onTrack} unit="" />
        <KpiCard icon="⚠️" iconBg="kpi-icon-amber"  label="Months At Risk"  value={atRisk}  unit="" />
        <KpiCard icon="🎯" iconBg="kpi-icon-blue"   label="Annual Goal"     value={targetPct != null ? `-${targetPct}%` : '—'} unit="" deltaLabel="reduction vs last year" />
      </div>

      {/* ── Charts ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-6)', marginBottom: 'var(--space-6)' }}>

        {/* Line Chart — intensity trend per estate */}
        <div className="section-card">
          <div className="section-card-header">
            <div className="section-card-title">
              <div className="section-card-title-icon">📈</div>
              Intensity Trend by Estate
            </div>
          </div>
          <div className="section-card-body">
            <svg viewBox="0 0 400 200" width="100%" style={{ overflow: 'visible' }}>
              {/* Grid lines */}
              {[2, 3, 4, 5].map(v => {
                const y = 180 - ((v - 2) / 3) * 160;
                return (
                  <g key={v}>
                    <line x1="40" y1={y} x2="390" y2={y} stroke="var(--color-border)" strokeDasharray="4" strokeWidth="1" />
                    <text x="35" y={y + 4} fontSize="10" fill="var(--color-text-muted)" textAnchor="end">{v}</text>
                  </g>
                );
              })}
              {/* Target line */}
              {(() => {
                const ty = 180 - ((target - 2) / 3) * 160;
                return <line x1="40" y1={ty} x2="390" y2={ty} stroke="var(--color-danger)" strokeDasharray="6 3" strokeWidth="1.5" opacity="0.6" />;
              })()}
              {/* Lines per estate */}
              {Object.entries(
                waterData.reduce((g, w) => { if (!g[w.estate]) g[w.estate] = []; g[w.estate].push(w); return g; }, {})
              ).map(([estate, rows], ei) => {
                const colors = ['#2563eb','#16a34a','#d97706','#9333ea'];
                const color = colors[ei % colors.length];
                const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                const points = rows.map(w => {
                  const mx = months.indexOf(w.month);
                  const x = 40 + (mx / 11) * 350;
                  const y = 180 - ((w.intensity - 2) / 3) * 160;
                  return `${x},${y}`;
                }).join(' ');
                return (
                  <g key={estate}>
                    <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    {rows.map(w => {
                      const mx = months.indexOf(w.month);
                      const x = 40 + (mx / 11) * 350;
                      const y = 180 - ((w.intensity - 2) / 3) * 160;
                      return <circle key={w.month} cx={x} cy={y} r="3" fill={color} />;
                    })}
                  </g>
                );
              })}
              {/* Month labels */}
              {['Jan','Feb','Mar','Apr','May'].map((m, i) => {
                const x = 40 + (i / 11) * 350;
                return <text key={m} x={x} y="196" fontSize="10" fill="var(--color-text-muted)" textAnchor="middle">{m}</text>;
              })}
            </svg>
            {/* Legend */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 8 }}>
              {Object.keys(waterData.reduce((g, w) => { g[w.estate] = 1; return g; }, {})).map((estate, ei) => {
                const colors = ['#2563eb','#16a34a','#d97706','#9333ea'];
                return (
                  <div key={estate} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                    <div style={{ width: 12, height: 3, borderRadius: 2, background: colors[ei % colors.length] }} />
                    {estate}
                  </div>
                );
              })}
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                <div style={{ width: 12, height: 2, borderRadius: 2, background: 'var(--color-danger)', opacity: 0.6 }} />
                Target
              </div>
            </div>
          </div>
        </div>

        {/* Bar Chart — compare estates per month */}
        <div className="section-card">
          <div className="section-card-header">
            <div className="section-card-title">
              <div className="section-card-title-icon">📊</div>
              Estate Comparison by Month
            </div>
          </div>
          <div className="section-card-body">
            <svg viewBox="0 0 400 200" width="100%" style={{ overflow: 'visible' }}>
              {/* Grid lines */}
              {[2, 3, 4, 5].map(v => {
                const y = 180 - ((v - 2) / 3) * 160;
                return (
                  <g key={v}>
                    <line x1="40" y1={y} x2="390" y2={y} stroke="var(--color-border)" strokeDasharray="4" strokeWidth="1" />
                    <text x="35" y={y + 4} fontSize="10" fill="var(--color-text-muted)" textAnchor="end">{v}</text>
                  </g>
                );
              })}
              {/* Bars grouped by month */}
              {(() => {
                const months = ['Jan','Feb','Mar','Apr','May'];
                const estateNames = [...new Set(waterData.map(w => w.estate))];
                const colors = ['#2563eb','#16a34a','#d97706','#9333ea'];
                const groupW = 60;
                const barW = Math.min(10, (groupW - 4) / estateNames.length);
                return months.map((month, mi) => {
                  const gx = 50 + mi * groupW;
                  return (
                    <g key={month}>
                      {estateNames.map((estate, ei) => {
                        const row = waterData.find(w => w.estate === estate && w.month === month);
                        if (!row) return null;
                        const barH = ((row.intensity - 2) / 3) * 160;
                        const x = gx + ei * (barW + 1);
                        const y = 180 - barH;
                        return (
                          <rect key={estate} x={x} y={y} width={barW} height={barH}
                            fill={colors[ei % colors.length]} opacity="0.8" rx="1"
                          />
                        );
                      })}
                      <text x={gx + (estateNames.length * (barW + 1)) / 2} y="196" fontSize="10" fill="var(--color-text-muted)" textAnchor="middle">{month}</text>
                    </g>
                  );
                });
              })()}
            </svg>
            {/* Legend */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 8 }}>
              {[...new Set(waterData.map(w => w.estate))].map((estate, ei) => {
                const colors = ['#2563eb','#16a34a','#d97706','#9333ea'];
                return (
                  <div key={estate} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: colors[ei % colors.length] }} />
                    {estate}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="table-wrap" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="table-header-bar">
          <div>
            <div className="table-title">Monthly Water Intensity</div>
            <div className="table-subtitle">Factory water use per kg tea produced · {CURRENT_YEAR}</div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span className="badge badge-success">{onTrack}/{waterData.length} On Track</span>
            <button
              onClick={() => setShowModal(true)}
              style={{
                padding: '7px 16px', borderRadius: 8, border: 'none',
                background: 'var(--color-primary)', color: '#fff',
                fontWeight: 600, fontSize: '0.8125rem', cursor: 'pointer'
              }}
            >
              + Log Water Data
            </button>
          </div>
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
            {Object.entries(
              waterData.reduce((groups, w) => {
              const key = w.estate || 'Unknown';
              if (!groups[key]) groups[key] = [];
              groups[key].push(w);
              return groups;
              }, {})
            ).map(([estateName, rows]) => (
              <>
                <tr key={`header-${estateName}`} style={{ backgroundColor: 'var(--color-surface-2, #f0f4f8)' }}>
                  <td colSpan={6} style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--color-text)', padding: '0.6rem 1rem', letterSpacing: '0.03em' }}>
                    🏡 {estateName}
                  </td>
                </tr>
                {rows.map(w => {
                  const variance = (w.intensity - w.target).toFixed(2);
                  const ok  = w.status === 'on_track';
                  const pct = Math.min(100, (w.intensity / 6) * 100);
                  return (
                    <tr key={`${estateName}-${w.month}`}>
                      <td style={{ fontWeight: 600, paddingLeft: '2rem' }}>{w.month}</td>
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
                      <td>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button
                            onClick={() => setEditRow(w)}
                            style={{ padding: '3px 10px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => setDeleteRow(w)}
                            style={{ padding: '3px 10px', borderRadius: 6, border: '1px solid rgba(220,38,38,0.3)', background: 'transparent', color: 'var(--color-danger)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </>
            ))}
          </tbody>
        </table>
      </div>

      {worst.intensity > 0 && worst.status !== 'on_track' && (
        <div className="alert alert-info">
          <span>ℹ️</span>
          <span>{worst.month} recorded the highest intensity at {worst.intensity} L/kg. Review factory maintenance logs and irrigation schedules.</span>
        </div>
      )}

      {/* ── Edit Modal ── */}
      {editRow && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--color-surface)', borderRadius: 16, padding: 32, width: '100%', maxWidth: 420, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 20 }}>Edit — {editRow.estate} {editRow.month}</div>
            <WaterEditForm
              token={token}
              row={editRow}
              onClose={() => setEditRow(null)}
              onSaved={() => {
                setEditRow(null);
                setLoading(true);
                apiService.getWaterUsage(token, CURRENT_YEAR).then(usage => {
                  const formatted = usage.map(w => ({ month: w.month, estate: w.estate, id: w.id, water_m3: w.water_m3, yield_kg: w.yield_kg, intensity: w.intensity_l_per_kg, target, status: w.intensity_l_per_kg <= target ? 'on_track' : 'at_risk' }));
                  setWaterData(formatted);
                }).finally(() => setLoading(false));
              }}
            />
          </div>
        </div>
      )}

      {/* ── Delete Confirmation ── */}
      {deleteRow && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--color-surface)', borderRadius: 16, padding: 32, width: '100%', maxWidth: 400, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 8 }}>Delete Entry</div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: 20 }}>
              Are you sure you want to delete <strong>{deleteRow.estate} — {deleteRow.month}</strong>?
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setDeleteRow(null)} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600 }}>Cancel</button>
              <button
                onClick={async () => {
                  try {
                    await apiService.deleteWaterUsage(token, deleteRow.id);
                    setDeleteRow(null);
                    setLoading(true);
                    const usage = await apiService.getWaterUsage(token, CURRENT_YEAR);
                    setWaterData(usage.map(w => ({ month: w.month, estate: w.estate, id: w.id, water_m3: w.water_m3, yield_kg: w.yield_kg, intensity: w.intensity_l_per_kg, target, status: w.intensity_l_per_kg <= target ? 'on_track' : 'at_risk' })));
                  } catch(e) { console.error(e); }
                  finally { setLoading(false); }
                }}
                style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--color-danger)', color: '#fff', cursor: 'pointer', fontWeight: 600 }}
              >
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ── Tab: Fertilizer ──────────────────────────────────────────────────── */
function FertilizerTab({ onOverdueChange }) {
  const { token, canWrite } = useAuth();
  const today = new Date().toISOString().slice(0, 10);

  const [estates, setEstates] = useState([]);
  const [estateId, setEstateId] = useState('');
  const [alerts, setAlerts] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [selectedScheduleId, setSelectedScheduleId] = useState('');
  const [schedule, setSchedule] = useState([]);
  const [scheduleStatus, setScheduleStatus] = useState('due,overdue');
  const [selectedBlock, setSelectedBlock] = useState('');
  const [subTab, setSubTab] = useState('schedule'); // 'schedule' | 'history'
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [genResult, setGenResult] = useState(null);

  // Application history — lazy loaded when history tab is first opened
  const [applications, setApplications] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  // Application modal
  const [fertTypes, setFertTypes] = useState([]);
  const [blocks, setBlocks] = useState([]);
  const [appModal, setAppModal] = useState(null); // null | { mode:'done', entry } | { mode:'manual' }
  const [appForm, setAppForm] = useState({});
  const [appSaving, setAppSaving] = useState(false);
  const [appError, setAppError] = useState('');

  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiService.getEstates(token),
      apiService.getFertilizerTypes(token),
    ]).then(([estData, typeData]) => {
      setEstates(estData);
      if (estData.length > 0) setEstateId(estData[0].id);
      setFertTypes(Array.isArray(typeData) ? typeData : []);
    }).catch(() => {});
  }, [token]);

  // On estate change: fetch alerts + schedule headers + blocks in parallel
  useEffect(() => {
    if (!token || !estateId) return;
    setLoading(true);
    setError('');
    setSubTab('schedule');
    setHistoryLoaded(false);
    setApplications([]);
    setSchedules([]);
    setSelectedScheduleId('');
    setSchedule([]);
    Promise.all([
      apiService.getFertilizerAlerts(token, estateId),
      apiService.getFertilizerSchedules(token, estateId),
      apiService.getBlocks(token, estateId),
    ])
      .then(([a, hdrs, b]) => {
        const blockList  = Array.isArray(b)    ? b    : [];
        const alertList  = Array.isArray(a)    ? a    : [];
        const hdrList    = Array.isArray(hdrs) ? hdrs : [];
        setAlerts(alertList);
        setBlocks(blockList);
        setSelectedBlock(blockList.length > 0 ? blockList[0].id : '');
        setSchedules(hdrList);
        const active = hdrList.find(h => h.status === 'active') || hdrList[0];
        setSelectedScheduleId(active ? active.id : '');
        if (onOverdueChange) onOverdueChange();
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, estateId]);

  // Fetch entries whenever the selected schedule or status filter changes
  useEffect(() => {
    if (!token || !selectedScheduleId) { setSchedule([]); return; }
    apiService.getFertilizerScheduleEntries(token, selectedScheduleId, { status: scheduleStatus || undefined })
      .then(rows => setSchedule(Array.isArray(rows) ? rows : []))
      .catch(() => setSchedule([]));
  }, [token, selectedScheduleId, scheduleStatus]);

  const reload = async () => {
    const [a, hdrs] = await Promise.all([
      apiService.getFertilizerAlerts(token, estateId),
      apiService.getFertilizerSchedules(token, estateId),
    ]);
    const alertList = Array.isArray(a)    ? a    : [];
    const hdrList   = Array.isArray(hdrs) ? hdrs : [];
    setAlerts(alertList);
    setSchedules(hdrList);
    if (onOverdueChange) onOverdueChange();
    if (selectedScheduleId) {
      apiService.getFertilizerScheduleEntries(token, selectedScheduleId, { status: scheduleStatus || undefined })
        .then(rows => setSchedule(Array.isArray(rows) ? rows : []));
    }
    if (historyLoaded) {
      apiService.getFertilizerApplications(token, { estateId, limit: 500 })
        .then(apps => setApplications(Array.isArray(apps) ? apps : []));
    }
  };

  // Lazy-load history when the tab is first opened
  useEffect(() => {
    if (subTab !== 'history' || historyLoaded || !token || !estateId) return;
    setHistoryLoading(true);
    apiService.getFertilizerApplications(token, { estateId, limit: 500 })
      .then(apps => { setApplications(Array.isArray(apps) ? apps : []); setHistoryLoaded(true); })
      .catch(() => {})
      .finally(() => setHistoryLoading(false));
  }, [subTab, token, estateId]);

  const nextMonthStr = (() => {
    const d = new Date();
    const y = d.getMonth() === 11 ? d.getFullYear() + 1 : d.getFullYear();
    const m = d.getMonth() === 11 ? 1 : d.getMonth() + 2;
    return `${y}-${String(m).padStart(2, '0')}-01`;
  })();

  const fmtMonth = iso => {
    if (!iso) return '';
    const [y, mo] = iso.split('-');
    return new Date(y, mo - 1, 1).toLocaleString('default', { month: 'long', year: 'numeric' });
  };

  const handleGenerate = async () => {
    if (!estateId) return;
    setGenerating(true); setError(''); setGenResult(null);
    try {
      const result = await apiService.generateFertilizerScheduleForMonth(token, {
        estate_id: estateId,
        period_start: nextMonthStr,
      });
      setGenResult(result);
      const hdrs = await apiService.getFertilizerSchedules(token, estateId);
      const hdrList = Array.isArray(hdrs) ? hdrs : [];
      setSchedules(hdrList);
      // Stay on current schedule; only select the new one if nothing was selected
      if (!selectedScheduleId && result.schedule_id) setSelectedScheduleId(result.schedule_id);
    } catch (e) {
      if (e.message && e.message.includes('already exists')) {
        setError(`A schedule for ${fmtMonth(nextMonthStr)} already exists. Manage it in the Fertilizer Schedules tab.`);
      } else {
        setError(e.message);
      }
    }
    finally { setGenerating(false); }
  };

  const handleSkip = async (id) => {
    try {
      await apiService.updateFertilizerScheduleEntry(token, id, { status: 'skipped' });
      await reload();
    } catch (e) { setError(e.message); }
  };

  const openDoneModal = (entry) => {
    setAppForm({
      block_id: entry.block_id,
      fertilizer_type_id: entry.fertilizer_type_id || '',
      application_date: today,
      quantity_kg: entry.total_kg_needed ? String(Math.round(Number(entry.total_kg_needed))) : '',
      rate_kg_per_ha: entry.scheduled_rate_kg_per_ha ? String(entry.scheduled_rate_kg_per_ha) : '',
      recommendation: 'apply_now',
      notes: '',
      schedule_id: entry.id,
    });
    setAppError('');
    setAppModal({ mode: 'done', entry });
  };

  const openManualModal = () => {
    setAppForm({
      block_id: blocks.length > 0 ? blocks[0].id : '',
      fertilizer_type_id: fertTypes.length > 0 ? fertTypes[0].id : '',
      application_date: today,
      quantity_kg: '',
      rate_kg_per_ha: '',
      recommendation: 'apply_now',
      notes: '',
      schedule_id: null,
    });
    setAppError('');
    setAppModal({ mode: 'manual' });
  };

  const handleRecordApplication = async () => {
    if (!appForm.quantity_kg || Number(appForm.quantity_kg) <= 0) {
      setAppError('Quantity must be greater than 0'); return;
    }
    setAppSaving(true); setAppError('');
    try {
      await apiService.recordFertilizerApplication(token, {
        block_id: appForm.block_id,
        fertilizer_type_id: appForm.fertilizer_type_id,
        application_date: appForm.application_date,
        quantity_kg: Number(appForm.quantity_kg),
        rate_kg_per_ha: appForm.rate_kg_per_ha ? Number(appForm.rate_kg_per_ha) : undefined,
        recommendation: appForm.recommendation || undefined,
        notes: appForm.notes || undefined,
        schedule_id: appForm.schedule_id || undefined,
      });
      setAppModal(null);
      await reload();
    } catch (e) { setAppError(e.message); }
    finally { setAppSaving(false); }
  };

  const overdueCount = alerts.filter(a => a.status === 'overdue').length;
  const dueCount = alerts.filter(a => a.status === 'due').length;
  const pendingCount = alerts.filter(a => a.status === 'pending').length;

  // Derive block tabs from loaded blocks; count open entries per block from schedule
  const openStatuses = new Set(['pending', 'due', 'overdue']);
  const blockTabs = blocks
    .map(b => ({
      id: b.id,
      code: b.block_code,
      openCount: schedule.filter(s => s.block_id === b.id && openStatuses.has(s.status)).length,
      total: schedule.filter(s => s.block_id === b.id).length,
    }))
    .sort((a, b) => a.code.localeCompare(b.code));

  const visibleSchedule = selectedBlock
    ? schedule.filter(s => s.block_id === selectedBlock)
    : schedule;

  const visibleApplications = selectedBlock
    ? applications.filter(a => a.block_id === selectedBlock)
    : applications;

  const statusBadge = { pending: 'badge-neutral', due: 'badge-warning', overdue: 'badge-danger', done: 'badge-success', skipped: 'badge-neutral' };
  const statusLabel = { pending: 'Pending', due: 'Due', overdue: 'Overdue', done: 'Done', skipped: 'Skipped' };

  const inputStyle = { width: '100%', padding: '8px 12px', borderRadius: 8, boxSizing: 'border-box', border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.875rem' };
  const labelStyle = { display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 };

  return (
    <>
      {/* Controls */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Estate</div>
          <select value={estateId} onChange={e => { setEstateId(e.target.value); setGenResult(null); }} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.875rem', fontWeight: 600, cursor: 'pointer' }}>
            {estates.length === 0 && <option value="">Loading…</option>}
            {estates.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
        </div>
        {schedules.length > 0 && (
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Schedule</div>
            <select value={selectedScheduleId} onChange={e => setSelectedScheduleId(e.target.value)}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.875rem', fontWeight: 600, cursor: 'pointer' }}>
              {schedules.map(h => (
                <option key={h.id} value={h.id}>
                  {fmtMonth(h.period_start)}{h.status === 'closed' ? ' (inactive)' : ''}
                </option>
              ))}
            </select>
          </div>
        )}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          {canWrite && (
            <button onClick={handleGenerate} disabled={generating || !estateId}
              style={{ padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', background: generating ? '#6b7280' : 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8125rem', opacity: !estateId ? 0.5 : 1 }}>
              {generating ? 'Generating…' : `⚡ Generate ${fmtMonth(nextMonthStr)}`}
            </button>
          )}
          {canWrite && (
            <button onClick={openManualModal} disabled={!estateId || blocks.length === 0}
              style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', cursor: 'pointer', background: 'transparent', color: 'var(--color-text)', fontWeight: 600, fontSize: '0.8125rem', opacity: !estateId ? 0.5 : 1 }}>
              + Record Application
            </button>
          )}
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(220,38,38,0.08)', color: 'var(--color-danger)', marginBottom: 20, fontSize: '0.875rem', border: '1px solid rgba(220,38,38,0.2)' }}>
          {error}
        </div>
      )}

      {genResult && (
        <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(22,163,74,0.08)', color: 'var(--color-success)', marginBottom: 20, fontSize: '0.875rem', border: '1px solid rgba(22,163,74,0.2)' }}>
          Schedule generated for <strong>{fmtMonth(genResult.period_start)}</strong>: {genResult.inserted} new entries · {genResult.skipped_existing ?? 0} skipped existing · {genResult.skipped_recent ?? 0} applied recently
        </div>
      )}

      {/* KPI cards */}
      <div className="kpi-grid">
        <KpiCard icon="🚨" iconBg="kpi-icon-amber" label="Overdue"    value={overdueCount}   unit="" />
        <KpiCard icon="⚠️" iconBg="kpi-icon-amber" label="Due Now"    value={dueCount}       unit="" />
        <KpiCard icon="📅" iconBg="kpi-icon-blue"  label="Pending"    value={pendingCount}   unit="" />
        <KpiCard icon="🌱" iconBg="kpi-icon-green" label="All Alerts" value={alerts.length}  unit="" />
      </div>

      {loading && <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading fertilizer data…</div>}

      {/* Tab bar + filters */}
      <div style={{ display: 'flex', alignItems: 'center', borderBottom: '2px solid var(--color-border)', marginBottom: 'var(--space-5)', gap: 0 }}>
        {[
          { id: 'schedule', label: 'Schedule' },
          { id: 'history',  label: 'Application History' },
        ].map(t => (
          <button key={t.id} onClick={() => setSubTab(t.id)} style={{
            padding: '9px 20px', background: 'transparent', border: 'none', cursor: 'pointer',
            fontWeight: 600, fontSize: '0.875rem',
            color: subTab === t.id ? 'var(--color-primary)' : 'var(--color-text-muted)',
            borderBottom: subTab === t.id ? '2px solid var(--color-primary)' : '2px solid transparent',
            marginBottom: -2,
          }}>
            {t.label}
          </button>
        ))}
        {/* Filters pushed to the right */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', paddingBottom: 6 }}>
          <select value={selectedBlock} onChange={e => setSelectedBlock(e.target.value)}
            style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.8125rem', fontWeight: 600 }}>
            {blockTabs.map(b => <option key={b.id} value={b.id}>{b.code}</option>)}
            <option value="">All Blocks</option>
          </select>
          {subTab === 'schedule' && (
            <select value={scheduleStatus} onChange={e => setScheduleStatus(e.target.value)}
              style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.8125rem', minWidth: 140 }}>
              <option value="due,overdue">Due &amp; Overdue</option>
              <option value="pending">Pending</option>
              <option value="done">Done</option>
              <option value="skipped">Skipped</option>
              <option value="">All</option>
            </select>
          )}
        </div>
      </div>

      {/* Schedule tab */}
      {subTab === 'schedule' && (
        <div className="table-wrap">
          <div className="table-header-bar">
            <div>
              <div className="table-title">Schedule</div>
              <div className="table-subtitle">{visibleSchedule.length} entr{visibleSchedule.length === 1 ? 'y' : 'ies'}</div>
            </div>
          </div>
          {loading ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading…</div>
          ) : visibleSchedule.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)' }}>
              No entries for this filter.
              {canWrite && <span> Click <strong>Generate Schedule</strong> to create entries.</span>}
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  {!selectedBlock && <th>Block</th>}
                  <th>Fertilizer</th>
                  <th>Due Date</th>
                  <th>Status</th>
                  <th>Rate kg/ha</th>
                  <th>Total Kg</th>
                  {canWrite && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {visibleSchedule.map(s => (
                  <tr key={s.id}>
                    {!selectedBlock && <td style={{ fontWeight: 600 }}>{s.block_code}</td>}
                    <td>{s.fertilizer_code || '—'}</td>
                    <td style={{ fontSize: '0.8125rem' }}>{s.due_date}</td>
                    <td><span className={`badge ${statusBadge[s.status] || 'badge-neutral'}`}>{statusLabel[s.status] || s.status}</span></td>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>{s.scheduled_rate_kg_per_ha ? `${s.scheduled_rate_kg_per_ha} kg/ha` : '—'}</td>
                    <td style={{ fontWeight: 600 }}>{s.total_kg_needed ? `${Number(s.total_kg_needed).toFixed(0)} kg` : '—'}</td>
                    {canWrite && (
                      <td>
                        {(s.status === 'due' || s.status === 'overdue' || s.status === 'pending') && (
                          <div style={{ display: 'flex', gap: 6 }}>
                            <button onClick={() => openDoneModal(s)}
                              style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: 'var(--color-success)', color: '#fff', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>
                              Done
                            </button>
                            <button onClick={() => handleSkip(s.id)}
                              style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>
                              Skip
                            </button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Application History tab */}
      {subTab === 'history' && (
        <div className="table-wrap">
          <div className="table-header-bar">
            <div>
              <div className="table-title">Application History</div>
              <div className="table-subtitle">{visibleApplications.length} record{visibleApplications.length !== 1 ? 's' : ''}</div>
            </div>
          </div>
          {historyLoading ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading…</div>
          ) : visibleApplications.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)' }}>No applications recorded yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  {!selectedBlock && <th>Block</th>}
                  <th>Date</th>
                  <th>Fertilizer</th>
                  <th style={{ textAlign: 'right' }}>Qty (kg)</th>
                  <th style={{ textAlign: 'right' }}>Rate (kg/ha)</th>
                  <th>Recommendation</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {visibleApplications.map(a => (
                  <tr key={a.id}>
                    {!selectedBlock && <td style={{ fontWeight: 600 }}>{a.block_code}</td>}
                    <td style={{ fontSize: '0.8125rem' }}>{a.application_date}</td>
                    <td style={{ fontSize: '0.8125rem' }}>{a.fertilizer_code || a.fertilizer_name || '—'}</td>
                    <td style={{ textAlign: 'right', fontWeight: 600, fontSize: '0.8125rem' }}>{a.quantity_kg != null ? `${Number(a.quantity_kg).toFixed(0)} kg` : '—'}</td>
                    <td style={{ textAlign: 'right', fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>{a.rate_kg_per_ha ? `${a.rate_kg_per_ha}` : '—'}</td>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>{a.recommendation ? a.recommendation.replace('_', ' ') : '—'}</td>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', maxWidth: 180 }}>{a.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {!loading && schedules.length === 0 && !error && (
        <div style={{ padding: 48, textAlign: 'center', background: 'var(--color-surface-2)', borderRadius: 14, border: '1px solid var(--color-border)', marginTop: 'var(--space-6)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 10 }}>🌱</div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>No schedules for this estate</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            {canWrite ? `Click "Generate ${fmtMonth(nextMonthStr)}" to create the first schedule.` : 'No schedule has been generated yet.'}
          </div>
        </div>
      )}

      {/* ── Record / Manual Application Modal ── */}
      {appModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--color-surface)', borderRadius: 16, padding: 32, width: '100%', maxWidth: 480, boxShadow: '0 20px 60px rgba(0,0,0,0.3)', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 4 }}>
              {appModal.mode === 'done' ? 'Record Application' : 'Manual Application Entry'}
            </div>
            {appModal.mode === 'done' && (
              <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginBottom: 20 }}>
                {appModal.entry.block_code} · {appModal.entry.fertilizer_code} · scheduled {appModal.entry.due_date}
              </div>
            )}
            {appModal.mode === 'manual' && <div style={{ marginBottom: 20 }} />}

            {appError && (
              <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(220,38,38,0.1)', color: 'var(--color-danger)', marginBottom: 16, fontSize: '0.875rem' }}>
                {appError}
              </div>
            )}

            {/* Block selector — manual only */}
            {appModal.mode === 'manual' && (
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Block</label>
                <select value={appForm.block_id} onChange={e => setAppForm(p => ({ ...p, block_id: e.target.value }))} style={inputStyle}>
                  {blocks.map(b => <option key={b.id} value={b.id}>{b.block_code}</option>)}
                </select>
              </div>
            )}

            {/* Fertilizer type — manual only */}
            {appModal.mode === 'manual' && (
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Fertilizer Product</label>
                <select value={appForm.fertilizer_type_id} onChange={e => setAppForm(p => ({ ...p, fertilizer_type_id: e.target.value }))} style={inputStyle}>
                  {fertTypes.map(t => <option key={t.id} value={t.id}>{t.code} — {t.name}</option>)}
                </select>
              </div>
            )}

            {/* Application date */}
            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Application Date</label>
              <input type="date" value={appForm.application_date} onChange={e => setAppForm(p => ({ ...p, application_date: e.target.value }))} style={inputStyle} />
            </div>

            {/* Quantity + Rate side by side */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
              <div>
                <label style={labelStyle}>Quantity (kg) <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                <input type="number" min="0" step="0.1" value={appForm.quantity_kg} onChange={e => setAppForm(p => ({ ...p, quantity_kg: e.target.value }))} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Rate (kg/ha)</label>
                <input type="number" min="0" step="0.1" value={appForm.rate_kg_per_ha} onChange={e => setAppForm(p => ({ ...p, rate_kg_per_ha: e.target.value }))} placeholder="Auto" style={inputStyle} />
              </div>
            </div>

            {/* Recommendation */}
            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Recommendation</label>
              <select value={appForm.recommendation} onChange={e => setAppForm(p => ({ ...p, recommendation: e.target.value }))} style={inputStyle}>
                <option value="apply_now">Apply Now</option>
                <option value="delay">Delay</option>
                <option value="increase_dosage">Increase Dosage</option>
                <option value="skipped">Skipped</option>
              </select>
            </div>

            {/* Notes */}
            <div style={{ marginBottom: 20 }}>
              <label style={labelStyle}>Notes</label>
              <textarea value={appForm.notes} onChange={e => setAppForm(p => ({ ...p, notes: e.target.value }))} rows={2} placeholder="Optional" style={{ ...inputStyle, resize: 'vertical' }} />
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => { setAppModal(null); setAppError(''); }} disabled={appSaving}
                style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={handleRecordApplication} disabled={appSaving}
                style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontWeight: 600, opacity: appSaving ? 0.7 : 1 }}>
                {appSaving ? 'Saving…' : 'Record Application'}
              </button>
            </div>
          </div>
        </div>
      )}
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
  const [addingGroup, setAddingGroup] = useState(null);   // assignment id showing add-group dropdown
  const [editingTarget, setEditingTarget] = useState(null); // assignment id being edited
  const [targetInputs, setTargetInputs]   = useState({});   // { assignmentId: value }
  const [savingTarget, setSavingTarget]   = useState(false);

  // Yield editing state
  const [editingYield, setEditingYield]   = useState(null);  // assignment id being edited
  const [yieldInputsTable, setYieldInputsTable] = useState({});  // { assignmentId: value }
  const [savingYield, setSavingYield]     = useState(false);

  // Group members modal (rotation view: click a group → see assigned people that month)
  const [groupMembers, setGroupMembers] = useState(null);  // null = closed
  const openGroupMembers = async (round, groupCode) => {
    setGroupMembers({ round, group_code: groupCode, loading: true, members: [] });
    try {
      const data = await apiService.getRotationMembers(token, estateId, round, groupCode);
      setGroupMembers({
        round, group_code: groupCode,
        block_code: data.block_code, period_start: data.period_start,
        members: data.members || [], loading: false,
      });
    } catch (e) {
      setGroupMembers({ round, group_code: groupCode, members: [], loading: false, error: e.message });
    }
  };

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

  const handleSaveTargetValue = async (assignmentId, newValue) => {
    if (!newValue || newValue <= 0) {
      setEditingTarget(null);
      return;
    }
    setSavingTarget(true);
    try {
      await apiService.overrideAssignment(token, assignmentId, { expected_yield_kg: parseFloat(newValue) });
      // Reload plan to reflect updated targets
      const updated = await apiService.getLabourPlan(token, plan.id);
      setPlan(updated);
      setEditingTarget(null);
    } catch (e) {
      console.error('Error saving target:', e);
      setEditingTarget(null);
    } finally {
      setSavingTarget(false);
    }
  };

  const handleSaveYieldValue = async (assignmentId, newValue) => {
    if (newValue === '' || newValue === null) {
      setEditingYield(null);
      return;
    }
    setSavingYield(true);
    try {
      const numValue = parseFloat(newValue);
      if (isNaN(numValue)) throw new Error('Invalid number');
      await apiService.recordPlanYield(token, plan.id, [{ assignment_id: assignmentId, actual_yield_kg: numValue }]);
      // Reload plan to reflect updated yields
      const updated = await apiService.getLabourPlan(token, plan.id);
      setPlan(updated);
      setEditingYield(null);
    } catch (e) {
      console.error('Error saving yield:', e);
      setEditingYield(null);
    } finally {
      setSavingYield(false);
    }
  };


  // ── KPIs derived from plan assignments
  const assignments = plan?.assignments || [];
  const totalWorkers  = assignments.reduce((s, a) => s + (a.allocated_workers ?? a.group_capacity ?? 0), 0);
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
                  <div className="table-title">Block Assignments — {monthStart}</div>
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
                    <SortHeader label="Block" field="block_code" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <SortHeader label="Group" field="group_name" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <SortHeader label="Workers" field="allocated_workers" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <SortHeader label="Predicted (kg)" field="predicted_yield_kg" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <SortHeader label="Target (kg)" field="expected_yield_kg" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <SortHeader label="Actual (kg)" field="actual_yield_kg" sort={assignSort} onSort={(f) => toggleSort(f, setAssignSort)} />
                    <th>Efficiency</th>
                    <th>Progress</th>
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
                            <span style={{ fontWeight: 600 }}>{a.allocated_workers != null ? a.allocated_workers : (a.group_capacity || '—')}</span>
                          </div>
                        </td>
                        <td style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                          {a.predicted_yield_kg ? Math.round(a.predicted_yield_kg).toLocaleString() : '—'}
                        </td>
                        <td style={{ fontWeight: 700 }}>
                          {editingTarget === a.id ? (
                            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                              <input
                                type="number"
                                min="0"
                                step="0.1"
                                value={targetInputs[a.id] ?? exp}
                                onChange={e => setTargetInputs(p => ({ ...p, [a.id]: e.target.value }))}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') handleSaveTargetValue(a.id, targetInputs[a.id]);
                                  if (e.key === 'Escape') setEditingTarget(null);
                                }}
                                autoFocus
                                disabled={savingTarget}
                                style={{
                                  width: '80px', padding: '6px 8px', borderRadius: 4, border: '2px solid var(--color-primary)',
                                  background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.9rem',
                                  fontWeight: 700
                                }}
                              />
                              <button
                                onClick={() => handleSaveTargetValue(a.id, targetInputs[a.id])}
                                disabled={savingTarget}
                                style={{
                                  padding: '4px 10px', borderRadius: 4, border: 'none', cursor: 'pointer',
                                  background: 'var(--color-success)', color: '#fff', fontWeight: 600,
                                  fontSize: '0.75rem', opacity: savingTarget ? 0.6 : 1
                                }}
                              >
                                {savingTarget ? '⏳' : '✓'}
                              </button>
                              <button
                                onClick={() => setEditingTarget(null)}
                                disabled={savingTarget}
                                style={{
                                  padding: '4px 8px', borderRadius: 4, border: '1px solid var(--color-border)',
                                  background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer',
                                  fontSize: '0.75rem', opacity: savingTarget ? 0.6 : 1
                                }}
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            <div
                              onClick={() => {
                                setEditingTarget(a.id);
                                setTargetInputs(p => ({ ...p, [a.id]: exp }));
                              }}
                              style={{
                                cursor: 'pointer', padding: '4px 8px', borderRadius: 4,
                                background: 'transparent', transition: 'background 0.2s',
                                display: 'flex', alignItems: 'center', gap: 8
                              }}
                              onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-2)'}
                              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                              title="Click to edit target value"
                            >
                              {exp ? Math.round(exp).toLocaleString() : '—'}
                              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 400 }}>✏️</span>
                            </div>
                          )}
                        </td>
                        <td style={{ fontWeight: 700 }}>
                          {editingYield === a.id ? (
                            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                              <input
                                type="number"
                                min="0"
                                step="0.1"
                                value={yieldInputsTable[a.id] ?? act ?? ''}
                                onChange={e => setYieldInputsTable(p => ({ ...p, [a.id]: e.target.value }))}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') handleSaveYieldValue(a.id, yieldInputsTable[a.id]);
                                  if (e.key === 'Escape') setEditingYield(null);
                                }}
                                autoFocus
                                disabled={savingYield}
                                style={{
                                  width: '80px', padding: '6px 8px', borderRadius: 4, border: '2px solid var(--color-primary)',
                                  background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.9rem',
                                  fontWeight: 700
                                }}
                              />
                              <button
                                onClick={() => handleSaveYieldValue(a.id, yieldInputsTable[a.id])}
                                disabled={savingYield}
                                style={{
                                  padding: '4px 10px', borderRadius: 4, border: 'none', cursor: 'pointer',
                                  background: 'var(--color-success)', color: '#fff', fontWeight: 600,
                                  fontSize: '0.75rem', opacity: savingYield ? 0.6 : 1
                                }}
                              >
                                {savingYield ? '⏳' : '✓'}
                              </button>
                              <button
                                onClick={() => setEditingYield(null)}
                                disabled={savingYield}
                                style={{
                                  padding: '4px 8px', borderRadius: 4, border: '1px solid var(--color-border)',
                                  background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer',
                                  fontSize: '0.75rem', opacity: savingYield ? 0.6 : 1
                                }}
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            <div
                              onClick={() => {
                                setEditingYield(a.id);
                                setYieldInputsTable(p => ({ ...p, [a.id]: act || '' }));
                              }}
                              style={{
                                cursor: 'pointer',
                                padding: '4px 8px', borderRadius: 4,
                                background: 'transparent', transition: 'background 0.2s',
                                display: 'flex', alignItems: 'center', gap: 8
                              }}
                              onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-2)'}
                              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                              title="Click to record actual yield"
                            >
                              {act ? Math.round(act).toLocaleString() : '—'}
                              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 400 }}>✏️</span>
                            </div>
                          )}
                        </td>
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
          <div className="table-wrap" style={{ overflowX: 'auto' }}>
            <div className="table-header-bar">
              <div>
                <div className="table-title">{rotation.cycle_name}</div>
                <div className="table-subtitle">
                  {rotation.total_rounds}-round cycle · {rotation.rounds_executed ?? rotation.total_rounds} rounds executed
                </div>
              </div>
              <span className="badge badge-neutral">{rotation.total_rounds} rounds</span>
            </div>

            {/* Progress indicator — shows only executed rounds */}
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', gap: 8 }}>
                {Array.from({ length: rotation.rounds_executed ?? rotation.total_rounds }, (_, i) => i + 1).map(rn => (
                  <div key={rn} style={{
                    flex: 1, height: 8, borderRadius: 4,
                    background: rn < rotation.current_round  ? 'var(--color-success)'
                              : rn === rotation.current_round ? 'var(--color-primary)'
                              : 'var(--color-surface-2)',
                    transition: 'background 0.3s',
                  }} title={`${roundToMonth(rn)}${rn === rotation.current_round ? ' ← current' : ''}`} />
                ))}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                {roundToMonth(rotation.current_round)} — {Math.round(((rotation.rounds_executed ?? rotation.total_rounds) / rotation.total_rounds) * 100)}% through cycle
              </div>
            </div>

            <table style={{ minWidth: 'max-content', width: '100%' }}>
              <thead>
                <tr>
                  <SortHeader label="Month" field="round" sort={rotSort} onSort={(f) => toggleSort(f, setRotSort)} />
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
                        {roundToMonth(rn)}
                        {isCurrent && (
                          <span className="badge badge-success" style={{ marginLeft: 8, fontSize: '0.65rem' }}>current</span>
                        )}
                      </td>
                      {cells.map(c => {
                        const actual = actualByBlock?.[c.block_code];
                        const changed = actual && actual.group_code !== c.group_code;
                        const groupCode = (actual ? actual.group_code : c.group_code) || c.group_code;
                        const workers = actual
                          ? (actual.allocated_workers ?? actual.group_capacity ?? c.capacity)
                          : c.capacity;
                        return (
                          <td key={c.block_code} style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                            {groupCode ? (
                              <button
                                onClick={() => openGroupMembers(parseInt(rn), groupCode)}
                                title={`View people assigned to ${groupCode} in ${roundToMonth(rn)}`}
                                style={{
                                  background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                                  textAlign: 'left', font: 'inherit', color: 'inherit', width: '100%',
                                }}
                              >
                                <div style={{ fontWeight: 600, color: 'var(--color-primary)', textDecoration: 'underline dotted', textUnderlineOffset: 2 }}>
                                  {groupCode}
                                </div>
                                <div style={{ fontSize: '0.7rem' }}>{workers} workers</div>
                              </button>
                            ) : (
                              <span style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>—</span>
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
                    ['skill_type',      'Skill',      [['plucker','Picker'],['supervisor','Supervisor'],['driver','Driver']]],
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

      {/* ── Group Members Modal (rotation view: who was assigned to a group that month) ── */}
      {groupMembers && (
        <div
          onClick={() => setGroupMembers(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'var(--color-surface)', borderRadius: 16, padding: 28,
              width: '100%', maxWidth: 520, boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
              maxHeight: '85vh', overflowY: 'auto',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>
                  {groupMembers.group_code} — {roundToMonth(groupMembers.round)}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                  {groupMembers.block_code ? `Block ${groupMembers.block_code}` : ''}
                  {groupMembers.loading ? '' : ` · ${groupMembers.members.length} people assigned`}
                </div>
              </div>
              <button
                onClick={() => setGroupMembers(null)}
                style={{ background: 'none', border: 'none', fontSize: '1.4rem', cursor: 'pointer', color: 'var(--color-text-muted)', lineHeight: 1 }}
              >×</button>
            </div>

            {groupMembers.loading ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading…</div>
            ) : groupMembers.error ? (
              <div style={{ padding: 16, color: 'var(--color-danger)' }}>{groupMembers.error}</div>
            ) : groupMembers.members.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)' }}>
                No snapshot recorded for this group/month.
              </div>
            ) : (
              <table style={{ width: '100%', marginTop: 12 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left' }}>Code</th>
                    <th style={{ textAlign: 'left' }}>Name</th>
                    <th style={{ textAlign: 'left' }}>Role</th>
                  </tr>
                </thead>
                <tbody>
                  {groupMembers.members.map(m => (
                    <tr key={m.employee_id}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{m.employee_code}</td>
                      <td>{m.full_name}</td>
                      <td>
                        <span className={`badge ${m.skill_type === 'supervisor' ? 'badge-success' : 'badge-neutral'}`} style={{ fontSize: '0.65rem' }}>
                          {m.skill_type}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
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

/* ── Tab: Yield Predictions ──────────────────────────────────────────────── */
function YieldPredictionTab() {
  const { token } = useAuth();
  const [estates, setEstates] = useState([]);
  const [estateId, setEstateId] = useState('');
  const [year, setYear] = useState(CURRENT_YEAR);
  const [month, setMonth] = useState(CURRENT_MONTH);
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

/* ── Tab: Estates & Blocks ────────────────────────────────────── */
function EstateBlocksTab() {
  const { token, canWrite, isManager } = useAuth();
  const [estates, setEstates] = useState([]);
  const [selectedEstate, setSelectedEstate] = useState(null);
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [editingEstate, setEditingEstate] = useState(null);
  const [editingBlock, setEditingBlock] = useState(null);
  const [estateForm, setEstateForm] = useState({ name: '', region: '' });
  const [blockForm, setBlockForm] = useState({ block_code: '', soil_type: '', growth_stage: '', area_hectares: '', state: 'active' });
  const [saving, setSaving] = useState(false);
  const stateOptions = ['preparation', 'planting', 'growing', 'harvesting', 'fallow', 'maintenance', 'active'];

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    apiService.getEstates(token).then(data => { setEstates(data || []); if (data.length > 0) setSelectedEstate(data[0]); }).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    if (!token || !selectedEstate) return;
    apiService.getBlocks(token, selectedEstate.id).then(data => setBlocks(data || [])).catch(e => setError(e.message));
  }, [token, selectedEstate]);

  const handleSaveEstate = async () => {
    if (!estateForm.name || !estateForm.region) { setError('Name and region required'); return; }
    setSaving(true);
    try {
      if (editingEstate && editingEstate !== 'new') {
        await apiService.updateEstate(token, editingEstate.id, estateForm);
      } else {
        await apiService.createEstate(token, estateForm);
      }
      setEditingEstate(null); setEstateForm({ name: '', region: '' });
      const updated = await apiService.getEstates(token);
      setEstates(updated); setError('');
      if (editingEstate === 'new' && updated.length > 0) setSelectedEstate(updated[updated.length - 1]);
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  };

  const handleDeleteEstate = async (estateId) => {
    if (!confirm('Delete estate & all blocks/employees/plans?')) return;
    try {
      await apiService.deleteEstate(token, estateId);
      const updated = await apiService.getEstates(token);
      setEstates(updated);
      if (selectedEstate?.id === estateId) setSelectedEstate(updated[0] || null);
    } catch (e) { setError(e.message); }
  };

  const handleSaveBlock = async () => {
    if (!blockForm.block_code) { setError('Block code required'); return; }
    setSaving(true);
    try {
      if (editingBlock && editingBlock !== 'new') {
        await apiService.updateBlock(token, editingBlock.id, blockForm);
      } else {
        await apiService.createBlock(token, { estate_id: selectedEstate.id, ...blockForm });
      }
      setEditingBlock(null); setBlockForm({ block_code: '', soil_type: '', growth_stage: '', area_hectares: '', state: 'active' });
      const updated = await apiService.getBlocks(token, selectedEstate.id);
      setBlocks(updated); setError('');
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  };

  const handleDeleteBlock = async (blockId) => {
    if (!confirm('Delete block?')) return;
    try {
      await apiService.deleteBlock(token, blockId);
      const updated = await apiService.getBlocks(token, selectedEstate.id);
      setBlocks(updated);
    } catch (e) { setError(e.message); }
  };

  return (
    <>
      {error && <div style={{ padding: '12px 16px', borderRadius: 8, background: 'rgba(220,38,38,0.08)', color: 'var(--color-danger)', marginBottom: 'var(--space-4)' }}>{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 'var(--space-5)' }}>
        {/* Estates Panel */}
        <div className="table-wrap">
          <div className="table-header-bar"><div><div className="table-title">Estates</div><div className="table-subtitle">{estates.length} total</div></div></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 'var(--space-4)' }}>
            {(canWrite || isManager) && (
              <button onClick={() => { setEditingEstate('new'); setEstateForm({ name: '', region: '' }); }} style={{ padding: '8px 12px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8125rem', width: '100%' }}>+ New Estate</button>
            )}
            {editingEstate && (
              <div style={{ padding: 'var(--space-3)', background: 'var(--color-surface)', borderRadius: 8, border: '1px solid var(--color-border)' }}>
                <input type="text" placeholder="Name" value={estateForm.name} onChange={e => setEstateForm(p => ({ ...p, name: e.target.value }))} style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.875rem', marginBottom: 8 }} />
                <input type="text" placeholder="Region" value={estateForm.region} onChange={e => setEstateForm(p => ({ ...p, region: e.target.value }))} style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.875rem', marginBottom: 8 }} />
                <div style={{ display: 'flex', gap: 6 }}>
                  <button onClick={() => { setEditingEstate(null); setEstateForm({ name: '', region: '' }); }} style={{ flex: 1, padding: '6px 8px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>Cancel</button>
                  <button onClick={handleSaveEstate} disabled={saving} style={{ flex: 1, padding: '6px 8px', borderRadius: 6, border: 'none', background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600, opacity: saving ? 0.7 : 1 }}>{saving ? '...' : 'Save'}</button>
                </div>
              </div>
            )}
            {loading ? <div style={{ padding: 'var(--space-4)', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>Loading…</div> : (
              estates.map(e => (
                <div key={e.id} style={{ padding: 'var(--space-3)', borderRadius: 6, border: selectedEstate?.id === e.id ? '2px solid var(--color-primary)' : '1px solid var(--color-border)', background: selectedEstate?.id === e.id ? 'var(--color-surface-2)' : 'transparent', cursor: 'pointer' }}>
                  <div onClick={() => setSelectedEstate(e)} style={{ fontWeight: 600, marginBottom: 4, color: 'var(--color-text)' }}>{e.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 6 }}>{e.region} • {e.block_count || 0} blocks</div>
                  {(canWrite || isManager) && (
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button onClick={() => { setEditingEstate(e); setEstateForm({ name: e.name, region: e.region }); }} style={{ flex: 1, padding: '4px 8px', borderRadius: 4, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text)', cursor: 'pointer', fontSize: '0.7rem', fontWeight: 600 }}>Edit</button>
                      <button onClick={() => handleDeleteEstate(e.id)} style={{ flex: 1, padding: '4px 8px', borderRadius: 4, border: '1px solid rgba(220,38,38,0.3)', background: 'transparent', color: 'var(--color-danger)', cursor: 'pointer', fontSize: '0.7rem', fontWeight: 600 }}>Del</button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Blocks Panel */}
        <div>
          {selectedEstate && (
            <>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 'var(--space-5)' }}>
                <div><div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>SELECTED</div><div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text)' }}>{selectedEstate.name}</div></div>
                {(canWrite || isManager) && (
                  <button onClick={() => { setEditingBlock('new'); setBlockForm({ block_code: '', soil_type: '', growth_stage: '', area_hectares: '', state: 'active' }); }} style={{ marginLeft: 'auto', padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8125rem' }}>+ New Block</button>
                )}
              </div>

              {editingBlock && (
                <div className="section-card" style={{ marginBottom: 'var(--space-5)' }}>
                  <div className="section-card-header"><div className="section-card-title">{editingBlock === 'new' ? 'Create Block' : 'Edit Block'}</div></div>
                  <div className="section-card-body">
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 'var(--space-4)' }}>
                      <input type="text" placeholder="Block Code" value={blockForm.block_code} onChange={e => setBlockForm(p => ({ ...p, block_code: e.target.value }))} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.875rem' }} />
                      <input type="text" placeholder="Soil Type" value={blockForm.soil_type} onChange={e => setBlockForm(p => ({ ...p, soil_type: e.target.value }))} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.875rem' }} />
                      <input type="text" placeholder="Growth Stage" value={blockForm.growth_stage} onChange={e => setBlockForm(p => ({ ...p, growth_stage: e.target.value }))} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.875rem' }} />
                      <input type="number" step="0.01" placeholder="Area (hectares)" value={blockForm.area_hectares} onChange={e => setBlockForm(p => ({ ...p, area_hectares: e.target.value }))} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.875rem' }} />
                      <select value={blockForm.state} onChange={e => setBlockForm(p => ({ ...p, state: e.target.value }))} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: '0.875rem', gridColumn: '1 / -1' }}>
                        {stateOptions.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                      </select>
                    </div>
                    <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                      <button onClick={() => { setEditingBlock(null); setBlockForm({ block_code: '', soil_type: '', growth_stage: '', area_hectares: '', state: 'active' }); }} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600 }}>Cancel</button>
                      <button onClick={handleSaveBlock} disabled={saving} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontWeight: 600, opacity: saving ? 0.7 : 1 }}>{saving ? 'Saving…' : 'Save'}</button>
                    </div>
                  </div>
                </div>
              )}

              <div className="table-wrap">
                <div className="table-header-bar"><div><div className="table-title">Blocks</div><div className="table-subtitle">{blocks.length} blocks</div></div></div>
                {blocks.length === 0 ? <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)' }}>No blocks. Create one to get started!</div> : (
                  <table>
                    <thead><tr><th>Code</th><th>Soil</th><th>Stage</th><th>Area (ha)</th><th>State</th>{(canWrite || isManager) && <th>Actions</th>}</tr></thead>
                    <tbody>{blocks.map(b => (
                      <tr key={b.id}><td style={{ fontWeight: 600 }}>{b.block_code}</td><td>{b.soil_type || '—'}</td><td>{b.growth_stage || '—'}</td><td>{b.area_hectares || '—'}</td><td><span className={`badge badge-${b.state === 'active' ? 'success' : b.state === 'harvesting' ? 'warning' : 'neutral'}`}>{b.state.charAt(0).toUpperCase() + b.state.slice(1)}</span></td>
                      {(canWrite || isManager) && <td style={{ display: 'flex', gap: 6 }}><button onClick={() => { setEditingBlock(b); setBlockForm(b); }} style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>Edit</button><button onClick={() => handleDeleteBlock(b.id)} style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid rgba(220,38,38,0.3)', background: 'transparent', color: 'var(--color-danger)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>Delete</button></td>}
                      </tr>
                    ))}</tbody>
                  </table>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}


/* ── Tab: Fertilizer Schedule Management ─────────────────────────────── */
function FertilizerScheduleMgmtTab() {
  const { token, canWrite } = useAuth();
  const [estates, setEstates]             = useState([]);
  const [estateId, setEstateId]           = useState('');
  const [schedules, setSchedules]         = useState([]);
  const [loading, setLoading]             = useState(false);
  const [generating, setGenerating]       = useState(false);
  const [deleting, setDeleting]           = useState(null); // scheduleId being deleted
  const [confirmDelete, setConfirmDelete] = useState(null); // schedule obj
  const [error, setError]                 = useState('');
  const [genResult, setGenResult]         = useState(null);

  const nextMonthStr = (() => {
    const d = new Date();
    const y = d.getMonth() === 11 ? d.getFullYear() + 1 : d.getFullYear();
    const m = d.getMonth() === 11 ? 1 : d.getMonth() + 2;
    return `${y}-${String(m).padStart(2, '0')}-01`;
  })();

  const fmtMonth = iso => {
    if (!iso) return '';
    const [y, mo] = iso.split('-');
    return new Date(y, mo - 1, 1).toLocaleString('default', { month: 'long', year: 'numeric' });
  };

  useEffect(() => {
    if (!token) return;
    apiService.getEstates(token).then(data => {
      setEstates(data);
      if (data.length > 0) setEstateId(data[0].id);
    }).catch(() => {});
  }, [token]);

  const loadSchedules = () => {
    setLoading(true);
    apiService.getFertilizerSchedules(token, estateId)
      .then(data => setSchedules(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!token || !estateId) return;
    loadSchedules();
  }, [token, estateId]);

  const handleGenerate = async () => {
    if (!estateId) return;
    setGenerating(true); setError(''); setGenResult(null);
    try {
      const result = await apiService.generateFertilizerScheduleForMonth(token, {
        estate_id: estateId,
        period_start: nextMonthStr,
      });
      setGenResult(result);
      loadSchedules();
    } catch (e) {
      if (e.message && e.message.includes('already exists')) {
        setError(`A schedule for ${fmtMonth(nextMonthStr)} already exists. Delete it first to regenerate.`);
      } else {
        setError(e.message);
      }
    } finally { setGenerating(false); }
  };

  const handleDelete = async (sched) => {
    setDeleting(sched.id);
    setError('');
    try {
      await apiService.deleteFertilizerSchedule(token, sched.id);
      setConfirmDelete(null);
      loadSchedules();
    } catch (e) { setError(e.message); }
    finally { setDeleting(null); }
  };

  const statusBadge  = { active: 'badge-success', closed: 'badge-neutral' };
  const statusLabel  = { active: 'Active',        closed: 'Inactive' };

  return (
    <>
      {/* Controls */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Estate</div>
          <select value={estateId} onChange={e => { setEstateId(e.target.value); setGenResult(null); setError(''); }}
            style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.875rem', fontWeight: 600, cursor: 'pointer' }}>
            {estates.length === 0 && <option value="">Loading…</option>}
            {estates.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
        </div>
        {canWrite && (
          <button onClick={handleGenerate} disabled={generating || !estateId}
            style={{ marginLeft: 'auto', padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', background: generating ? '#6b7280' : 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8125rem', opacity: !estateId ? 0.5 : 1 }}>
            {generating ? 'Generating…' : `⚡ Generate ${fmtMonth(nextMonthStr)}`}
          </button>
        )}
      </div>

      {error && (
        <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(220,38,38,0.08)', color: 'var(--color-danger)', marginBottom: 20, fontSize: '0.875rem', border: '1px solid rgba(220,38,38,0.2)' }}>
          {error}
        </div>
      )}

      {genResult && (
        <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(22,163,74,0.08)', color: 'var(--color-success)', marginBottom: 20, fontSize: '0.875rem', border: '1px solid rgba(22,163,74,0.2)' }}>
          Schedule generated for <strong>{fmtMonth(genResult.period_start)}</strong>: {genResult.inserted} entries created
        </div>
      )}

      <div className="table-wrap">
        <div className="table-header-bar">
          <div>
            <div className="table-title">Schedule Runs</div>
            <div className="table-subtitle">{schedules.length} schedule{schedules.length !== 1 ? 's' : ''}</div>
          </div>
        </div>
        {loading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading…</div>
        ) : schedules.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)' }}>
            No schedules yet.{canWrite && ` Click "Generate ${fmtMonth(nextMonthStr)}" to create the first one.`}
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Month</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Entries</th>
                <th style={{ textAlign: 'right' }}>Overdue</th>
                <th style={{ textAlign: 'right' }}>Due</th>
                <th style={{ textAlign: 'right' }}>Done</th>
                <th>Generated By</th>
                <th>Generated At</th>
                {canWrite && <th></th>}
              </tr>
            </thead>
            <tbody>
              {schedules.map(s => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 600 }}>{fmtMonth(s.period_start)}</td>
                  <td><span className={`badge ${statusBadge[s.status] || 'badge-neutral'}`}>{statusLabel[s.status] || s.status}</span></td>
                  <td style={{ textAlign: 'right', fontSize: '0.8125rem' }}>{s.entry_count ?? 0}</td>
                  <td style={{ textAlign: 'right', fontSize: '0.8125rem', color: s.overdue_count > 0 ? 'var(--color-danger)' : 'inherit', fontWeight: s.overdue_count > 0 ? 700 : 400 }}>{s.overdue_count ?? 0}</td>
                  <td style={{ textAlign: 'right', fontSize: '0.8125rem', color: s.due_count > 0 ? 'var(--color-warning)' : 'inherit' }}>{s.due_count ?? 0}</td>
                  <td style={{ textAlign: 'right', fontSize: '0.8125rem', color: 'var(--color-success)' }}>{s.done_count ?? 0}</td>
                  <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>{s.generated_by_name || '—'}</td>
                  <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>{s.generated_at ? s.generated_at.slice(0, 16).replace('T', ' ') : '—'}</td>
                  {canWrite && (
                    <td>
                      <button onClick={() => setConfirmDelete(s)}
                        style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid rgba(220,38,38,0.3)', background: 'rgba(220,38,38,0.07)', color: 'var(--color-danger)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>
                        Delete
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--color-surface)', borderRadius: 16, padding: 32, width: '100%', maxWidth: 420, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 12 }}>Delete Schedule?</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: 24 }}>
              This will permanently delete the <strong>{fmtMonth(confirmDelete.period_start)}</strong> schedule and all {confirmDelete.entry_count ?? 0} entries. This cannot be undone.
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setConfirmDelete(null)} disabled={!!deleting}
                style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={() => handleDelete(confirmDelete)} disabled={!!deleting}
                style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--color-danger)', color: '#fff', cursor: 'pointer', fontWeight: 600, opacity: deleting ? 0.7 : 1 }}>
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ── Tab: Fertilizer Programme ────────────────────────────────────────── */
function FertilizerProgrammeTab() {
  const { token, canWrite } = useAuth();

  const [estates, setEstates]   = useState([]);
  const [estateId, setEstateId] = useState('');
  const [fertTypes, setFertTypes] = useState([]);
  const [steps, setSteps]       = useState([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');
  const [modal, setModal]       = useState(null); // null | 'add' | { step obj }
  const [form, setForm]         = useState({});
  const [saving, setSaving]     = useState(false);
  const [formError, setFormError] = useState('');
  const [deleting, setDeleting] = useState(null); // id being deleted
  const [conflictStep, setConflictStep] = useState(null); // existing step that would conflict

  const ZONES   = ['Low', 'Mid', 'High'];
  const STAGES  = ['Mature', 'Young', 'Immature'];

  useEffect(() => {
    if (!token) return;
    Promise.all([apiService.getEstates(token), apiService.getFertilizerTypes(token)])
      .then(([est, types]) => {
        setEstates(est);
        setFertTypes(Array.isArray(types) ? types : []);
        if (est.length > 0) setEstateId(est[0].id);
      }).catch(() => {});
  }, [token]);

  const load = (eid = estateId) => {
    if (!token || !eid) return;
    setLoading(true); setError('');
    apiService.getFertilizerProgramme(token, eid)
      .then(data => setSteps(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [token, estateId]);

  const openAdd = () => {
    setForm({ fertilizer_type_id: fertTypes[0]?.id || '', application_no: 1, interval_weeks: 8, rate_kg_per_ha: '', zone_override: '', growth_stage_filter: '', notes: '' });
    setFormError(''); setModal('add');
  };

  const openEdit = (s) => {
    setForm({ interval_weeks: s.interval_weeks, rate_kg_per_ha: s.rate_kg_per_ha, zone_override: s.zone_override || '', growth_stage_filter: s.growth_stage_filter || '', notes: s.notes || '' });
    setFormError(''); setModal(s);
  };

  const buildPayload = () => ({
    interval_weeks: Number(form.interval_weeks),
    rate_kg_per_ha: Number(form.rate_kg_per_ha),
    zone_override: form.zone_override || null,
    growth_stage_filter: form.growth_stage_filter || null,
    notes: form.notes.trim() || null,
  });

  const handleSave = async () => {
    if (!form.rate_kg_per_ha || Number(form.rate_kg_per_ha) <= 0) { setFormError('Rate must be greater than 0'); return; }
    if (!form.interval_weeks || Number(form.interval_weeks) <= 0) { setFormError('Interval must be greater than 0'); return; }

    // Conflict check — only on add
    if (modal === 'add') {
      const incomingZone  = form.zone_override || null;
      const incomingStage = form.growth_stage_filter || null;
      const conflict = steps.find(s =>
        s.fertilizer_type_id === form.fertilizer_type_id &&
        Number(s.application_no) === Number(form.application_no) &&
        (s.zone_override || null) === incomingZone &&
        (s.growth_stage_filter || null) === incomingStage
      );
      if (conflict) { setConflictStep(conflict); return; }
    }

    await _doSave();
  };

  const _doSave = async () => {
    setSaving(true); setFormError('');
    try {
      if (modal === 'add') {
        await apiService.createFertilizerProgrammeStep(token, { estate_id: estateId, fertilizer_type_id: form.fertilizer_type_id, application_no: Number(form.application_no), ...buildPayload() });
      } else {
        await apiService.updateFertilizerProgrammeStep(token, modal.id, buildPayload());
      }
      setModal(null); setConflictStep(null); load();
    } catch (e) { setFormError(e.message); }
    finally { setSaving(false); }
  };

  const handleReplaceConfirmed = async () => {
    setSaving(true); setFormError('');
    try {
      await apiService.deleteFertilizerProgrammeStep(token, conflictStep.id);
      await apiService.createFertilizerProgrammeStep(token, { estate_id: estateId, fertilizer_type_id: form.fertilizer_type_id, application_no: Number(form.application_no), ...buildPayload() });
      setModal(null); setConflictStep(null); load();
    } catch (e) { setFormError(e.message); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    setDeleting(id);
    try { await apiService.deleteFertilizerProgrammeStep(token, id); load(); }
    catch (e) { setError(e.message); }
    finally { setDeleting(null); }
  };

  // Group steps by fertilizer code for visual clarity
  const grouped = steps.reduce((acc, s) => {
    const key = s.fertilizer_code;
    if (!acc[key]) acc[key] = [];
    acc[key].push(s);
    return acc;
  }, {});

  const inputStyle = { width: '100%', padding: '8px 12px', borderRadius: 8, boxSizing: 'border-box', border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.875rem' };
  const labelStyle = { display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 };

  return (
    <>
      {/* Controls */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Estate</div>
          <select value={estateId} onChange={e => setEstateId(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.875rem', fontWeight: 600, cursor: 'pointer' }}>
            {estates.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
        </div>
        {canWrite && (
          <div style={{ marginLeft: 'auto' }}>
            <button onClick={openAdd} disabled={!estateId || fertTypes.length === 0}
              style={{ padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8125rem' }}>
              + Add Step
            </button>
          </div>
        )}
      </div>

      {error && (
        <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(220,38,38,0.08)', color: 'var(--color-danger)', marginBottom: 20, fontSize: '0.875rem', border: '1px solid rgba(220,38,38,0.2)' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading…</div>
      ) : steps.length === 0 ? (
        <div style={{ padding: 48, textAlign: 'center', background: 'var(--color-surface-2)', borderRadius: 14, border: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 10 }}>📋</div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>No programme steps for this estate</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            {canWrite ? 'Add steps to define the fertilizer rotation schedule.' : 'No programme has been configured yet.'}
          </div>
        </div>
      ) : (
        Object.entries(grouped).map(([fertCode, groupSteps]) => (
          <div key={fertCode} className="table-wrap" style={{ marginBottom: 'var(--space-5)' }}>
            <div className="table-header-bar">
              <div>
                <div className="table-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.9rem', color: 'var(--color-primary)' }}>{fertCode}</span>
                  <span style={{ fontWeight: 400, color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>{groupSteps[0].fertilizer_name}</span>
                </div>
                <div className="table-subtitle">
                  {groupSteps[0].npk_n != null ? `N ${groupSteps[0].npk_n}% · P ${groupSteps[0].npk_p}% · K ${groupSteps[0].npk_k}%` : ''}
                  {' · '}{groupSteps.length} application{groupSteps.length !== 1 ? 's' : ''} per year
                </div>
              </div>
            </div>
            <table>
              <thead>
                <tr>
                  <th>App #</th>
                  <th>Interval (weeks)</th>
                  <th style={{ textAlign: 'right' }}>Rate (kg/ha)</th>
                  <th>Zone</th>
                  <th>Growth Stage</th>
                  <th>Notes</th>
                  {canWrite && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {groupSteps.map(s => (
                  <tr key={s.id}>
                    <td style={{ fontWeight: 700, color: 'var(--color-primary)' }}>#{s.application_no}</td>
                    <td>{s.interval_weeks} wks</td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>{s.rate_kg_per_ha}</td>
                    <td>{s.zone_override ? <span className="badge badge-neutral">{s.zone_override}</span> : <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8125rem' }}>All zones</span>}</td>
                    <td>{s.growth_stage_filter ? <span className="badge badge-neutral">{s.growth_stage_filter}</span> : <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8125rem' }}>All stages</span>}</td>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', maxWidth: 200 }}>{s.notes || '—'}</td>
                    {canWrite && (
                      <td>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button onClick={() => openEdit(s)}
                            style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>
                            Edit
                          </button>
                          <button onClick={() => handleDelete(s.id)} disabled={deleting === s.id}
                            style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid rgba(220,38,38,0.3)', background: 'transparent', color: 'var(--color-danger)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600, opacity: deleting === s.id ? 0.5 : 1 }}>
                            {deleting === s.id ? '…' : 'Remove'}
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}

      {/* Conflict confirmation modal */}
      {conflictStep && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100 }}>
          <div style={{ background: 'var(--color-surface)', borderRadius: 16, padding: 32, width: '100%', maxWidth: 440, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: 8 }}>Step already exists</div>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
              A step for <strong>{conflictStep.fertilizer_code}</strong> application&nbsp;#{conflictStep.application_no}
              {conflictStep.zone_override ? `, zone ${conflictStep.zone_override}` : ''}
              {conflictStep.growth_stage_filter ? `, ${conflictStep.growth_stage_filter} blocks` : ''} already exists with:
            </p>
            <div style={{ background: 'var(--color-surface-2)', borderRadius: 10, padding: '12px 16px', marginBottom: 20, fontSize: '0.875rem', display: 'flex', gap: 24 }}>
              <div><div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 2 }}>Interval</div><strong>{conflictStep.interval_weeks} weeks</strong></div>
              <div><div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 2 }}>Rate</div><strong>{conflictStep.rate_kg_per_ha} kg/ha</strong></div>
              {conflictStep.notes && <div><div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 2 }}>Notes</div><span>{conflictStep.notes}</span></div>}
            </div>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: 20 }}>
              Do you want to <strong>replace it</strong> with the new values, or go back and adjust?
            </p>
            {formError && <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(220,38,38,0.1)', color: 'var(--color-danger)', marginBottom: 12, fontSize: '0.875rem' }}>{formError}</div>}
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setConflictStep(null)} disabled={saving}
                style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600 }}>
                Go Back
              </button>
              <button onClick={handleReplaceConfirmed} disabled={saving}
                style={{ padding: '8px 18px', borderRadius: 8, border: 'none', background: 'var(--color-danger)', color: '#fff', cursor: 'pointer', fontWeight: 600, opacity: saving ? 0.7 : 1 }}>
                {saving ? 'Replacing…' : 'Replace'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add / Edit Modal */}
      {modal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--color-surface)', borderRadius: 16, padding: 32, width: '100%', maxWidth: 480, boxShadow: '0 20px 60px rgba(0,0,0,0.3)', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 4 }}>
              {modal === 'add' ? 'Add Programme Step' : `Edit Step — ${modal.fertilizer_code} #${modal.application_no}`}
            </div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginBottom: 20 }}>
              {modal === 'add' ? estates.find(e => e.id === estateId)?.name : modal.estate_name}
            </div>

            {formError && (
              <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(220,38,38,0.1)', color: 'var(--color-danger)', marginBottom: 16, fontSize: '0.875rem' }}>
                {formError}
              </div>
            )}

            {/* Fertilizer + App No — add mode only */}
            {modal === 'add' && (
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12, marginBottom: 14 }}>
                <div>
                  <label style={labelStyle}>Fertilizer Product <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                  <select value={form.fertilizer_type_id} onChange={e => setForm(p => ({ ...p, fertilizer_type_id: e.target.value }))} style={inputStyle}>
                    {fertTypes.map(t => <option key={t.id} value={t.id}>{t.code} — {t.name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Application # <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                  <input type="number" min="1" value={form.application_no} onChange={e => setForm(p => ({ ...p, application_no: e.target.value }))} style={inputStyle} />
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
              <div>
                <label style={labelStyle}>Interval (weeks) <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                <input type="number" min="1" value={form.interval_weeks} onChange={e => setForm(p => ({ ...p, interval_weeks: e.target.value }))} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Rate (kg/ha) <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                <input type="number" min="0" step="0.1" value={form.rate_kg_per_ha} onChange={e => setForm(p => ({ ...p, rate_kg_per_ha: e.target.value }))} style={inputStyle} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
              <div>
                <label style={labelStyle}>Zone</label>
                <select value={form.zone_override} onChange={e => setForm(p => ({ ...p, zone_override: e.target.value }))} style={inputStyle}>
                  <option value="">All zones</option>
                  {ZONES.map(z => <option key={z} value={z}>{z}</option>)}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Growth Stage</label>
                <select value={form.growth_stage_filter} onChange={e => setForm(p => ({ ...p, growth_stage_filter: e.target.value }))} style={inputStyle}>
                  <option value="">All stages</option>
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={labelStyle}>Notes</label>
              <textarea value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} rows={2} placeholder="Optional — e.g. based on soil test 2026-04" style={{ ...inputStyle, resize: 'vertical' }} />
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setModal(null)} disabled={saving}
                style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={handleSave} disabled={saving}
                style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontWeight: 600, opacity: saving ? 0.7 : 1 }}>
                {saving ? 'Saving…' : modal === 'add' ? 'Add Step' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ── Tab: Fertilizer Management ───────────────────────────────────────── */
function FertilizerMgmtTab() {
  const { token, canWrite } = useAuth();
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(null); // null | 'add' | { edit obj }
  const [form, setForm] = useState({ code: '', name: '', npk_n: '', npk_p: '', npk_k: '', default_dosage_kg: '', description: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');

  const load = () => {
    setLoading(true);
    apiService.getFertilizerTypes(token)
      .then(data => setTypes(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (token) load(); }, [token]);

  const openAdd = () => {
    setForm({ code: '', name: '', npk_n: '', npk_p: '', npk_k: '', default_dosage_kg: '', description: '' });
    setFormError('');
    setModal('add');
  };

  const openEdit = (t) => {
    setForm({
      code: t.code,
      name: t.name,
      npk_n: t.npk_n ?? '',
      npk_p: t.npk_p ?? '',
      npk_k: t.npk_k ?? '',
      default_dosage_kg: t.default_dosage_kg ?? '',
      description: t.description ?? '',
    });
    setFormError('');
    setModal(t);
  };

  const handleSave = async () => {
    if (!form.name.trim()) { setFormError('Name is required'); return; }
    if (modal === 'add' && !form.code.trim()) { setFormError('Code is required'); return; }
    setSaving(true); setFormError('');
    const payload = {
      name: form.name.trim(),
      npk_n: form.npk_n !== '' ? Number(form.npk_n) : null,
      npk_p: form.npk_p !== '' ? Number(form.npk_p) : null,
      npk_k: form.npk_k !== '' ? Number(form.npk_k) : null,
      default_dosage_kg: form.default_dosage_kg !== '' ? Number(form.default_dosage_kg) : null,
      description: form.description.trim() || null,
    };
    try {
      if (modal === 'add') {
        await apiService.createFertilizerType(token, { code: form.code.trim(), ...payload });
      } else {
        await apiService.updateFertilizerType(token, modal.id, payload);
      }
      setModal(null);
      load();
    } catch (e) { setFormError(e.message); }
    finally { setSaving(false); }
  };

  const inputStyle = { width: '100%', padding: '8px 12px', borderRadius: 8, boxSizing: 'border-box', border: '1px solid var(--color-border)', background: 'var(--color-surface-2)', color: 'var(--color-text)', fontSize: '0.875rem' };
  const labelStyle = { display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 };

  return (
    <>
      {error && (
        <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(220,38,38,0.08)', color: 'var(--color-danger)', marginBottom: 20, fontSize: '0.875rem', border: '1px solid rgba(220,38,38,0.2)' }}>
          {error}
        </div>
      )}

      <div className="table-wrap">
        <div className="table-header-bar">
          <div>
            <div className="table-title">Fertilizer Products</div>
            <div className="table-subtitle">{types.length} products in catalogue</div>
          </div>
          {canWrite && (
            <button onClick={openAdd} style={{ padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8125rem' }}>
              + Add Fertilizer
            </button>
          )}
        </div>

        {loading ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading…</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th style={{ textAlign: 'right' }}>N %</th>
                <th style={{ textAlign: 'right' }}>P %</th>
                <th style={{ textAlign: 'right' }}>K %</th>
                <th style={{ textAlign: 'right' }}>Default Dosage (kg/ha)</th>
                <th>Description</th>
                {canWrite && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {types.length === 0 ? (
                <tr><td colSpan={canWrite ? 8 : 7} style={{ textAlign: 'center', padding: 32, color: 'var(--color-text-muted)' }}>No fertilizer products found.</td></tr>
              ) : types.map(t => (
                <tr key={t.id}>
                  <td><span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.8125rem', color: 'var(--color-primary)' }}>{t.code}</span></td>
                  <td style={{ fontWeight: 600 }}>{t.name}</td>
                  <td style={{ textAlign: 'right', fontWeight: 600 }}>{t.npk_n != null ? `${t.npk_n}%` : '—'}</td>
                  <td style={{ textAlign: 'right', fontWeight: 600 }}>{t.npk_p != null ? `${t.npk_p}%` : '—'}</td>
                  <td style={{ textAlign: 'right', fontWeight: 600 }}>{t.npk_k != null ? `${t.npk_k}%` : '—'}</td>
                  <td style={{ textAlign: 'right', color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>{t.default_dosage_kg != null ? `${t.default_dosage_kg} kg` : '—'}</td>
                  <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', maxWidth: 240 }}>{t.description || '—'}</td>
                  {canWrite && (
                    <td>
                      <button onClick={() => openEdit(t)} style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>
                        Edit
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Add / Edit Modal ── */}
      {modal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--color-surface)', borderRadius: 16, padding: 32, width: '100%', maxWidth: 520, boxShadow: '0 20px 60px rgba(0,0,0,0.3)', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 20 }}>
              {modal === 'add' ? 'Add Fertilizer Product' : `Edit — ${modal.code}`}
            </div>

            {formError && (
              <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(220,38,38,0.1)', color: 'var(--color-danger)', marginBottom: 16, fontSize: '0.875rem' }}>
                {formError}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 12, marginBottom: 14 }}>
              <div>
                <label style={labelStyle}>Code {modal === 'add' && <span style={{ color: 'var(--color-danger)' }}>*</span>}</label>
                <input
                  type="text"
                  value={form.code}
                  readOnly={modal !== 'add'}
                  onChange={e => setForm(p => ({ ...p, code: e.target.value }))}
                  placeholder="e.g. T0_200"
                  style={{ ...inputStyle, cursor: modal !== 'add' ? 'not-allowed' : 'text', color: modal !== 'add' ? 'var(--color-text-muted)' : 'var(--color-text)', fontFamily: 'monospace' }}
                />
              </div>
              <div>
                <label style={labelStyle}>Name <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                <input type="text" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="e.g. Urea 200" style={inputStyle} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 14 }}>
              {[['npk_n', 'Nitrogen (N %)'], ['npk_p', 'Phosphorus (P %)'], ['npk_k', 'Potassium (K %)']].map(([field, label]) => (
                <div key={field}>
                  <label style={labelStyle}>{label}</label>
                  <input type="number" min="0" max="100" step="0.01" value={form[field]} onChange={e => setForm(p => ({ ...p, [field]: e.target.value }))} placeholder="0.00" style={inputStyle} />
                </div>
              ))}
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Default Dosage (kg/ha)</label>
              <input type="number" min="0" step="0.001" value={form.default_dosage_kg} onChange={e => setForm(p => ({ ...p, default_dosage_kg: e.target.value }))} placeholder="Optional" style={inputStyle} />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={labelStyle}>Description</label>
              <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} rows={2} placeholder="Optional" style={{ ...inputStyle, resize: 'vertical' }} />
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setModal(null)} disabled={saving} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={handleSave} disabled={saving} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontWeight: 600, opacity: saving ? 0.7 : 1 }}>
                {saving ? 'Saving…' : modal === 'add' ? 'Add Product' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ── Tab: User Management (admin only) ───────────────────────────────── */
function UserManagementTab() {
  const { token } = useAuth();
  const [users, setUsers]       = useState([]);
  const [estates, setEstates]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');

  // Scheduler status
  const [schedStatus, setSchedStatus]     = useState(null);
  const [schedLoading, setSchedLoading]   = useState(false);
  const [schedError, setSchedError]       = useState('');

  // Modal state
  const [modal, setModal]       = useState(false);
  const [form, setForm]         = useState({ full_name: '', email: '', password: '', role: 'manager', estate_id: '' });
  const [saving, setSaving]     = useState(false);
  const [formError, setFormError] = useState('');

  const ROLE_LABELS = { admin: 'Admin', estate_manager: 'Estate Manager', manager: 'Manager' };

  const load = async () => {
    setLoading(true); setError('');
    try {
      const [usersData, estatesData] = await Promise.all([
        apiService.getSystemUsers(token),
        apiService.getPublicEstates(token),
      ]);
      setUsers(usersData.users || []);
      setEstates(estatesData);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadSchedStatus = async () => {
    setSchedLoading(true); setSchedError('');
    try {
      const data = await apiService.getSchedulerStatus(token);
      setSchedStatus(data);
    } catch (e) {
      setSchedError(e.message);
    } finally {
      setSchedLoading(false);
    }
  };

  useEffect(() => { if (token) { load(); loadSchedStatus(); } }, [token]);

  const openModal = () => {
    setForm({ full_name: '', email: '', password: '', role: 'manager', estate_id: '' });
    setFormError('');
    setModal(true);
  };

  const handleSave = async () => {
    if (!form.full_name || !form.email || !form.password) {
      setFormError('Full name, email and password are required.');
      return;
    }
    if (form.role === 'manager' && !form.estate_id) {
      setFormError('Please select an estate for the Manager role.');
      return;
    }
    setSaving(true); setFormError('');
    try {
      await apiService.createSystemUser(token, {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        role: form.role,
        estate_id: form.role === 'manager' ? form.estate_id : null,
      });
      setModal(false);
      await load();
    } catch (e) {
      setFormError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const roleBadgeClass = (role) => {
    if (role === 'admin') return 'badge-danger';
    if (role === 'estate_manager') return 'badge-warning';
    return 'badge-neutral';
  };

  return (
    <div>
      {error && (
        <div className="alert alert-warning" style={{ marginBottom: 'var(--space-5)' }}>
          <span>⚠️</span><span>{error}</span>
        </div>
      )}

      <div className="table-wrap">
        <div className="table-header-bar">
          <div>
            <div className="table-title">System Accounts</div>
            <div className="table-subtitle">{users.length} users with system access</div>
          </div>
          <button
            onClick={openModal}
            style={{
              padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: '0.8125rem',
            }}
          >
            + Add User
          </button>
        </div>

        {loading ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading users…</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Estate</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 32 }}>No users found.</td></tr>
              ) : users.map(u => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 600 }}>{u.full_name}</td>
                  <td style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>{u.email}</td>
                  <td>
                    <span className={`badge ${roleBadgeClass(u.role)}`}>{ROLE_LABELS[u.role] || u.role}</span>
                  </td>
                  <td style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>{u.estate_name || '—'}</td>
                  <td style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Scheduler Status Card ── */}
      <div style={{ marginTop: 'var(--space-6)' }}>
        <div className="table-wrap" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <div className="table-title">Monthly Labour Scheduler</div>
              <div className="table-subtitle">Runs automatically on the 1st of each month at 09:50 (Asia/Colombo)</div>
            </div>
            <button
              onClick={loadSchedStatus}
              disabled={schedLoading}
              style={{
                padding: '6px 14px', borderRadius: 8, border: '1px solid var(--color-border)',
                background: 'var(--color-surface-2)', color: 'var(--color-text)', cursor: 'pointer',
                fontSize: '0.8125rem', fontWeight: 600, opacity: schedLoading ? 0.6 : 1,
              }}
            >
              {schedLoading ? 'Refreshing…' : '↻ Refresh'}
            </button>
          </div>

          {schedError && (
            <div className="alert alert-warning" style={{ marginBottom: 12 }}>
              <span>⚠️</span><span>{schedError}</span>
            </div>
          )}

          {schedStatus ? (() => {
            const job     = schedStatus.jobs?.[0];
            const lastRun = schedStatus.last_run || {};
            const statusColor = {
              ok:      'var(--color-success)',
              skipped: 'var(--color-warning)',
              error:   'var(--color-danger)',
            };
            const statusIcon = { ok: '✅', skipped: '⏭️', error: '❌' };

            const fmtLocal = (iso) => {
              if (!iso) return '—';
              try { return new Date(iso).toLocaleString(); } catch { return iso; }
            };

            return (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                {/* Running state */}
                <div style={{
                  background: 'var(--color-surface-2)', borderRadius: 10,
                  border: '1px solid var(--color-border)', padding: '16px 20px',
                }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      width: 10, height: 10, borderRadius: '50%',
                      background: schedStatus.running ? 'var(--color-success)' : 'var(--color-danger)',
                      display: 'inline-block', flexShrink: 0,
                    }} />
                    <span style={{ fontWeight: 700, fontSize: '1rem' }}>
                      {schedStatus.running ? 'Running' : 'Stopped'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                    Timezone: {schedStatus.timezone}
                  </div>
                </div>

                {/* Next fire */}
                <div style={{
                  background: 'var(--color-surface-2)', borderRadius: 10,
                  border: '1px solid var(--color-border)', padding: '16px 20px',
                }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Next Run</div>
                  <div style={{ fontWeight: 700, fontSize: '0.9375rem', lineHeight: 1.3 }}>
                    {job ? fmtLocal(job.next_run_local) : '—'}
                  </div>
                  {job && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                      {job.trigger}
                    </div>
                  )}
                </div>

                {/* Last run */}
                <div style={{
                  background: 'var(--color-surface-2)', borderRadius: 10,
                  border: '1px solid var(--color-border)', padding: '16px 20px',
                }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Last Run</div>
                  {lastRun.fired_at ? (
                    <>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span>{statusIcon[lastRun.status] || '❓'}</span>
                        <span style={{ fontWeight: 700, color: statusColor[lastRun.status] || 'inherit' }}>
                          {lastRun.status?.toUpperCase() || 'Unknown'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                        {fmtLocal(lastRun.fired_at)}
                      </div>
                      {lastRun.detail && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4, fontStyle: 'italic' }}>
                          {lastRun.detail}
                        </div>
                      )}
                    </>
                  ) : (
                    <div style={{ fontWeight: 600, color: 'var(--color-text-muted)' }}>No runs recorded</div>
                  )}
                </div>
              </div>
            );
          })() : (
            !schedLoading && <div style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>No scheduler data available.</div>
          )}
        </div>
      </div>

      {/* ── Add User Modal ── */}
      {modal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div style={{
            background: 'var(--color-surface)', borderRadius: 16, padding: 32,
            width: '100%', maxWidth: 460, boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
            maxHeight: '90vh', overflowY: 'auto',
          }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 20 }}>Add System User</div>

            {formError && (
              <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(220,38,38,0.1)',
                            color: 'var(--color-danger)', marginBottom: 16, fontSize: '0.875rem' }}>
                {formError}
              </div>
            )}

            {[
              ['full_name', 'Full Name', 'text', 'Kamal Perera'],
              ['email',     'Email',     'email', 'user@plantation.com'],
              ['password',  'Temporary Password', 'password', ''],
            ].map(([field, label, type, placeholder]) => (
              <div key={field} style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600,
                                color: 'var(--color-text-muted)', marginBottom: 4 }}>{label}</label>
                <input
                  type={type}
                  value={form[field]}
                  onChange={e => setForm(p => ({ ...p, [field]: e.target.value }))}
                  placeholder={placeholder}
                  style={{
                    width: '100%', padding: '8px 12px', borderRadius: 8, boxSizing: 'border-box',
                    border: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
                    color: 'var(--color-text)', fontSize: '0.875rem',
                  }}
                />
              </div>
            ))}

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600,
                              color: 'var(--color-text-muted)', marginBottom: 4 }}>Role</label>
              <select
                value={form.role}
                onChange={e => setForm(p => ({ ...p, role: e.target.value, estate_id: '' }))}
                style={{
                  width: '100%', padding: '8px 12px', borderRadius: 8,
                  border: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
                  color: 'var(--color-text)', fontSize: '0.875rem',
                }}
              >
                <option value="admin">Admin — full access to all estates</option>
                <option value="estate_manager">Estate Manager — full access to all estates</option>
                <option value="manager">Manager — read-only, single estate</option>
              </select>
            </div>

            {form.role === 'manager' && (
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600,
                                color: 'var(--color-text-muted)', marginBottom: 4 }}>Estate</label>
                <select
                  value={form.estate_id}
                  onChange={e => setForm(p => ({ ...p, estate_id: e.target.value }))}
                  style={{
                    width: '100%', padding: '8px 12px', borderRadius: 8,
                    border: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
                    color: 'var(--color-text)', fontSize: '0.875rem',
                  }}
                >
                  <option value="">Select an estate…</option>
                  {estates.map(es => (
                    <option key={es.id} value={es.id}>{es.name}</option>
                  ))}
                </select>
              </div>
            )}

            <div style={{ fontSize: '0.775rem', color: 'var(--color-text-muted)', marginBottom: 20,
                          padding: '8px 12px', borderRadius: 6, background: 'var(--color-surface-2)',
                          border: '1px solid var(--color-border)' }}>
              Password must be at least 8 characters with uppercase, lowercase, number and special character. The user can change it after logging in.
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setModal(false)}
                style={{
                  padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)',
                  background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontWeight: 600,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  padding: '8px 20px', borderRadius: 8, border: 'none',
                  background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontWeight: 600,
                  opacity: saving ? 0.7 : 1,
                }}
              >
                {saving ? 'Creating…' : 'Create User'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const navItems = [
  { id: 'estate-blocks', icon: '🏗️', label: 'Estates & Blocks' },
  { id: 'roi',           icon: '📊', label: 'ROI Calculator' },
  { id: 'water',         icon: '💧', label: 'Water Efficiency' },
  { id: 'fertilizer',    icon: '🌱', label: 'Fertilizer Rotation' },
  { id: 'fert-schedules', icon: '📆', label: 'Fertilizer Schedules' },
  { id: 'fert-programme', icon: '📋', label: 'Fertilizer Programme' },
  { id: 'fert-mgmt',     icon: '🧪', label: 'Fertilizer Management' },
  { id: 'labour',        icon: '👥', label: 'Labour Planner' },
  { id: 'predictions',   icon: '🔮', label: 'Yield Predictions' },
  { id: 'reports',       icon: '📄', label: 'Reports' },
  { id: 'user-management', icon: '🔑', label: 'User Management', adminOnly: true },
];

const tabTitles = {
  overview:   { title: 'Overview',           sub: `Estate-wide summary for ${CURRENT_PERIOD_LABEL}` },
  'estate-blocks': { title: 'Estates & Blocks',  sub: 'Manage all estates and their plantation blocks' },
  roi:        { title: 'ROI Calculator',      sub: 'Cost-per-kg analysis across all estates' },
  water:      { title: 'Water Efficiency',    sub: 'Monthly factory water intensity tracking' },
  fertilizer:  { title: 'Fertilizer Rotation',    sub: 'Block-level application schedule & alerts' },
  'fert-schedules': { title: 'Fertilizer Schedules', sub: 'Manage monthly schedule runs — generate, review and delete per-estate schedules' },
  'fert-programme': { title: 'Fertilizer Programme', sub: 'Per-estate application schedules — adjust intervals & rates to match local soil conditions' },
  'fert-mgmt': { title: 'Fertilizer Management',  sub: 'Product catalogue — NPK profiles, dosage rates' },
  labour:     { title: 'Labour Planner',      sub: 'Monthly worker allocation & production targets' },
  predictions: { title: 'Yield Predictions',  sub: 'ML model forecasts for each block & month' },
  reports:    { title: 'Estate Reports',      sub: 'Generate detailed per-estate performance reports' },
  'user-management': { title: 'User Management', sub: 'Admin only — create and manage system accounts' },
};

// Convert round number to month name (round 1 = Jan, round 2 = Feb, etc.)
const roundToMonth = (roundNumber) => {
  const months = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December'];
  return months[roundNumber] || `Round ${roundNumber}`;
};

/* ── Main Dashboard ───────────────────────────────────────────────────── */
export default function DashboardPage() {
  const { user, isAuthenticated, loading, logout, token, isAdmin } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('estate-blocks');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [fertOverdueCount, setFertOverdueCount] = useState(0);

  const refreshFertOverdueCount = () => {
    if (!token) return;
    apiService.getFertilizerAlerts(token)
      .then(data => setFertOverdueCount(Array.isArray(data) ? data.filter(a => a.status === 'overdue').length : 0))
      .catch(() => {});
  };

  useEffect(() => { refreshFertOverdueCount(); }, [token]);

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
      <aside className={`dash-sidebar${sidebarCollapsed ? ' collapsed' : ''}`}>
        <div className="dash-sidebar-logo">
          <img src="/logo.png" alt="KVPL Logo" className="dash-sidebar-logo-mark" style={{ width: '40px', height: '40px', objectFit: 'contain' }} />
          <div className="dash-sidebar-brand">
            KVPL
            <small>Plantation System</small>
          </div>
        </div>

        <nav className="dash-nav">
          <div className="dash-nav-label">Main Menu</div>
          {navItems.filter(item => !item.adminOnly || isAdmin).map(item => (
            <button
              key={item.id}
              className={`dash-nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <span className="dash-nav-icon">{item.icon}</span>
              <span className="dash-nav-item-label">{item.label}</span>
              {item.id === 'fertilizer' && fertOverdueCount > 0 && (
                <span className="dash-nav-badge">{fertOverdueCount}</span>
              )}
            </button>
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
            <span className="tag" style={{ fontSize: '0.75rem' }}>{CURRENT_PERIOD_LABEL}</span>
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
            {activeTab === 'fertilizer' && fertOverdueCount > 0 && (
              <div className="alert alert-danger" style={{ marginTop: 'var(--space-3)', marginBottom: 0 }}>
                <span>🚨</span>
                <span><strong>{fertOverdueCount} block{fertOverdueCount !== 1 ? 's' : ''}</strong> overdue for fertilizer application. Delays reduce yield and soil health.</span>
              </div>
            )}
          </div>

          {activeTab === 'overview'    && <OverviewTab />}
          {activeTab === 'estate-blocks' && <EstateBlocksTab />}
          {activeTab === 'roi'         && <ROITab />}
          {activeTab === 'water'       && <WaterTab />}
          {activeTab === 'fertilizer'     && <FertilizerTab onOverdueChange={refreshFertOverdueCount} />}
          {activeTab === 'fert-schedules' && <FertilizerScheduleMgmtTab />}
          {activeTab === 'fert-programme' && <FertilizerProgrammeTab />}
          {activeTab === 'fert-mgmt'   && <FertilizerMgmtTab />}
          {activeTab === 'labour'      && <LabourTab />}
          {activeTab === 'predictions' && <YieldPredictionTab />}
          {activeTab === 'reports'     && <ReportTab />}
          {activeTab === 'user-management' && isAdmin && <UserManagementTab />}
        </main>
      </div>
    </div>
  );
}
