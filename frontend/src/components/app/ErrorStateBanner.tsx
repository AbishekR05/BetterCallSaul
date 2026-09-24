import React from 'react';
import { ApiError } from '../../api/client';
import './ErrorStateBanner.css';

interface ErrorStateBannerProps {
  error: ApiError | Error | null;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export const ErrorStateBanner: React.FC<ErrorStateBannerProps> = ({ error, onRetry, onDismiss }) => {
  if (!error) return null;

  let title = 'Statutory System Warning';
  let message = error.message || 'An unexpected error occurred during statutory query execution.';
  let isRateLimit = false;

  if (error instanceof ApiError) {
    switch (error.status) {
      case 429:
        title = 'Rate Limit Exceeded (429)';
        message = error.message || (error.retryAfterSeconds 
          ? `Query rate limit exceeded. Please wait ${error.retryAfterSeconds} seconds.` 
          : 'Query rate limit exceeded. Please wait a moment before submitting another statutory query.');
        isRateLimit = true;
        break;
      case 503:
        title = 'Server Busy (503)';
        message = 'Statutory inference engine is currently under high load. Please try again shortly.';
        break;
      case 504:
        title = 'Upstream Timeout (504)';
        message = 'Statutory search timed out while scanning vector corpus. Please refine your query keywords.';
        break;
      case 409:
        title = 'Session Busy (409)';
        message = 'Another statutory query is active in this session. Please wait for completion.';
        break;
      default:
        title = `API Error (${error.status})`;
        message = error.message;
    }
  }

  return (
    <div className={`error-banner ${isRateLimit ? 'rate-limit' : ''}`}>
      <div className="error-content">
        <span className="error-tag-icon">!</span>
        <div className="error-text">
          <strong className="error-title">{title}</strong>
          <span className="error-desc">{message}</span>
        </div>
      </div>
      <div className="error-actions">
        {onRetry && (
          <button className="btn btn-secondary btn-sm" onClick={onRetry}>
            Retry Query
          </button>
        )}
        {onDismiss && (
          <button className="error-close-btn" onClick={onDismiss} aria-label="Dismiss banner">
            ✕
          </button>
        )}
      </div>
    </div>
  );
};

export default ErrorStateBanner;
