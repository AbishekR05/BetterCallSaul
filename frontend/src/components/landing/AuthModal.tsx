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

    const cleanUser = username.trim();
    const cleanPass = password.trim();

    if (!cleanUser || !cleanPass) {
      setLocalError('Please enter both username and password.');
      return;
    }

    if (mode === 'register' && cleanPass.length < 8) {
      setLocalError('Password must be at least 8 characters long.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login({ auth_identifier: cleanUser, password: cleanPass });
      } else {
        await register({ auth_identifier: cleanUser, password: cleanPass });
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
          <svg className="auth-scale-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
            <path d="M12 3v18M4 7h16M4 7l4 8M12 7l-4 8M12 7l4 8M20 7l-4 8M2 15h8M14 15h8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <h2 className="auth-title font-serif">
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
            <span className="error-mark">!</span> {localError || error}
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
            <label htmlFor="auth-password">Password {mode === 'register' && '(min 8 chars)'}</label>
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
