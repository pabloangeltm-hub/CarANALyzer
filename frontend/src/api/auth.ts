import {
  apiClient,
  clearAuthTokens,
  requestTokenRefresh,
  setAuthTokens,
} from '@/api/client'
import type {
  APIKeyCreate,
  APIKeyResponse,
  LoginRequest,
  TokenResponse,
} from '@/types/api'

export async function login(payload: LoginRequest) {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', payload)
  setAuthTokens(data)
  return data
}

export async function refreshSession(refreshToken: string) {
  return requestTokenRefresh(refreshToken)
}

export async function logout() {
  try {
    await apiClient.post('/auth/logout')
  } finally {
    clearAuthTokens()
  }
}

export async function createApiKey(payload: APIKeyCreate) {
  const { data } = await apiClient.post<APIKeyResponse>('/auth/api-key', payload)
  return data
}
