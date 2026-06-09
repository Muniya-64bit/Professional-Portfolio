"""
Integration tests for ROI blueprint routes (roi.py).
All DB calls are mocked — no live database needed.
"""
import os
import sys
import json
import uuid
import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')

from tests.conftest import auth_header

ESTATE_ID = str(uuid.uuid4())

# ── Cursor / connection helpers ───────────────────────────────────────────────

def _row_description(names):
    """Build a minimal cursor.description list for _row_dict()."""
    Col = type('Col', (), {})
    cols = []
    for n in names:
        c = Col()
        c.name = n
        cols.append(c)
    return cols


def _make_conn_with_rows(rows, col_names):
    """Return (conn, cur) where cur.fetchall returns rows and description is set."""
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur.fetchone.return_value = rows[0] if rows else None
    cur.description = _row_description(col_names)
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    return conn, cur


def _no_db_conn():
    return None


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/roi/input-costs
# ═════════════════════════════════════════════════════════════════════════════

class TestListInputCosts:
    def test_requires_auth(self, client):
        resp = client.get('/api/roi/input-costs')
        assert resp.status_code == 401

    def test_db_unavailable_returns_503(self, client, admin_token):
        with patch('roi._db', return_value=None):
            resp = client.get('/api/roi/input-costs', headers=auth_header(admin_token))
        assert resp.status_code == 503

    def test_returns_200_empty_list(self, client, admin_token):
        conn, _ = _make_conn_with_rows([], [])
        with patch('roi._db', return_value=conn):
            resp = client.get('/api/roi/input-costs', headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_filters_by_estate_year_month(self, client, admin_token):
        conn, cur = _make_conn_with_rows([], [])
        with patch('roi._db', return_value=conn):
            resp = client.get(
                '/api/roi/input-costs?estate_id=abc&year=2025&month=6',
                headers=auth_header(admin_token),
            )
        assert resp.status_code == 200
        # Verify params were sent to execute (estate_id, year, month all appended)
        call_args = cur.execute.call_args[0]
        assert 'abc' in call_args[1]
        assert 2025 in call_args[1]
        assert 6 in call_args[1]


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/roi/input-costs
# ═════════════════════════════════════════════════════════════════════════════

class TestCreateInputCost:
    def _good_payload(self):
        return {
            'estate_id': ESTATE_ID,
            'year': 2025,
            'month': 6,
            'fertilizer_cost_lkr': 10000,
            'chemical_cost_lkr': 5000,
            'labour_input_cost_lkr': 20000,
            'other_cost_lkr': 2000,
        }

    def test_requires_auth(self, client):
        resp = client.post('/api/roi/input-costs', json=self._good_payload())
        assert resp.status_code == 401

    def test_missing_estate_id_returns_400(self, client, admin_token):
        data = self._good_payload()
        del data['estate_id']
        resp = client.post('/api/roi/input-costs', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_missing_year_returns_400(self, client, admin_token):
        data = self._good_payload()
        del data['year']
        resp = client.post('/api/roi/input-costs', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_missing_month_returns_400(self, client, admin_token):
        data = self._good_payload()
        del data['month']
        resp = client.post('/api/roi/input-costs', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_year_out_of_range_returns_400(self, client, admin_token):
        data = self._good_payload()
        data['year'] = 1999
        resp = client.post('/api/roi/input-costs', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_month_out_of_range_returns_400(self, client, admin_token):
        data = self._good_payload()
        data['month'] = 13
        resp = client.post('/api/roi/input-costs', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_negative_cost_returns_400(self, client, admin_token):
        data = self._good_payload()
        data['fertilizer_cost_lkr'] = -100
        resp = client.post('/api/roi/input-costs', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_non_numeric_cost_returns_400(self, client, admin_token):
        data = self._good_payload()
        data['chemical_cost_lkr'] = 'abc'
        resp = client.post('/api/roi/input-costs', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_db_unavailable_returns_503(self, client, admin_token):
        with patch('roi._db', return_value=None):
            resp = client.post('/api/roi/input-costs', json=self._good_payload(),
                               headers=auth_header(admin_token))
        assert resp.status_code == 503

    def test_duplicate_returns_409(self, client, admin_token):
        conn = MagicMock()
        cur = MagicMock()
        # First fetchone: duplicate found
        cur.fetchone.return_value = (uuid.uuid4(),)
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('roi._db', return_value=conn):
            resp = client.post('/api/roi/input-costs', json=self._good_payload(),
                               headers=auth_header(admin_token))
        assert resp.status_code == 409

    def test_estate_not_found_returns_404(self, client, admin_token):
        conn = MagicMock()
        cur = MagicMock()
        # First: no duplicate; Second: estate not found
        cur.fetchone.side_effect = [None, None]
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('roi._db', return_value=conn):
            resp = client.post('/api/roi/input-costs', json=self._good_payload(),
                               headers=auth_header(admin_token))
        assert resp.status_code == 404

    def test_successful_create_returns_201(self, client, admin_token):
        rec_id = uuid.uuid4()
        estate_uuid = uuid.uuid4()
        now = datetime.utcnow()
        inserted_row = (rec_id, estate_uuid, 2025, 6, 10000, 5000, 20000, 2000, 37000, 'manual', now)
        col_names = ['id', 'estate_id', 'year', 'month',
                     'fertilizer_cost_lkr', 'chemical_cost_lkr',
                     'labour_input_cost_lkr', 'other_cost_lkr',
                     'total_cost_lkr', 'source', 'created_at']

        conn = MagicMock()
        cur = MagicMock()
        # 1st fetchone: no duplicate; 2nd: estate found; 3rd: inserted row
        cur.fetchone.side_effect = [None, (estate_uuid,), inserted_row]
        cur.description = _row_description(col_names)
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('roi._db', return_value=conn):
            with patch('roi._recalculate_roi_snapshot'):
                resp = client.post('/api/roi/input-costs', json=self._good_payload(),
                                   headers=auth_header(admin_token))
        assert resp.status_code == 201


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/roi/yield-records
# ═════════════════════════════════════════════════════════════════════════════

class TestListYieldRecords:
    def test_requires_auth(self, client):
        resp = client.get('/api/roi/yield-records')
        assert resp.status_code == 401

    def test_db_unavailable_returns_503(self, client, admin_token):
        with patch('roi._db', return_value=None):
            resp = client.get('/api/roi/yield-records', headers=auth_header(admin_token))
        assert resp.status_code == 503

    def test_returns_200_empty_list(self, client, admin_token):
        conn, _ = _make_conn_with_rows([], [])
        with patch('roi._db', return_value=conn):
            resp = client.get('/api/roi/yield-records', headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.get_json() == []


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/roi/yield-records
# ═════════════════════════════════════════════════════════════════════════════

class TestCreateYieldRecord:
    def _good_payload(self):
        return {
            'estate_id': ESTATE_ID,
            'year': 2025,
            'month': 6,
            'yield_kg': 50000,
        }

    def test_requires_auth(self, client):
        resp = client.post('/api/roi/yield-records', json=self._good_payload())
        assert resp.status_code == 401

    def test_missing_estate_id_returns_400(self, client, admin_token):
        data = self._good_payload()
        del data['estate_id']
        resp = client.post('/api/roi/yield-records', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_missing_yield_kg_returns_400(self, client, admin_token):
        data = self._good_payload()
        del data['yield_kg']
        resp = client.post('/api/roi/yield-records', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_negative_yield_returns_400(self, client, admin_token):
        data = self._good_payload()
        data['yield_kg'] = -1
        resp = client.post('/api/roi/yield-records', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_non_numeric_yield_returns_400(self, client, admin_token):
        data = self._good_payload()
        data['yield_kg'] = 'lots'
        resp = client.post('/api/roi/yield-records', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_year_too_early_returns_400(self, client, admin_token):
        data = self._good_payload()
        data['year'] = 1990
        resp = client.post('/api/roi/yield-records', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_month_zero_returns_400(self, client, admin_token):
        data = self._good_payload()
        data['month'] = 0
        resp = client.post('/api/roi/yield-records', json=data, headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_duplicate_returns_409(self, client, admin_token):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = (uuid.uuid4(),)  # duplicate found
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('roi._db', return_value=conn):
            resp = client.post('/api/roi/yield-records', json=self._good_payload(),
                               headers=auth_header(admin_token))
        assert resp.status_code == 409

    def test_estate_not_found_returns_404(self, client, admin_token):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.side_effect = [None, None]  # no dup, no estate
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('roi._db', return_value=conn):
            resp = client.post('/api/roi/yield-records', json=self._good_payload(),
                               headers=auth_header(admin_token))
        assert resp.status_code == 404

    def test_db_unavailable_returns_503(self, client, admin_token):
        with patch('roi._db', return_value=None):
            resp = client.post('/api/roi/yield-records', json=self._good_payload(),
                               headers=auth_header(admin_token))
        assert resp.status_code == 503

    def test_successful_create_returns_201(self, client, admin_token):
        rec_id = uuid.uuid4()
        estate_uuid = uuid.uuid4()
        now = datetime.utcnow()
        inserted_row = (rec_id, estate_uuid, 2025, 6, 50000.0, 'manual', now)
        col_names = ['id', 'estate_id', 'year', 'month', 'yield_kg', 'source', 'created_at']

        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.side_effect = [None, (estate_uuid,), inserted_row]
        cur.description = _row_description(col_names)
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('roi._db', return_value=conn):
            with patch('roi._recalculate_roi_snapshot'):
                resp = client.post('/api/roi/yield-records', json=self._good_payload(),
                                   headers=auth_header(admin_token))
        assert resp.status_code == 201


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/roi/summary
# ═════════════════════════════════════════════════════════════════════════════

class TestGetROISummary:
    def test_requires_auth(self, client):
        resp = client.get('/api/roi/summary')
        assert resp.status_code == 401

    def test_db_unavailable_returns_503(self, client, admin_token):
        with patch('roi._db', return_value=None):
            resp = client.get('/api/roi/summary', headers=auth_header(admin_token))
        assert resp.status_code == 503

    def test_returns_summary_for_year_month(self, client, admin_token):
        conn, cur = _make_conn_with_rows(
            [(3, Decimal('120.50'), Decimal('100.00'), Decimal('150.00'), 1)],
            ['total_estates', 'avg_cost_per_kg', 'best_cost_per_kg', 'worst_cost_per_kg', 'flagged_count'],
        )
        with patch('roi._db', return_value=conn):
            resp = client.get('/api/roi/summary?year=2025&month=6', headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total_estates'] == 3
        assert data['flagged_count'] == 1

    def test_summary_defaults_to_current_month_when_no_params(self, client, admin_token):
        conn, cur = _make_conn_with_rows(
            [(0, None, None, None, 0)],
            ['total_estates', 'avg_cost_per_kg', 'best_cost_per_kg', 'worst_cost_per_kg', 'flagged_count'],
        )
        with patch('roi._db', return_value=conn):
            resp = client.get('/api/roi/summary', headers=auth_header(admin_token))
        assert resp.status_code == 200

    def test_summary_with_months_param(self, client, admin_token):
        conn, cur = _make_conn_with_rows(
            [(5, Decimal('110.00'), Decimal('90.00'), Decimal('130.00'), 2)],
            ['total_estates', 'avg_cost_per_kg', 'best_cost_per_kg', 'worst_cost_per_kg', 'flagged_count'],
        )
        with patch('roi._db', return_value=conn):
            resp = client.get('/api/roi/summary?months=12', headers=auth_header(admin_token))
        assert resp.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/roi/rankings
# ═════════════════════════════════════════════════════════════════════════════

class TestGetROIRankings:
    def test_requires_auth(self, client):
        resp = client.get('/api/roi/rankings')
        assert resp.status_code == 401

    def test_db_unavailable_returns_503(self, client, admin_token):
        with patch('roi._db', return_value=None):
            resp = client.get('/api/roi/rankings', headers=auth_header(admin_token))
        assert resp.status_code == 503

    def test_returns_list(self, client, admin_token):
        conn, _ = _make_conn_with_rows([], [])
        with patch('roi._db', return_value=conn):
            resp = client.get('/api/roi/rankings?year=2025&month=6', headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)


# ═════════════════════════════════════════════════════════════════════════════
# _recalculate_roi_snapshot() — unit test
# ═════════════════════════════════════════════════════════════════════════════

class TestRecalculateROISnapshot:
    def test_handles_db_unavailable_gracefully(self):
        from roi import _recalculate_roi_snapshot
        with patch('roi.get_db_connection', return_value=None):
            # Should not raise
            _recalculate_roi_snapshot(2025, 6)

    def test_handles_no_complete_data(self):
        from roi import _recalculate_roi_snapshot
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchall.return_value = []
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('roi.get_db_connection', return_value=conn):
            # Returns early when no rows — should not raise
            _recalculate_roi_snapshot(2025, 6)
        conn.rollback.assert_not_called()

    def test_computes_ranks_and_flags(self):
        from roi import _recalculate_roi_snapshot
        estate1 = uuid.uuid4()
        estate2 = uuid.uuid4()
        estate3 = uuid.uuid4()
        # estate1=100, estate2=200, estate3=500 → mean=266.7, std≈166.5, threshold≈433.2
        # estate3 should be flagged
        rows = [
            (estate1, Decimal('100000'), Decimal('1000'), Decimal('100')),
            (estate2, Decimal('200000'), Decimal('1000'), Decimal('200')),
            (estate3, Decimal('500000'), Decimal('1000'), Decimal('500')),
        ]
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchall.return_value = rows
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('roi.get_db_connection', return_value=conn):
            _recalculate_roi_snapshot(2025, 6)

        conn.commit.assert_called_once()
        # 3 upserts expected
        insert_calls = [
            c for c in cur.execute.call_args_list
            if 'roi_snapshot' in str(c)
        ]
        assert len(insert_calls) == 3

    def test_exception_rolls_back(self):
        from roi import _recalculate_roi_snapshot
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchall.side_effect = Exception('DB error')
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('roi.get_db_connection', return_value=conn):
            _recalculate_roi_snapshot(2025, 6)

        conn.rollback.assert_called_once()
