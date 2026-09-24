import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ErrorStateBanner } from '../components/app/ErrorStateBanner';
import { ApiError } from '../api/client';

describe('ErrorStateBanner Component', () => {
  it('renders rate limit 429 error correctly', () => {
    const err = new ApiError(429, { error_code: 'rate_limited', message: 'Query rate limit exceeded. Please wait a moment before submitting another statutory query.' });
    render(<ErrorStateBanner error={err} />);

    expect(screen.getByText('Rate Limit Exceeded (429)')).toBeInTheDocument();
    expect(screen.getByText('Query rate limit exceeded. Please wait a moment before submitting another statutory query.')).toBeInTheDocument();
  });

  it('renders server busy 503 error correctly', () => {
    const err = new ApiError(503, { error_code: 'server_busy', message: 'Server Busy' });
    render(<ErrorStateBanner error={err} />);

    expect(screen.getByText('Server Busy (503)')).toBeInTheDocument();
    expect(
      screen.getByText('Statutory inference engine is currently under high load. Please try again shortly.')
    ).toBeInTheDocument();
  });

  it('renders timeout 504 error correctly', () => {
    const err = new ApiError(504, { error_code: 'upstream_timeout', message: 'Gateway Timeout' });
    render(<ErrorStateBanner error={err} />);

    expect(screen.getByText('Upstream Timeout (504)')).toBeInTheDocument();
    expect(
      screen.getByText('Statutory search timed out while scanning vector corpus. Please refine your query keywords.')
    ).toBeInTheDocument();
  });
});
