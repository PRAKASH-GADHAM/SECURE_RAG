import { api } from "./api";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export const authService = {
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>("/api/v1/auth/login", data);
    return response.data;
  },

  async register(data: RegisterRequest): Promise<User> {
    const response = await api.post<User>("/api/v1/auth/register", data);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/api/v1/auth/me");
    return response.data;
  },

  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>("/api/v1/auth/refresh", {
      refresh_token: refreshToken,
    });
    return response.data;
  },
};
