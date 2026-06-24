// ── Event types — must match backend/models/events.py EventType enum ──────────

export type EventType =
  | 'planner.start'
  | 'planner.done'
  | 'worker.spawn'
  | 'worker.command'
  | 'worker.result'
  | 'worker.failed'
  | 'worker.timeout'
  | 'worker.killed'
  | 'manager.verify'
  | 'manager.verify_ok'
  | 'manager.verify_fail'
  | 'manager.relevance_filter'
  | 'manager.package'
  | 'main_llm.start'
  | 'main_llm.stream'
  | 'main_llm.done'
  | 'token.update'
  | 'system.error'
  | 'session.done'
  | 'benchmark.started'
  | 'benchmark.progress'
  | 'benchmark.stream'
  | 'benchmark.complete'
  | 'benchmark.timeout'
  | 'benchmark.error'

export interface NexusEvent {
  type: EventType
  session_id: string
  timestamp: number          // Unix epoch float (seconds)
  data: Record<string, unknown>
}

// ── Token stats — mirrors backend/models/schemas.py TokenStats ────────────────
// Note: total_nexus and reduction_pct are @property on the Python side and
// NOT in model_dump(). Compute them here with helpers.

export interface TokenStats {
  planner_in: number
  planner_out: number
  worker_in: number
  worker_out: number
  manager_in: number
  manager_out: number
  main_in: number
  main_out: number
  naive_estimate: number
}

export const DEFAULT_STATS: TokenStats = {
  planner_in: 0, planner_out: 0,
  worker_in: 0, worker_out: 0,
  manager_in: 0, manager_out: 0,
  main_in: 0, main_out: 0,
  naive_estimate: 0,
}

export function totalNexus(s: TokenStats): number {
  return (
    s.planner_in + s.planner_out +
    s.worker_in + s.worker_out +
    s.manager_in + s.manager_out +
    s.main_in + s.main_out
  )
}

export function reductionPct(s: TokenStats): number {
  if (s.naive_estimate === 0) return 0
  return Math.max(0, (1 - totalNexus(s) / s.naive_estimate) * 100)
}

export function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString()
}

// ── Typed data accessors for specific events ──────────────────────────────────

export interface PlannerDoneData { task_count: number; tok_in: number; tok_out: number }
export interface WorkerSpawnData  { task_id: string; description: string; command: string }
export interface WorkerCommandData { task_id: string; command: string; output_lines: number }
export interface WorkerResultData  { task_id: string; citations: string[]; tok_in: number; tok_out: number }
export interface WorkerFailedData  { task_id: string; error: string }
export interface ManagerVerifyData { total_citations: number }
export interface ManagerVerifyOkData { citation: string }
export interface ManagerVerifyFailData { citation: string; reason: string }
export interface ManagerPackageData { verified: number; dropped: number; token_estimate: number }
export interface MainLlmStartData  { context_facts: number; context_tokens: number }
export interface MainLlmStreamData { chunk: string }
export interface MainLlmDoneData   { response: string; tokens: TokenStats }
export interface SessionDoneData   { tokens: TokenStats; nexus_total: number; naive_estimate: number; reduction_pct: number }
export interface SystemErrorData   { error: string; trace?: string }

export interface BenchmarkResult {
  tokens: number
  toolCalls: number
  timeSeconds: number
  model?: string
}
