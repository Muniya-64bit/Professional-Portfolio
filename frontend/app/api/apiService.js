/**
 * API service for backend communication with token handling
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

// Token refresh threshold (refresh if expires in less than 1 hour)
const TOKEN_REFRESH_THRESHOLD = 3600; // 1 hour in seconds

export const apiService = {
  // Auth endpoints
  async signup(email, password, fullName) {
    try {
      const response = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
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
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
    return json;
  },

  getEstates(token) {
    return this._labour(token, 'GET', '/estates');
  },

  getLabourPlans(token, { estateId, weekStart } = {}) {
    const q = new URLSearchParams();
    if (estateId)  q.set('estate_id',  estateId);
    if (weekStart) q.set('week_start', weekStart);
    return this._labour(token, 'GET', `/plans${q.toString() ? '?' + q : ''}`);
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

  overrideAssignment(token, assignmentId, data) {
    return this._labour(token, 'PUT', `/assignments/${assignmentId}`, data);
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


  // ── Water Efficiency ──────────────────────────────────────────────────────

  async _water(token, method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}/water${path}`, opts);
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

      // Decode the payload (second part)
      const decoded = JSON.parse(atob(parts[1]));
      return decoded.exp ? decoded.exp * 1000 : null; // Convert to milliseconds
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
