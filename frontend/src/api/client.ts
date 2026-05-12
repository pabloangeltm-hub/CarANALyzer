import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

import type { TokenResponse } from '@/types/api'

const ACCESS_TOKEN_KEY = 'agartha.accessToken'
const REFRESH_TOKEN_KEY = 'agartha.refreshToken'
export const AUTH_CHANGED_EVENT = 'agartha:auth-changed'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

export function getAccessToken() {
  return globalThis.localStorage?.getItem(ACCESS_TOKEN_KEY) ?? null
}

export function getRefreshToken() {
  return globalThis.localStorage?.getItem(REFRESH_TOKEN_KEY) ?? null
}

export function hasAuthTokens() {
  return Boolean(getAccessToken() && getRefreshToken())
}

function notifyAuthChanged() {
  globalThis.dispatchEvent?.(new Event(AUTH_CHANGED_EVENT))
}

export function setAuthTokens(tokens: TokenResponse) {
  globalThis.localStorage?.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
  if (tokens.refresh_token) {
    globalThis.localStorage?.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
  }
  notifyAuthChanged()
}

export function clearAuthTokens() {
  globalThis.localStorage?.removeItem(ACCESS_TOKEN_KEY)
  globalThis.localStorage?.removeItem(REFRESH_TOKEN_KEY)
  notifyAuthChanged()
}

export async function requestTokenRefresh(refreshToken: string) {
  const { data } = await refreshClient.post<TokenResponse>(
    '/auth/refresh',
    undefined,
    { headers: { Authorization: `Bearer ${refreshToken}` } },
  )
  setAuthTokens(data)
  return data
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry
    ) {
      return Promise.reject(error)
    }

    const refreshToken = getRefreshToken()
    if (!refreshToken) {
      clearAuthTokens()
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      const data = await requestTokenRefresh(refreshToken)
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`
      return apiClient(originalRequest)
    } catch (refreshError) {
      clearAuthTokens()
      return Promise.reject(refreshError)
    }
  },
)
