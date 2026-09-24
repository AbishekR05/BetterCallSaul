import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchApi, ApiError, setStoredToken, getStoredToken, clearStoredToken } from '../api/client';

describe('API Client Layer', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('injects Bearer token into Authorization header when available', async () => {
    setStoredToken('mock_jwt_token_123');

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ status: 'ok' })
    });
    global.fetch = mockFetch;

    await fetchApi('/api/v1/health');

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/health',
      expect.objectContaining({
        headers: expect.any(Headers)
      })
    );

    const actualHeaders: Headers = mockFetch.mock.calls[0][1].headers;
    expect(actualHeaders.get('Authorization')).toBe('Bearer mock_jwt_token_123');
  });

  it('handles stored token utilities cleanly', () => {
    setStoredToken('test_token');
    expect(getStoredToken()).toBe('test_token');
    clearStoredToken();
    expect(getStoredToken()).toBeNull();
  });

  it('throws ApiError with status and payload details on HTTP error response', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      statusText: 'Too Many Requests',
      headers: new Headers({ 'content-type': 'application/json', 'Retry-After': '60' }),
      json: async () => ({ error_code: 'rate_limited', message: 'Rate limit exceeded. Wait 60s.' })
    });
    global.fetch = mockFetch;

    try {
      await fetchApi('/api/v1/turns');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(429);
      expect(err.message).toBe('Rate limit exceeded. Wait 60s.');
      expect(err.retryAfterSeconds).toBe(60);
    }
  });
});
