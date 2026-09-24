import React, { createContext, useContext, useState } from 'react';
import { getStoredToken, setStoredToken, clearStoredToken } from '../api/client';
import { authApi, LoginRequest, RegisterRequest } from '../api/authApi';

interface User {
  username: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  userIdentifier: string | null;
  token: string | null;
  error: string | null;
  clearError: () => void;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (credentials: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [userIdentifier, setUserIdentifier] = useState<string | null>(
    sessionStorage.getItem('bcs_user_id')
  );
  const [error, setError] = useState<string | null>(null);

  const isAuthenticated = Boolean(token);
  const user: User | null = userIdentifier ? { username: userIdentifier } : null;

  const clearError = () => setError(null);

  const login = async (credentials: LoginRequest) => {
    setError(null);
    try {
      const res = await authApi.login({
        auth_identifier: credentials.auth_identifier || (credentials as any).username,
        password: credentials.password,
      });
      const newToken = res.access_token;
      const identifier = credentials.auth_identifier || (credentials as any).username;
      
      setStoredToken(newToken);
      sessionStorage.setItem('bcs_user_id', identifier);
      setToken(newToken);
      setUserIdentifier(identifier);
    } catch (err: any) {
      setError(err.message || 'Login failed');
      throw err;
    }
  };

  const register = async (credentials: RegisterRequest) => {
    setError(null);
    try {
      const identifier = credentials.auth_identifier || (credentials as any).username;
      await authApi.register({
        auth_identifier: identifier,
        password: credentials.password,
      });
      // Automatically log in after registration
      await login(credentials as any);
    } catch (err: any) {
      setError(err.message || 'Registration failed');
      throw err;
    }
  };

  const logout = async () => {
    try {
      if (token) {
        await authApi.logout();
      }
    } catch {
      // Ignore API logout errors and proceed with client state cleanup
    } finally {
      clearStoredToken();
      sessionStorage.removeItem('bcs_user_id');
      setToken(null);
      setUserIdentifier(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        userIdentifier,
        token,
        error,
        clearError,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
