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
