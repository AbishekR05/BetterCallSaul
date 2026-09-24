// frontend/src/api/client.ts

export interface ApiErrorPayload {
  error_code?: string;
  message?: string;
  detail?: string | any[];
  request_id?: string;
}

export class ApiError extends Error {
  public errorCode: string;
  public requestId: string;
  public status: number;
  public retryAfterSeconds?: number;

  constructor(status: number, payload: ApiErrorPayload, retryAfter?: number) {
    let msg = payload.message;
    if (!msg && payload.detail) {
      if (Array.isArray(payload.detail)) {
        msg = payload.detail.map((d: any) => `${d.loc ? d.loc.join('.') + ': ' : ''}${d.msg || JSON.stringify(d)}`).join('; ');
      } else {
        msg = String(payload.detail);
      }
    }
    super(msg || `API Error: ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.errorCode = payload.error_code || (status === 401 ? 'unauthenticated' : status === 422 ? 'validation_error' : 'internal_error');
    this.requestId = payload.request_id || 'unknown';
    this.retryAfterSeconds = retryAfter;
  }
}

const TOKEN_KEY = 'bcs_auth_token';

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});

  // 1. Attach Content-Type for JSON mutations
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // 2. Attach Authorization token if available (§8)
  const token = getStoredToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // 3. Attach X-Request-ID for client tracing (§8)
  if (!headers.has('X-Request-ID')) {
    headers.set('X-Request-ID', `req_${Math.random().toString(36).substring(2, 10)}`);
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  let data: any = {};
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  }

  if (!response.ok) {
    // Extract Retry-After header if present
    const retryHeader = response.headers.get('Retry-After');
    const retryAfter = retryHeader ? parseInt(retryHeader, 10) : undefined;

    throw new ApiError(response.status, data as ApiErrorPayload, retryAfter);
  }

  return data as T;
}
