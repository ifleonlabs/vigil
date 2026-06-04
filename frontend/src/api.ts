import type { Monitor, MonitorInput, Token } from './types'

const TOKEN_KEY = 'vigil_token'
const USER_KEY = 'vigil_user'

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY) },
  get username() { return localStorage.getItem(USER_KEY) },
  set(t: Token) { localStorage.setItem(TOKEN_KEY, t.access_token); localStorage.setItem(USER_KEY, t.username) },
  clear() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY) },
}

/** Thrown on any non-2xx response (or 401 -> session expired). */
export class ApiError extends Error {}

let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn }

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(opts.headers as Record<string, string>) }
  const token = auth.token
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(path, { ...opts, headers })
  if (res.status === 401) {
    auth.clear()
    onUnauthorized()
    throw new ApiError('Session expired — please sign in.')
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({})) as { detail?: string }
    throw new ApiError(detail.detail || `Request failed (${res.status})`)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

export const api = {
  register: (username: string, password: string) =>
    request<Token>('/api/register', { method: 'POST', body: JSON.stringify({ username, password }) }),
  login: (username: string, password: string) =>
    request<Token>('/api/login', { method: 'POST', body: JSON.stringify({ username, password }) }),

  listMonitors: () => request<Monitor[]>('/api/monitors'),
  createMonitor: (input: MonitorInput) =>
    request<Monitor>('/api/monitors', { method: 'POST', body: JSON.stringify(input) }),
  updateMonitor: (id: number, patch: Partial<Monitor>) =>
    request<Monitor>(`/api/monitors/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  deleteMonitor: (id: number) => request<void>(`/api/monitors/${id}`, { method: 'DELETE' }),
  checkNow: (id: number) => request(`/api/monitors/${id}/check`, { method: 'POST' }),
}
