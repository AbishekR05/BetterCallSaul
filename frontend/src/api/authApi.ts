// frontend/src/api/authApi.ts
import { fetchApi } from './client';

export interface RegisterRequest {
  auth_identifier: string;
  password: string;
}

export interface RegisterResponse {
  user_id: string;
  auth_identifier: string;
  created_at_utc: string;
}

export interface LoginRequest {
  auth_identifier: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  expires_at_utc: string;
  token_type: string;
}

export const authApi = {
  register: (data: RegisterRequest): Promise<RegisterResponse> => {
    return fetchApi<RegisterResponse>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  login: (data: LoginRequest): Promise<LoginResponse> => {
    return fetchApi<LoginResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  logout: (): Promise<void> => {
    return fetchApi<void>('/api/v1/auth/logout', {
      method: 'POST',
    });
  },
};
