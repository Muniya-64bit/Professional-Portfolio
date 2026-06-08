'use client';

import { useState, useRef } from 'react';

export function CSVImportModal({ isOpen, onClose, recordType, token, apiService, onSuccess, estates }) {
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [uploadProgress, setUploadProgress] = useState(null);
  const fileInputRef = useRef(null);

  const isInputCost = recordType === 'costs';
  const columns = isInputCost
    ? ['estate_id', 'year', 'month', 'fertilizer_cost_lkr', 'chemical_cost_lkr', 'labour_input_cost_lkr', 'other_cost_lkr', 'source']
    : ['estate_id', 'year', 'month', 'yield_kg', 'source'];

  const downloadTemplate = () => {
    const headers = isInputCost
      ? 'estate_id,year,month,fertilizer_cost_lkr,chemical_cost_lkr,labour_input_cost_lkr,other_cost_lkr,source\n' +
        'e123,2026,6,5000,2000,3000,500,manual\n'
      : 'estate_id,year,month,yield_kg,source\n' +
        'e123,2026,6,1500.5,manual\n';

    const blob = new Blob([headers], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${isInputCost ? 'input_costs' : 'yield_records'}_template.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const parseCSV = (text) => {
    const lines = text.trim().split('\n');
    if (lines.length < 2) throw new Error('CSV must have header and at least one data row');

    const [headerLine] = lines;
    const headers = headerLine.split(',').map(h => h.trim());

    const records = [];
    const errors = [];

    for (let i = 1; i < lines.length; i++) {
      try {
        const values = lines[i].split(',').map(v => v.trim());
        if (values.every(v => v === '')) continue; // Skip empty rows

        const record = {};
        headers.forEach((header, idx) => {
          record[header] = values[idx];
        });
        records.push({ data: record, rowNumber: i + 1 });
      } catch (e) {
        errors.push({ row: i + 1, error: e.message });
      }
    }

    return { records, errors };
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError('');
    setSuccessMsg('');
    setImporting(true);
    setUploadProgress({ loaded: 0, total: 100 });

    try {
      const text = await file.text();
      const { records, errors: parseErrors } = parseCSV(text);

      if (records.length === 0) {
        throw new Error('No valid records found in CSV');
      }

      let successCount = 0;
      let failureCount = 0;
      const failureReasons = [];

      // Import records sequentially
      for (let i = 0; i < records.length; i++) {
        const { data, rowNumber } = records[i];
        const progress = Math.round((i / records.length) * 100);
        setUploadProgress({ loaded: progress, total: 100 });

        try {
          // Validate required fields
          const estateId = data.estate_id?.trim();
          const year = parseInt(data.year);
          const month = parseInt(data.month);

          if (!estateId || isNaN(year) || isNaN(month)) {
            throw new Error('Missing required fields: estate_id, year, month');
          }

          if (!(2000 <= year <= 2100)) {
            throw new Error(`Year must be between 2000 and 2100`);
          }

          if (!(1 <= month <= 12)) {
            throw new Error(`Month must be between 1 and 12`);
          }

          // Verify estate exists
          const estateExists = estates.some(e => e.id === estateId || e.name === estateId);
          if (!estateExists) {
            throw new Error(`Estate not found: ${estateId}`);
          }

          if (isInputCost) {
            const fertilizer = parseFloat(data.fertilizer_cost_lkr || 0);
            const chemical = parseFloat(data.chemical_cost_lkr || 0);
            const labour = parseFloat(data.labour_input_cost_lkr || 0);
            const other = parseFloat(data.other_cost_lkr || 0);

            if (isNaN(fertilizer) || isNaN(chemical) || isNaN(labour) || isNaN(other)) {
              throw new Error('Cost fields must be valid numbers');
            }

            if (fertilizer < 0 || chemical < 0 || labour < 0 || other < 0) {
              throw new Error('Cost fields must be non-negative');
            }

            await apiService.createInputCost(token, {
              estate_id: estateId,
              year,
              month,
              fertilizer_cost_lkr: fertilizer,
              chemical_cost_lkr: chemical,
              labour_input_cost_lkr: labour,
              other_cost_lkr: other,
              source: (data.source || 'csv').trim(),
            });
          } else {
            const yieldKg = parseFloat(data.yield_kg);

            if (isNaN(yieldKg)) {
              throw new Error('yield_kg must be a valid number');
            }

            if (yieldKg < 0) {
              throw new Error('yield_kg must be non-negative');
            }

            await apiService.createYieldRecord(token, {
              estate_id: estateId,
              year,
              month,
              yield_kg: yieldKg,
              source: (data.source || 'csv').trim(),
            });
          }

          successCount++;
        } catch (e) {
          failureCount++;
          failureReasons.push(`Row ${rowNumber}: ${e.message}`);
        }
      }

      const summary = `${successCount} row${successCount !== 1 ? 's' : ''} imported`;
      const failures = failureCount > 0 
        ? `${failureCount} row${failureCount !== 1 ? 's' : ''} failed` 
        : null;

      setSuccessMsg(`✓ ${summary}${failures ? ` · ${failures}` : ''}`);

      if (failureCount > 0 && failureReasons.length > 0) {
        // Show first few failures
        const failureText = failureReasons.slice(0, 3).join('\n');
        setError(`Import completed with issues:\n${failureText}${failureReasons.length > 3 ? `\n... and ${failureReasons.length - 3} more` : ''}`);
      }

      setTimeout(() => {
        onSuccess();
        onClose();
      }, 2000);
    } catch (e) {
      setError(e.message || 'Failed to import CSV');
    } finally {
      setImporting(false);
      setUploadProgress(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
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
        maxWidth: '500px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        padding: '32px',
      }}>
        {/* Header */}
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '700', margin: '0 0 8px 0' }}>
            📥 Import {isInputCost ? 'Input Costs' : 'Yield Records'}
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', margin: 0 }}>
            Upload a CSV file with {isInputCost ? 'input costs' : 'yield records'}
          </p>
        </div>

        {/* Messages */}
        {error && (
          <div style={{
            padding: '12px 14px',
            borderRadius: '8px',
            background: 'rgba(220,38,38,0.1)',
            color: 'var(--color-danger)',
            fontSize: '0.875rem',
            marginBottom: '16px',
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace',
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

        {/* Upload Progress */}
        {uploadProgress && (
          <div style={{ marginBottom: '16px' }}>
            <div style={{
              fontSize: '0.8125rem',
              color: 'var(--color-text-muted)',
              marginBottom: '8px',
              fontWeight: '600',
            }}>
              Processing: {uploadProgress.loaded}%
            </div>
            <div style={{
              width: '100%',
              height: '8px',
              borderRadius: '4px',
              background: 'var(--color-surface-2)',
              overflow: 'hidden',
            }}>
              <div
                style={{
                  width: `${uploadProgress.loaded}%`,
                  height: '100%',
                  background: 'var(--color-primary)',
                  transition: 'width 0.3s',
                }}
              />
            </div>
          </div>
        )}

        {/* CSV Columns Reference */}
        <div style={{
          padding: '12px 14px',
          borderRadius: '8px',
          background: 'var(--color-surface-2)',
          marginBottom: '20px',
        }}>
          <div style={{
            fontSize: '0.8125rem',
            fontWeight: '600',
            color: 'var(--color-text-muted)',
            marginBottom: '8px',
          }}>
            Required columns:
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '8px',
          }}>
            {columns.map(col => (
              <div
                key={col}
                style={{
                  fontSize: '0.8125rem',
                  color: 'var(--color-text)',
                  fontFamily: 'monospace',
                  padding: '6px 8px',
                  background: 'rgba(0,0,0,0.1)',
                  borderRadius: '4px',
                }}
              >
                {col}
              </div>
            ))}
          </div>
        </div>

        {/* File Upload */}
        <div style={{ marginBottom: '20px' }}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            disabled={importing}
            style={{ display: 'none' }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            style={{
              width: '100%',
              padding: '12px 16px',
              borderRadius: '8px',
              border: '2px dashed var(--color-border)',
              background: 'transparent',
              color: 'var(--color-text)',
              cursor: importing ? 'not-allowed' : 'pointer',
              fontWeight: '600',
              fontSize: '0.875rem',
              transition: 'all 0.2s',
              opacity: importing ? 0.6 : 1,
            }}
            onMouseOver={(e) => {
              if (!importing) {
                e.target.style.borderColor = 'var(--color-primary)';
                e.target.style.background = 'rgba(var(--color-primary-rgb, 37,99,235), 0.05)';
              }
            }}
            onMouseOut={(e) => {
              e.target.style.borderColor = 'var(--color-border)';
              e.target.style.background = 'transparent';
            }}
          >
            {importing ? '⏳ Processing…' : '📂 Select CSV file'}
          </button>
        </div>

        {/* Download Template */}
        <button
          onClick={downloadTemplate}
          disabled={importing}
          style={{
            width: '100%',
            padding: '10px 16px',
            borderRadius: '8px',
            border: '1px solid var(--color-border)',
            background: 'transparent',
            color: 'var(--color-text-muted)',
            cursor: importing ? 'not-allowed' : 'pointer',
            fontWeight: '600',
            fontSize: '0.8125rem',
            marginBottom: '20px',
            opacity: importing ? 0.6 : 1,
          }}
        >
          📋 Download template
        </button>

        {/* Footer */}
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            disabled={importing}
            style={{
              padding: '10px 24px',
              borderRadius: '8px',
              border: '1px solid var(--color-border)',
              background: 'transparent',
              color: 'var(--color-text-muted)',
              cursor: importing ? 'not-allowed' : 'pointer',
              fontWeight: '600',
              fontSize: '0.875rem',
              opacity: importing ? 0.6 : 1,
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
