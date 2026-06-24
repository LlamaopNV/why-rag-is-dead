const BASE = 'http://localhost:8000'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? 'Request failed')
  }
  return res.json() as Promise<T>
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(res.statusText)
  return res.json() as Promise<T>
}

// ── Typed response shapes ────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  anthropic: boolean
  ollama: boolean
  models: Record<string, boolean>
  codebase_indexed: boolean
}

export interface IndexStatusResponse {
  indexed: boolean
  path?: string
  file_count?: number
  total_lines?: number
  naive_token_estimate?: number
}

export interface IndexResponse {
  path: string
  file_count: number
  total_lines: number
  extensions: Record<string, number>
}

export interface QueryResponse {
  session_id: string
  status: string
}

export interface BenchmarkStatusResponse {
  available: boolean
  claude_binary: string | null
}

export interface RaceResponse {
  session_id: string
  status: string
}

// ── API calls ────────────────────────────────────────────────────────────────

export const api = {
  health:          ()                                          => get<HealthResponse>('/api/health'),
  indexStatus:     ()                                          => get<IndexStatusResponse>('/api/index/status'),
  index:           (path: string)                              => post<IndexResponse>('/api/index', { path }),
  benchmarkStatus: ()                                          => get<BenchmarkStatusResponse>('/api/benchmark/status'),

  // NEXUS only
  query: (query: string, session_id: string, naive_mode = false) =>
    post<QueryResponse>('/api/query', { query, session_id, naive_mode }),

  // NEXUS + Claude Code CLI simultaneously
  race: (query: string, session_id: string, codebase_path?: string) =>
    post<RaceResponse>('/api/benchmark/race', { query, session_id, codebase_path }),

  // Manual fallback: enter Claude Code CLI numbers by hand
  manualBenchmark: (tokens_used: number, tool_calls?: number, time_seconds?: number) =>
    post('/api/benchmark/manual', { tokens_used, tool_calls, time_seconds }),
}
