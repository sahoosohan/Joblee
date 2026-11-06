const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "")

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

const AUTH_TOKEN_KEY = "joblee-token"

export function setAuthToken(token: string | null) {
  if (token) localStorage.setItem(AUTH_TOKEN_KEY, token)
  else localStorage.removeItem(AUTH_TOKEN_KEY)
}

export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken()
  const headers = new Headers(options.headers)
  headers.set("Content-Type", "application/json")
  if (token) headers.set("Authorization", `Bearer ${token}`)
  const response = await fetch(`${API_URL}/api/v1${path}`, {
    ...options,
    headers,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    throw new ApiError(typeof detail === "string" ? detail : "Something went wrong. Please try again.", response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export type Company = { id: number; name: string; website?: string | null; location?: string | null; industry?: string | null; application_count: number }
export type Note = { id: number; application_id: number; content: string; created_at: string }
export type History = { id: number; from_status?: string | null; to_status: string; changed_at: string }
export type Application = {
  id: number; company_id: number; company_name: string; company_website?: string | null; company_industry?: string | null
  job_title: string; status: Stage; applied_date: string; job_url?: string | null; location?: string | null
  work_mode?: string | null; salary_min?: number | null; salary_max?: number | null; source?: string | null
  last_activity_at: string; note_count: number; needs_follow_up: boolean; notes?: Note[]; history?: History[]
  company?: Company
}
export type Stats = { total: number; applied: number; interviews: number; offers: number; rejected: number; response_rate: number; follow_ups_due: number }
export type Stage = "applied" | "interview" | "offer" | "rejected"
