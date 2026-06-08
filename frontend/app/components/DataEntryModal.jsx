'use client';

import { useState, useEffect } from 'react';

export function DataEntryModal({ isOpen, onClose, estates, token, onSuccess, apiService }) {
  const [activeTab, setActiveTab] = useState('costs'); // 'costs' | 'yield'
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Form state for input costs
  const [costForm, setCostForm] = useState({
    estate_id: estates.length > 0 ? estates[0].id : '',
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    fertilizer_cost_lkr: '',
    chemical_cost_lkr: '',
    labour_input_cost_lkr: '',
    other_cost_lkr: '',
    source: 'manual',
  });

  // Form state for yield records
  const [yieldForm, setYieldForm] = useState({
    estate_id: estates.length > 0 ? estates[0].id : '',
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    yield_kg: '',
    source: 'manual',
  });

  const monthOptions = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
  ];

  // Calculate total cost for input costs
  const totalCost = (
    parseFloat(costForm.fertilizer_cost_lkr || 0) +
    parseFloat(costForm.chemical_cost_lkr || 0) +
    parseFloat(costForm.labour_input_cost_lkr || 0) +
    parseFloat(costForm.other_cost_lkr || 0)
  ).toFixed(2);

  const handleSaveInputCost = async () => {
    setError('');
    setSuccessMsg('');

    // Validation
    if (!costForm.estate_id || !costForm.year || !costForm.month) {
      setError('Estate, year, and month are required');
      return;
    }

    if (!costForm.fertilizer_cost_lkr && !costForm.chemical_cost_lkr && 
        !costForm.labour_input_cost_lkr && !costForm.other_cost_lkr) {
      setError('At least one cost field must be filled');
      return;
    }

    setSaving(true);
    try {
      const response = await apiService.createInputCost(token, {
        estate_id: costForm.estate_id,
        year: parseInt(costForm.year),
        month: parseInt(costForm.month),
        fertilizer_cost_lkr: parseFloat(costForm.fertilizer_cost_lkr || 0),
        chemical_cost_lkr: parseFloat(costForm.chemical_cost_lkr || 0),
        labour_input_cost_lkr: parseFloat(costForm.labour_input_cost_lkr || 0),
        other_cost_lkr: parseFloat(costForm.other_cost_lkr || 0),
        source: costForm.source,
      });

      setSuccessMsg('Input cost saved successfully!');
      setTimeout(() => {
        setCostForm({
          estate_id: estates.length > 0 ? estates[0].id : '',
          year: new Date().getFullYear(),
          month: new Date().getMonth() + 1,
          fertilizer_cost_lkr: '',
          chemical_cost_lkr: '',
          labour_input_cost_lkr: '',
          other_cost_lkr: '',
          source: 'manual',
        });
        setError('');
        setSuccessMsg('');
        onSuccess();
        onClose();
      }, 1500);
    } catch (e) {
      setError(e.message || 'Failed to save input cost');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveYield = async () => {
    setError('');
    setSuccessMsg('');

    // Validation
    if (!yieldForm.estate_id || !yieldForm.year || !yieldForm.month || !yieldForm.yield_kg) {
      setError('Estate, year, month, and yield are required');
      return;
    }

    if (parseFloat(yieldForm.yield_kg) < 0) {
      setError('Yield must be non-negative');
      return;
    }

    setSaving(true);
    try {
      const response = await apiService.createYieldRecord(token, {
        estate_id: yieldForm.estate_id,
        year: parseInt(yieldForm.year),
        month: parseInt(yieldForm.month),
        yield_kg: parseFloat(yieldForm.yield_kg),
        source: yieldForm.source,
      });

      setSuccessMsg('Yield record saved successfully!');
      setTimeout(() => {
        setYieldForm({
          estate_id: estates.length > 0 ? estates[0].id : '',
          year: new Date().getFullYear(),
          month: new Date().getMonth() + 1,
          yield_kg: '',
          source: 'manual',
        });
        setError('');
        setSuccessMsg('');
        onSuccess();
        onClose();
      }, 1500);
    } catch (e) {
      setError(e.message || 'Failed to save yield record');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 2000,
      padding: '1rem',
    }}>
      <div style={{
        background: 'var(--color-surface)',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '600px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        maxHeight: '90vh',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{
          padding: '24px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
              📊 Add Monthly Data
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', margin: '4px 0 0 0' }}>
              Enter input costs or yield records for an estate
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '1.5rem',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              padding: 0,
            }}
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface-2)',
        }}>
          <button
            onClick={() => { setActiveTab('costs'); setError(''); setSuccessMsg(''); }}
            style={{
              flex: 1,
              padding: '16px',
              border: 'none',
              background: activeTab === 'costs' ? 'var(--color-surface)' : 'transparent',
              borderBottom: activeTab === 'costs' ? '3px solid var(--color-primary)' : 'none',
              color: activeTab === 'costs' ? 'var(--color-primary)' : 'var(--color-text-muted)',
              fontWeight: activeTab === 'costs' ? 600 : 500,
              cursor: 'pointer',
              fontSize: '0.9375rem',
              transition: 'all 0.2s',
            }}
          >
            💰 Input Costs
          </button>
          <button
            onClick={() => { setActiveTab('yield'); setError(''); setSuccessMsg(''); }}
            style={{
              flex: 1,
              padding: '16px',
              border: 'none',
              background: activeTab === 'yield' ? 'var(--color-surface)' : 'transparent',
              borderBottom: activeTab === 'yield' ? '3px solid var(--color-primary)' : 'none',
              color: activeTab === 'yield' ? 'var(--color-primary)' : 'var(--color-text-muted)',
              fontWeight: activeTab === 'yield' ? 600 : 500,
              cursor: 'pointer',
              fontSize: '0.9375rem',
              transition: 'all 0.2s',
            }}
          >
            🌾 Yield Record
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '24px', flex: 1, overflowY: 'auto' }}>
          {error && (
            <div style={{
              padding: '12px 14px',
              borderRadius: '8px',
              background: 'rgba(220,38,38,0.1)',
              color: 'var(--color-danger)',
              fontSize: '0.875rem',
              marginBottom: '16px',
            }}>
              ⚠️ {error}
            </div>
          )}

          {successMsg && (
            <div style={{
              padding: '12px 14px',
              borderRadius: '8px',
              background: 'rgba(34,197,94,0.1)',
              color: 'var(--color-success)',
              fontSize: '0.875rem',
              marginBottom: '16px',
            }}>
              ✓ {successMsg}
            </div>
          )}

          {activeTab === 'costs' && (
            <div>
              {/* Estate Selector */}
              <div style={{ marginBottom: '18px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '0.8125rem',
                  fontWeight: '600',
                  color: 'var(--color-text-muted)',
                  marginBottom: '6px',
                }}>
                  Estate <span style={{ color: 'var(--color-danger)' }}>*</span>
                </label>
                <select
                  value={costForm.estate_id}
                  onChange={(e) => setCostForm(p => ({ ...p, estate_id: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-surface-2)',
                    color: 'var(--color-text)',
                    fontSize: '0.875rem',
                    fontWeight: '500',
                  }}
                >
                  {estates.map(e => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              </div>

              {/* Year & Month */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '18px' }}>
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: '0.8125rem',
                    fontWeight: '600',
                    color: 'var(--color-text-muted)',
                    marginBottom: '6px',
                  }}>
                    Year <span style={{ color: 'var(--color-danger)' }}>*</span>
                  </label>
                  <input
                    type="number"
                    min="2000"
                    max="2100"
                    value={costForm.year}
                    onChange={(e) => setCostForm(p => ({ ...p, year: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface-2)',
                      color: 'var(--color-text)',
                      fontSize: '0.875rem',
                    }}
                  />
                </div>
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: '0.8125rem',
                    fontWeight: '600',
                    color: 'var(--color-text-muted)',
                    marginBottom: '6px',
                  }}>
                    Month <span style={{ color: 'var(--color-danger)' }}>*</span>
                  </label>
                  <select
                    value={costForm.month}
                    onChange={(e) => setCostForm(p => ({ ...p, month: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface-2)',
                      color: 'var(--color-text)',
                      fontSize: '0.875rem',
                    }}
                  >
                    {monthOptions.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Cost Fields */}
              {[
                ['fertilizer_cost_lkr', '🌱 Fertilizer Cost (LKR)'],
                ['chemical_cost_lkr', '🧪 Chemical Cost (LKR)'],
                ['labour_input_cost_lkr', '👥 Labour Cost (LKR)'],
                ['other_cost_lkr', '📦 Other Cost (LKR)'],
              ].map(([field, label]) => (
                <div key={field} style={{ marginBottom: '16px' }}>
                  <label style={{
                    display: 'block',
                    fontSize: '0.8125rem',
                    fontWeight: '600',
                    color: 'var(--color-text-muted)',
                    marginBottom: '6px',
                  }}>
                    {label}
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={costForm[field]}
                    onChange={(e) => setCostForm(p => ({ ...p, [field]: e.target.value }))}
                    placeholder="0.00"
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface-2)',
                      color: 'var(--color-text)',
                      fontSize: '0.875rem',
                    }}
                  />
                </div>
              ))}

              {/* Total Cost Display */}
              <div style={{
                padding: '16px',
                borderRadius: '8px',
                background: 'rgba(34,197,94,0.08)',
                border: '2px solid rgba(34,197,94,0.2)',
                marginBottom: '16px',
              }}>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', fontWeight: '600' }}>
                  Total Cost
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--color-success)', marginTop: '4px' }}>
                  Rs. {parseFloat(totalCost).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>

              {/* Source */}
              <div style={{ marginBottom: '18px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '0.8125rem',
                  fontWeight: '600',
                  color: 'var(--color-text-muted)',
                  marginBottom: '6px',
                }}>
                  Source (optional)
                </label>
                <input
                  type="text"
                  value={costForm.source}
                  onChange={(e) => setCostForm(p => ({ ...p, source: e.target.value }))}
                  placeholder="e.g., manual, csv"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-surface-2)',
                    color: 'var(--color-text)',
                    fontSize: '0.875rem',
                  }}
                />
              </div>
            </div>
          )}

          {activeTab === 'yield' && (
            <div>
              {/* Estate Selector */}
              <div style={{ marginBottom: '18px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '0.8125rem',
                  fontWeight: '600',
                  color: 'var(--color-text-muted)',
                  marginBottom: '6px',
                }}>
                  Estate <span style={{ color: 'var(--color-danger)' }}>*</span>
                </label>
                <select
                  value={yieldForm.estate_id}
                  onChange={(e) => setYieldForm(p => ({ ...p, estate_id: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-surface-2)',
                    color: 'var(--color-text)',
                    fontSize: '0.875rem',
                    fontWeight: '500',
                  }}
                >
                  {estates.map(e => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              </div>

              {/* Year & Month */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '18px' }}>
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: '0.8125rem',
                    fontWeight: '600',
                    color: 'var(--color-text-muted)',
                    marginBottom: '6px',
                  }}>
                    Year <span style={{ color: 'var(--color-danger)' }}>*</span>
                  </label>
                  <input
                    type="number"
                    min="2000"
                    max="2100"
                    value={yieldForm.year}
                    onChange={(e) => setYieldForm(p => ({ ...p, year: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface-2)',
                      color: 'var(--color-text)',
                      fontSize: '0.875rem',
                    }}
                  />
                </div>
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: '0.8125rem',
                    fontWeight: '600',
                    color: 'var(--color-text-muted)',
                    marginBottom: '6px',
                  }}>
                    Month <span style={{ color: 'var(--color-danger)' }}>*</span>
                  </label>
                  <select
                    value={yieldForm.month}
                    onChange={(e) => setYieldForm(p => ({ ...p, month: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface-2)',
                      color: 'var(--color-text)',
                      fontSize: '0.875rem',
                    }}
                  >
                    {monthOptions.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Yield Field */}
              <div style={{ marginBottom: '18px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '0.8125rem',
                  fontWeight: '600',
                  color: 'var(--color-text-muted)',
                  marginBottom: '6px',
                }}>
                  Yield (kg) <span style={{ color: 'var(--color-danger)' }}>*</span>
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.001"
                  value={yieldForm.yield_kg}
                  onChange={(e) => setYieldForm(p => ({ ...p, yield_kg: e.target.value }))}
                  placeholder="0.000"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-surface-2)',
                    color: 'var(--color-text)',
                    fontSize: '0.875rem',
                  }}
                />
              </div>

              {/* Source */}
              <div style={{ marginBottom: '18px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '0.8125rem',
                  fontWeight: '600',
                  color: 'var(--color-text-muted)',
                  marginBottom: '6px',
                }}>
                  Source (optional)
                </label>
                <input
                  type="text"
                  value={yieldForm.source}
                  onChange={(e) => setYieldForm(p => ({ ...p, source: e.target.value }))}
                  placeholder="e.g., manual, csv"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-surface-2)',
                    color: 'var(--color-text)',
                    fontSize: '0.875rem',
                  }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '20px 24px',
          borderTop: '1px solid var(--color-border)',
          display: 'flex',
          gap: '12px',
          justifyContent: 'flex-end',
          background: 'var(--color-surface-2)',
        }}>
          <button
            onClick={onClose}
            disabled={saving}
            style={{
              padding: '10px 24px',
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
              if (!saving) e.target.style.background = 'var(--color-surface)';
            }}
            onMouseOut={(e) => {
              e.target.style.background = 'transparent';
            }}
          >
            Cancel
          </button>
          <button
            onClick={activeTab === 'costs' ? handleSaveInputCost : handleSaveYield}
            disabled={saving}
            style={{
              padding: '10px 24px',
              borderRadius: '8px',
              border: 'none',
              background: 'var(--color-primary)',
              color: '#fff',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontWeight: '600',
              fontSize: '0.875rem',
              opacity: saving ? 0.7 : 1,
              transition: 'opacity 0.2s',
            }}
          >
            {saving ? '💾 Saving…' : '✓ Save ' + (activeTab === 'costs' ? 'Input Cost' : 'Yield')}
          </button>
        </div>
      </div>
    </div>
  );
}
