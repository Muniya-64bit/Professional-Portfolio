/**
 * API service for backend communication with token handling
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const TOKEN_REFRESH_THRESHOLD = 3600;

let _onUnauthorized = null;
export const setOnUnauthorized = (fn) => { _onUnauthorized = fn; };

export const apiService = {
  // Auth endpoints
  async signup(email, password, fullName, role, estateId) {
    try {
      const response = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
          role,
          estate_id: estateId || null,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Signup failed');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  },

  // Authenticated estate list (used in admin user creation form)
  async getPublicEstates(token) {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const response = await fetch(`${API_BASE}/estates/public`, { headers });
    if (!response.ok) throw new Error('Failed to load estates');
    return await response.json();
  },

  // Admin-only: list all system users
  async getSystemUsers(token) {
    return this._auth(token, 'GET', '/auth/users');
  },

  // Admin-only: create a system user
  async createSystemUser(token, data) {
    return this._auth(token, 'POST', '/auth/users', data);
  },

  // Admin-only: check scheduler status
  async getSchedulerStatus(token) {
    return this._auth(token, 'GET', '/scheduler/status');
  },

  async login(email, password) {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Login failed');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  },

  async verifyToken(token) {
    try {
      const response = await fetch(`${API_BASE}/auth/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Token verification failed');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  },

  async getProfile(token) {
    try {
      const response = await fetch(`${API_BASE}/auth/profile`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch profile');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  },

  async refreshToken(token) {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  },

  async logout(token) {
    try {
      const response = await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Logout failed');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  },

  // ── Auth helpers ──────────────────────────────────────────────────────────

  async _auth(token, method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}${path}`, opts);
    if (res.status === 401) {
      if (_onUnauthorized) _onUnauthorized();
      throw new Error('Session expired. Please log in again.');
    }
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
    return json;
  },

  // ── Labour Planner ────────────────────────────────────────────────────────

  async _labour(token, method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}/labour${path}`, opts);
    if (res.status === 401) {
      if (_onUnauthorized) _onUnauthorized();
      throw new Error('Session expired. Please log in again.');
    }
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
    return json;
  },

  getEstates(token) {
    return this._labour(token, 'GET', '/estates');
  },

  createEstate(token, data) {
    return this._labour(token, 'POST', '/estates', data);
  },

  updateEstate(token, estateId, data) {
    return this._labour(token, 'PUT', `/estates/${estateId}`, data);
  },

  deleteEstate(token, estateId) {
    return this._labour(token, 'DELETE', `/estates/${estateId}`);
  },

  getLabourPlans(token, { estateId, monthStart } = {}) {
    const q = new URLSearchParams();
    if (estateId)   q.set('estate_id',    estateId);
    if (monthStart) q.set('period_start', monthStart);
    return this._labour(token, 'GET', `/plans${q.toString() ? '?' + q : ''}`);
  },

  generateMonthlyPlans(token, { year, month, estateId } = {}) {
    const body = {};
    if (year)     body.year = year;
    if (month)    body.month = month;
    if (estateId) body.estate_id = estateId;
    return this._labour(token, 'POST', '/plans/generate-monthly', body);
  },

  getPredictions(token, { estateId, year, month } = {}) {
    const q = new URLSearchParams();
    if (estateId) q.set('estate_id', estateId);
    if (year)     q.set('year',  year);
    if (month)    q.set('month', month);
    return this._labour(token, 'GET', `/predictions${q.toString() ? '?' + q : ''}`);
  },

  getLabourPlan(token, planId) {
    return this._labour(token, 'GET', `/plans/${planId}`);
  },

  createLabourPlan(token, data) {
    return this._labour(token, 'POST', '/plans', data);
  },

  updateLabourPlan(token, planId, data) {
    return this._labour(token, 'PUT', `/plans/${planId}`, data);
  },

  createManualPlan(token, data) {
    return this._labour(token, 'POST', '/plans/manual/create', data);
  },

  addAssignmentToPlan(token, planId, data) {
    return this._labour(token, 'POST', `/plans/${planId}/assignments/add`, data);
  },

  overrideAssignment(token, assignmentId, data) {
    return this._labour(token, 'PUT', `/assignments/${assignmentId}`, data);
  },

  changeGroupAssignment(token, assignmentId, workerGroupId) {
    return this._labour(token, 'PUT', `/assignments/${assignmentId}/change-group`, { worker_group_id: workerGroupId });
  },

  removeAssignment(token, assignmentId) {
    return this._labour(token, 'DELETE', `/assignments/${assignmentId}/remove`);
  },

  removeGroupFromAssignment(token, assignmentId) {
    return this._labour(token, 'PUT', `/assignments/${assignmentId}/remove-group`);
  },

  addEmployeeOverride(token, assignmentId, data) {
    return this._labour(token, 'POST', `/assignments/${assignmentId}/employee-overrides`, data);
  },

  getEmployees(token, { estateId, groupId, skillType } = {}) {
    const q = new URLSearchParams();
    if (estateId)  q.set('estate_id',  estateId);
    if (groupId)   q.set('group_id',   groupId);
    if (skillType) q.set('skill_type', skillType);
    return this._labour(token, 'GET', `/employees${q.toString() ? '?' + q : ''}`);
  },

  createEmployee(token, data) {
    return this._labour(token, 'POST', '/employees', data);
  },

  updateEmployee(token, employeeId, data) {
    return this._labour(token, 'PUT', `/employees/${employeeId}`, data);
  },

  deleteEmployee(token, employeeId) {
    return this._labour(token, 'DELETE', `/employees/${employeeId}`);
  },

  getWorkerGroups(token, estateId) {
    const q = estateId ? `?estate_id=${estateId}` : '';
    return this._labour(token, 'GET', `/groups${q}`);
  },

  updateGroupMember(token, groupId, employeeId, action) {
    return this._labour(token, 'POST', `/groups/${groupId}/members`, { employee_id: employeeId, action });
  },

  getRotation(token, estateId) {
    const q = estateId ? `?estate_id=${estateId}` : '';
    return this._labour(token, 'GET', `/rotation${q}`);
  },

  getRotationMembers(token, estateId, round, groupCode) {
    const q = new URLSearchParams();
    if (estateId)  q.set('estate_id', estateId);
    if (round)     q.set('round', round);
    if (groupCode) q.set('group_code', groupCode);
    return this._labour(token, 'GET', `/rotation/members?${q}`);
  },

  // Block management
  getBlocks(token, estateId) {
    const q = estateId ? `?estate_id=${estateId}` : '';
    return this._labour(token, 'GET', `/blocks${q}`);
  },

  createBlock(token, data) {
    return this._labour(token, 'POST', '/blocks', data);
  },

  updateBlock(token, blockId, data) {
    return this._labour(token, 'PUT', `/blocks/${blockId}`, data);
  },

  deleteBlock(token, blockId) {
    return this._labour(token, 'DELETE', `/blocks/${blockId}`);
  },

  recordPlanYield(token, planId, yields) {
    return this._labour(token, 'POST', `/plans/${planId}/record-yield`, { yields });
  },

  getPlanEfficiency(token, planId) {
    return this._labour(token, 'GET', `/plans/${planId}/efficiency`);
  },

  async downloadPdfReport(token, estateId, year, month) {
    const res = await fetch(`${API_BASE}/reports/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ estate_id: estateId, year, month }),
    });
    if (res.status === 401) {
      if (_onUnauthorized) _onUnauthorized();
      throw new Error('Session expired. Please log in again.');
    }
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      throw new Error(json.error || `Report generation failed (${res.status})`);
    }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const cd   = res.headers.get('content-disposition') || '';
    const name = cd.match(/filename="?([^"]+)"?/)?.[1]
                 || `KVPL_Report_${year}_${String(month).padStart(2,'0')}.pdf`;
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },


  // ── Fertilizer Planner ───────────────────────────────────────────────────

  async _fertilizer(token, method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}/fertilizer${path}`, opts);
    if (res.status === 401) {
      if (_onUnauthorized) _onUnauthorized();
      throw new Error('Session expired. Please log in again.');
    }
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
    return json;
  },

  getFertilizerAlerts(token, estateId) {
    const q = estateId ? `?estate_id=${estateId}` : '';
    return this._fertilizer(token, 'GET', `/alerts${q}`);
  },

  // ── Schedule headers ─────────────────────────────────────────────────────
  getFertilizerSchedules(token, estateId) {
    const q = estateId ? `?estate_id=${estateId}` : '';
    return this._fertilizer(token, 'GET', `/schedules${q}`);
  },

  generateFertilizerScheduleForMonth(token, { estate_id, period_start }) {
    return this._fertilizer(token, 'POST', '/schedules/generate', { estate_id, period_start });
  },

  deleteFertilizerSchedule(token, scheduleId) {
    return this._fertilizer(token, 'DELETE', `/schedules/${scheduleId}`);
  },

  // ── Schedule entries ─────────────────────────────────────────────────────
  getFertilizerScheduleEntries(token, scheduleId, { blockId, status, limit } = {}) {
    const q = new URLSearchParams();
    if (blockId) q.set('block_id', blockId);
    if (status)  q.set('status', status);
    if (limit)   q.set('limit', limit);
    return this._fertilizer(token, 'GET', `/schedules/${scheduleId}/entries${q.toString() ? '?' + q : ''}`);
  },

  updateFertilizerScheduleEntry(token, entryId, data) {
    return this._fertilizer(token, 'PUT', `/entries/${entryId}`, data);
  },

  // legacy: single-estate fetch (most recent active schedule entries)
  getFertilizerSchedule(token, { estateId, blockId, status, limit } = {}) {
    const q = new URLSearchParams();
    if (estateId) q.set('estate_id', estateId);
    if (blockId)  q.set('block_id', blockId);
    if (status)   q.set('status', status);
    if (limit)    q.set('limit', limit);
    return this._fertilizer(token, 'GET', `/schedule${q.toString() ? '?' + q : ''}`);
  },

  // legacy generate alias
  generateFertilizerSchedule(token, estateId) {
    return this._fertilizer(token, 'POST', '/generate', { estate_id: estateId });
  },

  getFertilizerProgramme(token, estateId) {
    const q = estateId ? `?estate_id=${estateId}` : '';
    return this._fertilizer(token, 'GET', `/programme${q}`);
  },

  getFertilizerTypes(token) {
    return this._fertilizer(token, 'GET', '/types');
  },

  createFertilizerType(token, data) {
    return this._fertilizer(token, 'POST', '/types', data);
  },

  updateFertilizerType(token, id, data) {
    return this._fertilizer(token, 'PUT', `/types/${id}`, data);
  },

  recordFertilizerApplication(token, data) {
    return this._fertilizer(token, 'POST', '/applications', data);
  },

  getFertilizerApplications(token, { estateId, blockId, limit } = {}) {
    const q = new URLSearchParams();
    if (estateId) q.set('estate_id', estateId);
    if (blockId)  q.set('block_id', blockId);
    if (limit)    q.set('limit', limit);
    return this._fertilizer(token, 'GET', `/applications${q.toString() ? '?' + q : ''}`);
  },

  getFertilizerHistory(token, blockId, limit) {
    const q = new URLSearchParams({ block_id: blockId });
    if (limit) q.set('limit', limit);
    return this._fertilizer(token, 'GET', `/history?${q}`);
  },

  createFertilizerProgrammeStep(token, data) {
    return this._fertilizer(token, 'POST', '/programme', data);
  },

  updateFertilizerProgrammeStep(token, id, data) {
    return this._fertilizer(token, 'PUT', `/programme/${id}`, data);
  },

  deleteFertilizerProgrammeStep(token, id) {
    return this._fertilizer(token, 'DELETE', `/programme/${id}`);
  },

  // ── Water Efficiency ──────────────────────────────────────────────────────

  async _water(token, method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}/water${path}`, opts);
    if (res.status === 401) {
      if (_onUnauthorized) _onUnauthorized();
      throw new Error('Session expired. Please log in again.');
    }
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
    return json;
  },

  getWaterStatus(token) {
    return this._water(token, 'GET', '/status');
  },

  getWaterUsage(token, year = 2026, estateId = null) {
    const q = new URLSearchParams();
    q.set('year', year);
    if (estateId) q.set('estate_id', estateId);
    return this._water(token, 'GET', `/usage?${q}`);
  },

  getWaterBaseline(token) {
    return this._water(token, 'GET', '/baseline');
  },

  getWaterEstates(token) {
    return this._water(token, 'GET', '/estates');
  },

  addWaterUsage(token, data) {
    return this._water(token, 'POST', '/usage', data);
  },

  updateWaterUsage(token, usageId, data) {
    return this._water(token, 'PUT', `/usage/${usageId}`, data);
  },
  
  deleteWaterUsage(token, usageId) {
  return this._water(token, 'DELETE', `/usage/${usageId}`);
  },

  // ── ROI Calculator ────────────────────────────────────────────────────────

  async _roi(token, method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      credentials: 'include',
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}/roi${path}`, opts);
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
    return json;
  },

  getInputCosts(token, { estateId, year, month } = {}) {
    const q = new URLSearchParams();
    if (estateId) q.set('estate_id', estateId);
    if (year) q.set('year', year);
    if (month) q.set('month', month);
    return this._roi(token, 'GET', `/input-costs${q.toString() ? '?' + q : ''}`);
  },

  createInputCost(token, data) {
    return this._roi(token, 'POST', '/input-costs', data);
  },

  getYieldRecords(token, { estateId, year, month } = {}) {
    const q = new URLSearchParams();
    if (estateId) q.set('estate_id', estateId);
    if (year) q.set('year', year);
    if (month) q.set('month', month);
    return this._roi(token, 'GET', `/yield-records${q.toString() ? '?' + q : ''}`);
  },

  createYieldRecord(token, data) {
    return this._roi(token, 'POST', '/yield-records', data);
  },

  getROISummary(token, params = {}) {
  const qs = new URLSearchParams();
  if (params.months) qs.set('months', params.months);
  if (params.year)   qs.set('year',   params.year);
  if (params.month)  qs.set('month',  params.month);
  return this._roi(token, 'GET', `/summary${qs.toString() ? '?' + qs : ''}`);
},

  getROIRankings(token, params = {}) {
    const qs = new URLSearchParams();
    if (params.months) qs.set('months', params.months);
    if (params.year)   qs.set('year',   params.year);
    if (params.month)  qs.set('month',  params.month);
    return this._roi(token, 'GET', `/rankings${qs.toString() ? '?' + qs : ''}`);
  },

  getROIEstates(token) {
    return this._roi(token, 'GET', '/estates');
  },

  getROIEstateTrend(token, estateId, year) {
    const q = new URLSearchParams({ estate_id: estateId, year });
    return this._roi(token, 'GET', `/estate-trend?${q}`);
  },
  
  // Helper: Decode JWT token to get expiration time
  getTokenExpiration(token) {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return null;

      // JWT uses base64url — convert to standard base64 before atob
      const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=');
      const decoded = JSON.parse(atob(padded));
      return decoded.exp ? decoded.exp * 1000 : null;
    } catch (error) {
      return null;
    }
  },

  // Helper: Check if token should be refreshed
  shouldRefreshToken(token) {
    const expTime = this.getTokenExpiration(token);
    if (!expTime) return false;

    const now = new Date().getTime();
    const timeUntilExpiry = expTime - now;
    const thresholdMs = TOKEN_REFRESH_THRESHOLD * 1000;

    return timeUntilExpiry < thresholdMs && timeUntilExpiry > 0;
  },

  // Helper: Check if token is expired
  isTokenExpired(token) {
    const expTime = this.getTokenExpiration(token);
    if (!expTime) return true;

    const now = new Date().getTime();
    return expTime <= now;
  },
};
