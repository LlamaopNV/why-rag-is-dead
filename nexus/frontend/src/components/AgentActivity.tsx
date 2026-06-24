import { useEffect, useRef } from 'react'
import type { NexusEvent } from '../types/events'

// ── Event display config ──────────────────────────────────────────────────────

interface EvStyle { icon: string; color: string; indent?: boolean }

const STYLES: Partial<Record<string, EvStyle>> = {
  // Planner
  'planner.start':      { icon: '◌', color: 'text-purple-400' },
  'planner.done':       { icon: '◉', color: 'text-purple-400' },
  // Workers
  'worker.spawn':       { icon: '⚡', color: 'text-yellow-400' },
  'worker.command':     { icon: '›',  color: 'text-zinc-500',   indent: true },
  'worker.result':      { icon: '✓',  color: 'text-green-400',  indent: true },
  'worker.failed':      { icon: '✗',  color: 'text-red-400',    indent: true },
  'worker.timeout':     { icon: '⏱', color: 'text-red-400',    indent: true },
  'worker.killed':      { icon: '✗',  color: 'text-red-500',    indent: true },
  // Manager
  'manager.verify':            { icon: '◌', color: 'text-cyan-400' },
  'manager.verify_ok':         { icon: '✓',  color: 'text-green-500', indent: true },
  'manager.verify_fail':       { icon: '–',  color: 'text-zinc-700',  indent: true },
  'manager.relevance_filter':  { icon: '◈',  color: 'text-orange-400' },
  'manager.package':           { icon: '◉', color: 'text-cyan-400' },
  // Main LLM
  'main_llm.start':     { icon: '◌', color: 'text-blue-400' },
  'main_llm.done':      { icon: '◉', color: 'text-blue-400' },
  // Session
  'session.done':       { icon: '★',  color: 'text-green-400' },
  'system.error':       { icon: '✗',  color: 'text-red-500' },
  // Benchmark — distinct blue for Claude Code CLI events
  'benchmark.started':  { icon: '◌', color: 'text-sky-400' },
  'benchmark.progress': { icon: '›',  color: 'text-sky-600',  indent: true },
  'benchmark.complete': { icon: '◉', color: 'text-sky-400' },
  'benchmark.timeout':  { icon: '⏱', color: 'text-red-400' },
  'benchmark.error':    { icon: '✗',  color: 'text-red-400' },
}

const SILENT = new Set(['main_llm.stream', 'token.update', 'benchmark.stream'])

function label(event: NexusEvent): string {
  const d = event.data
  switch (event.type) {
    case 'planner.start':       return `Planner: analyzing query…`
    case 'planner.done':        return `Planner: ${d.task_count} tasks  ↑${d.tok_in} ↓${d.tok_out}`
    case 'worker.spawn':        return `Worker [${d.task_id}]  ${d.description}`
    case 'worker.command':      return `${d.command}  (${d.output_lines} lines)`
    case 'worker.result':       return `${(d.citations as string[])?.length ?? 0} citations  ↑${d.tok_in} ↓${d.tok_out}`
    case 'worker.failed':       return `failed: ${d.error}`
    case 'worker.timeout':      return `timeout`
    case 'worker.killed':       return `killed`
    case 'manager.verify':      return `Manager: verifying ${d.total_citations} citations…`
    case 'manager.verify_ok':   return `${d.citation}`
    case 'manager.verify_fail': return `${d.citation}  (${d.reason})`
    case 'manager.relevance_filter': {
      if (d.status === 'started')      return `7B filter: scoring ${d.total_facts} verified facts…`
      if (d.status === 'complete')     return `7B filter: ${d.kept} relevant · ${d.dropped} dropped  ↑${d.tok_in} ↓${d.tok_out}`
      if (d.status === 'parse_failed') return `7B filter: parse failed — keeping all`
      return `7B filter: ${d.status}${d.error ? ` — ${d.error}` : ''}`
    }
    case 'manager.package':     return `${d.verified} verified · ${d.dropped} dropped · ~${d.token_estimate} tok`
    case 'main_llm.start':      return `Claude: ${d.context_facts} facts · ~${d.context_tokens} tok`
    case 'main_llm.done':       return `Claude: response complete`
    case 'session.done':        return `NEXUS done · ${d.nexus_total?.toLocaleString()} tokens`
    case 'system.error':        return `${d.error}`

    // ── Benchmark events ───────────────────────────────────────────────────
    case 'benchmark.started':   return `Claude Code CLI: starting…`
    case 'benchmark.progress': {
      const t = d.type as string
      if (t === 'tool_use')    return `${d.tool_name}  ${d.preview ?? ''}`
      if (t === 'tool_result') return `↩ result`
      return ''
    }
    case 'benchmark.complete':
      return `Claude Code CLI done · ${(d.tokens as number)?.toLocaleString()} tok · ${d.tool_calls} tools · ${d.time_seconds}s${d.cost_usd ? ` · $${(d.cost_usd as number).toFixed(4)}` : ''}`
    case 'benchmark.timeout':   return `Claude Code CLI: timed out`
    case 'benchmark.error':     return `Claude Code CLI: ${d.error}`

    default: return event.type
  }
}

function elapsed(ts: number, start: number): string {
  if (start === 0) return ''
  const ms = Math.round((ts - start) * 1000)
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  events: NexusEvent[]
  isRunning: boolean
}

export function AgentActivity({ events, isRunning }: Props) {
  const endRef  = useRef<HTMLDivElement>(null)
  const visible = events.filter((e) => !SILENT.has(e.type))
  const startTs = visible[0]?.timestamp ?? 0

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [visible.length])

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0">
      <div className="px-4 py-2 border-b border-zinc-800 flex items-center gap-2 flex-shrink-0">
        <span className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase">
          Agent Activity
        </span>
        {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />}
        <span className="ml-auto text-[10px] text-zinc-700">{visible.length} events</span>
      </div>

      <div className="flex-1 overflow-y-auto py-1 font-mono text-xs">
        {visible.length === 0 && (
          <div className="text-zinc-700 text-center py-8 text-[11px]">
            Submit a query to watch agents work…
          </div>
        )}

        {visible.map((event, i) => {
          const s = STYLES[event.type]
          if (!s) return null
          return (
            <div
              key={i}
              className={`flex items-start gap-2 px-3 py-0.5 hover:bg-zinc-900/50 ${s.indent ? 'pl-7' : ''}`}
            >
              <span className={`flex-shrink-0 w-3 ${s.color}`}>{s.icon}</span>
              <span className={`flex-1 break-all ${s.color} opacity-90`}>{label(event)}</span>
              <span className="flex-shrink-0 text-zinc-700 tabular-nums text-[10px]">
                {elapsed(event.timestamp, startTs)}
              </span>
            </div>
          )
        })}

        {isRunning && (
          <div className="flex items-center gap-2 px-3 py-0.5 text-zinc-600">
            <span className="animate-pulse">▸</span>
            <span>processing…</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  )
}
