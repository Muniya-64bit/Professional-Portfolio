'use client';

import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { apiService } from '../api/apiService';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const refreshTimeoutRef = useRef(null);

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
      verifyToken(storedToken);
    } else {
      setLoading(false);
    }
  }, []);

  // Set up token auto-refresh
  useEffect(() => {
    if (token) {
      const expTime = apiService.getTokenExpiration(token);
      if (expTime) {
        const now = new Date().getTime();
        const timeUntilRefresh = expTime - now - 3600000; // Refresh 1 hour before expiry

        // Clear any existing timeout
        if (refreshTimeoutRef.current) {
          clearTimeout(refreshTimeoutRef.current);
        }

        // Set new timeout for auto-refresh
        if (timeUntilRefresh > 0) {
          refreshTimeoutRef.current = setTimeout(() => {
            refreshTokenAutomatically();
          }, timeUntilRefresh);
        }
      }
    }

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [token]);

  const refreshTokenAutomatically = async () => {
    try {
      if (token && !apiService.isTokenExpired(token)) {
        const response = await apiService.refreshToken(token);
        const newToken = response.token;
        localStorage.setItem('authToken', newToken);
        setToken(newToken);
        setError(null);
      }
    } catch (err) {
      console.log('Auto-refresh failed, user will need to login again');
      logout();
    }
  };

  const verifyToken = async (tk) => {
    try {
      if (apiService.isTokenExpired(tk)) {
        localStorage.removeItem('authToken');
        setToken(null);
        setUser(null);
        setLoading(false);
        return;
      }

      const response = await apiService.verifyToken(tk);
      setUser(response.user);
      setToken(tk);
      setError(null);
    } catch (err) {
      localStorage.removeItem('authToken');
      setToken(null);
      setUser(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const signup = async (email, password, fullName) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.signup(email, password, fullName);
      const { token: newToken, user: newUser } = response;

      localStorage.setItem('authToken', newToken);
      setToken(newToken);
      setUser(newUser);

      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.login(email, password);
      const { token: newToken, user: newUser } = response;

      localStorage.setItem('authToken', newToken);
      setToken(newToken);
      setUser(newUser);

      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      if (token) {
        await apiService.logout(token);
      }
    } catch (err) {
      console.error('Logout API call failed:', err.message);
    }

    // Clear local state regardless of API result
    localStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
    setError(null);

    // Clear refresh timeout
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }
  };

  const refreshToken = async () => {
    if (!token) return null;

    try {
      const response = await apiService.refreshToken(token);
      const newToken = response.token;
      localStorage.setItem('authToken', newToken);
      setToken(newToken);
      setError(null);
      return newToken;
    } catch (err) {
      setError(err.message);
      logout();
      return null;
    }
  };

  const value = {
    user,
    token,
    loading,
    error,
    signup,
    login,
    logout,
    refreshToken,
    isAuthenticated: !!token && !apiService.isTokenExpired(token || ''),
    isTokenExpired: token ? apiService.isTokenExpired(token) : true,
    shouldRefreshToken: token ? apiService.shouldRefreshToken(token) : false,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
