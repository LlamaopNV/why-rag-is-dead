import { type TokenStats, totalNexus, fmtTokens } from '../types/events'
import type { BenchmarkResult } from '../types/events'

interface Props {
  stats: TokenStats
  benchmark: BenchmarkResult | null
  nexusTimeMs: number
  isBenchmarkRunning: boolean
}

interface BarProps {
  label: string
  sublabel?: string
  tokens: number
  max: number
  color: string
  labelColor: string
}

function Bar({ label, sublabel, tokens, max, color, labelColor }: BarProps) {
  const pct = max > 0 ? Math.min(100, (tokens / max) * 100) : 0
  return (
    <div className="mb-2.5">
      <div className="flex justify-between items-baseline text-xs mb-1">
        <span className={`font-semibold ${labelColor}`}>
          {label}
          {sublabel && <span className="text-zinc-600 font-normal ml-1.5">{sublabel}</span>}
        </span>
        <span className="text-zinc-300 tabular-nums">{fmtTokens(tokens)}</span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${color}`}
          style={{ width: `${Math.max(pct, tokens > 0 ? 2 : 0)}%` }}
        />
      </div>
    </div>
  )
}

export function ContextBudget({ stats, benchmark, nexusTimeMs, isBenchmarkRunning }: Props) {
  const nexus = totalNexus(stats)
  const max   = benchmark ? Math.max(benchmark.tokens, nexus, 1) : Math.max(nexus, 1)

  const savingsPct = benchmark && nexus > 0
    ? Math.max(0, (1 - nexus / benchmark.tokens) * 100)
    : null

  const nexusTimeSec = nexusTimeMs > 0 ? (nexusTimeMs / 1000).toFixed(1) : null

  return (
    <div className="px-4 pt-4 pb-3 border-b border-zinc-800 flex-shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase">
          Context Budget
        </span>
        {savingsPct !== null && (
          <span className="text-lg font-bold text-green-400 tabular-nums">
            {savingsPct.toFixed(1)}% saved
          </span>
        )}
      </div>

      {/* Claude Code CLI bar */}
      {benchmark ? (
        <Bar
          label="Claude Code CLI"
          sublabel={`${benchmark.toolCalls} tools · ${benchmark.timeSeconds}s`}
          tokens={benchmark.tokens}
          max={max}
          color="bg-zinc-500"
          labelColor="text-zinc-400"
        />
      ) : isBenchmarkRunning ? (
        <div className="mb-2.5">
          <div className="flex justify-between items-baseline text-xs mb-1">
            <span className="font-semibold text-sky-400 flex items-center gap-1.5">
              Claude Code CLI
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse inline-block" />
            </span>
            <span className="text-zinc-600 text-[10px]">running…</span>
          </div>
          <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div className="h-full bg-sky-700/60 rounded-full animate-pulse w-full" />
          </div>
        </div>
      ) : (
        <div className="text-[10px] text-zinc-700 mb-2.5 italic">
          Hit ⚡ Race to compare against Claude Code CLI
        </div>
      )}

      {/* NEXUS bar */}
      <Bar
        label="NEXUS"
        sublabel={nexusTimeSec ? `${nexusTimeSec}s` : undefined}
        tokens={nexus}
        max={max}
        color={savingsPct !== null ? "bg-green-500" : "bg-blue-500"}
        labelColor={savingsPct !== null ? "text-green-400" : "text-blue-400"}
      />

      {/* Per-agent breakdown */}
      <div className="grid grid-cols-4 gap-1 mt-3 text-[10px] text-zinc-600">
        <div>
          <span className="block text-purple-500">Planner</span>
          <span className="text-zinc-400 tabular-nums">
            {fmtTokens(stats.planner_in + stats.planner_out)}
          </span>
        </div>
        <div>
          <span className="block text-yellow-600">Workers</span>
          <span className="text-zinc-400 tabular-nums">
            {fmtTokens(stats.worker_in + stats.worker_out)}
          </span>
        </div>
        <div>
          <span className="block text-cyan-700">Manager</span>
          <span className="text-zinc-400 tabular-nums">
            {fmtTokens(stats.manager_in + stats.manager_out)}
          </span>
        </div>
        <div>
          <span className="block text-blue-600">Claude</span>
          <span className="text-zinc-400 tabular-nums">
            {fmtTokens(stats.main_in + stats.main_out)}
          </span>
        </div>
      </div>

      {/* Comparison summary row */}
      {benchmark && savingsPct !== null && (
        <div className="mt-3 pt-2 border-t border-zinc-800 text-[10px] text-zinc-500 flex justify-between">
          <span>
            Claude Code: <span className="text-zinc-400">{fmtTokens(benchmark.tokens)}</span>
          </span>
          <span>
            NEXUS: <span className="text-green-400">{fmtTokens(nexus)}</span>
          </span>
          <span>
            Saved: <span className="text-green-400">{fmtTokens(benchmark.tokens - nexus)}</span>
          </span>
        </div>
      )}
    </div>
  )
}
