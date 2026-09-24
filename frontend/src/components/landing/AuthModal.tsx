import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import './AuthModal.css';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: 'login' | 'register';
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, initialMode = 'login' }) => {
  const { login, register, error, clearError } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!username.trim() || !password.trim()) {
      setLocalError('Please enter both username and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login({ auth_identifier: username, password });
      } else {
        await register({ auth_identifier: username, password });
      }
      onClose();
    } catch (err: any) {
      setLocalError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleMode = () => {
    setMode(mode === 'login' ? 'register' : 'login');
    setLocalError(null);
    clearError();
  };

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <button className="auth-close-btn" onClick={onClose} aria-label="Close modal">
          ✕
        </button>

        <div className="auth-header">
          <div className="auth-icon">⚖️</div>
          <h2 className="auth-title">
            {mode === 'login' ? 'Sign In to Workspace' : 'Create Legal Account'}
          </h2>
          <p className="auth-subtitle">
            {mode === 'login' 
              ? 'Access statutory queries, session history, and citations' 
              : 'Register to access Indian Penal Code & BNS search workspace'}
          </p>
        </div>

        {(localError || error) && (
          <div className="auth-error">
            ⚠️ {localError || error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="auth-username">Username / Identifier</label>
            <input
              id="auth-username"
              type="text"
              className="form-control"
              placeholder="e.g. counsel_sharma"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isSubmitting}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              className="form-control"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <button 
            type="submit" 
            className="btn btn-primary auth-submit-btn" 
            disabled={isSubmitting}
          >
            {isSubmitting 
              ? 'Authenticating...' 
              : mode === 'login' ? 'Sign In →' : 'Register Account →'}
          </button>
        </form>

        <div className="auth-footer">
          <span>
            {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}
          </span>
          <button type="button" className="auth-toggle-btn" onClick={toggleMode}>
            {mode === 'login' ? 'Register here' : 'Sign in here'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthModal;
