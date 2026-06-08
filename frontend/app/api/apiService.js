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

  // Public (unauthenticated) estate list for the signup estate selector
  async getPublicEstates() {
    const response = await fetch(`${API_BASE}/estates/public`);
    if (!response.ok) throw new Error('Failed to load estates');
    return await response.json();
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
