export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
export const API_BASE = `${API_URL}/api/v1`
export const USE_MOCK = import.meta.env.VITE_API_MOCK === 'true'

const TOKEN_KEY = 'baribhara.token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  status: number
  fieldErrors: Record<string, string>

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

type Query = Record<string, string | number | boolean | null | undefined>

export interface RequestOptions {
  query?: Query
  body?: unknown
  auth?: boolean
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

function cleanQuery(query?: Query) {
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== '') out[k] = String(v)
  }
  return out
}

/**
 * Normalises the error bodies FastAPI can produce:
 *  - {"detail": "Not found"}
 *  - {"detail": [{"loc": [...], "msg": "..."}]}       (422 validation)
 *  - {"error": {"code": "...", "message": "..."}}     (custom handlers)
 *  - {"message": "..."}
 */
function parseError(status: number, body: unknown): ApiError {
  const fallback = status >= 500 ? 'The server had a problem. Please try again.' : `Request failed (${status})`
  if (!body || typeof body !== 'object') return new ApiError(status, fallback)
  const b = body as Record<string, unknown>

  if (Array.isArray(b.detail)) {
    const fieldErrors: Record<string, string> = {}
    for (const item of b.detail as { loc?: unknown[]; msg?: string }[]) {
      const field = item.loc?.filter((p) => p !== 'body').join('.') ?? ''
      if (field && item.msg) fieldErrors[field] = item.msg
    }
    const first = Object.entries(fieldErrors)[0]
    return new ApiError(status, first ? `${first[0]}: ${first[1]}` : 'Some fields are invalid.', fieldErrors)
  }
  if (typeof b.detail === 'string') return new ApiError(status, b.detail)
  if (b.error && typeof b.error === 'object' && typeof (b.error as Record<string, unknown>).message === 'string') {
    return new ApiError(status, (b.error as { message: string }).message)
  }
  if (typeof b.message === 'string') return new ApiError(status, b.message)
  return new ApiError(status, fallback)
}

export async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const token = opts.auth === false ? null : tokenStore.get()
  const query = cleanQuery(opts.query)

  try {
    if (USE_MOCK) {
      // Loaded on demand so the mock data never ships in a real build
      const { mockRequest } = await import('@/lib/mock/server')
      return await mockRequest<T>(method, path, { query, body: opts.body, token })
    }

    const qs = new URLSearchParams(query).toString()
    let res: Response
    try {
      res = await fetch(`${API_BASE}${path}${qs ? `?${qs}` : ''}`, {
        method,
        headers: {
          ...(opts.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      })
    } catch {
      throw new ApiError(0, `Cannot reach the server at ${API_URL}. Is the backend running?`)
    }

    if (res.status === 204) return undefined as T
    const text = await res.text()
    const data = text ? safeJson(text) : null
    if (!res.ok) throw parseError(res.status, data)
    return data as T
  } catch (err) {
    if (err instanceof ApiError && err.status === 401 && token) onUnauthorized?.()
    throw err
  }
}

function safeJson(text: string) {
  try {
    return JSON.parse(text)
  } catch {
    return { message: text }
  }
}

export const http = {
  get: <T>(path: string, query?: Query) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'body'>) => request<T>('POST', path, { ...opts, body }),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, { body }),
  delete: (path: string) => request<void>('DELETE', path),
}
