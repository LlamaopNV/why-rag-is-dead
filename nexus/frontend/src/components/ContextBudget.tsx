import { type TokenStats, DEFAULT_STATS, totalNexus, reductionPct, fmtTokens } from '../types/events'

interface Props {
  stats: TokenStats
}

interface BarProps {
  label: string
  tokens: number
  max: number
  color: string
  labelColor: string
}

function Bar({ label, tokens, max, color, labelColor }: BarProps) {
  const pct = max > 0 ? Math.min(100, (tokens / max) * 100) : 0
  return (
    <div className="mb-2.5">
      <div className="flex justify-between items-baseline text-xs mb-1">
        <span className={`font-semibold ${labelColor}`}>{label}</span>
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

export function ContextBudget({ stats }: Props) {
  const nexus = totalNexus(stats)
  const naive = stats.naive_estimate
  const pct   = reductionPct(stats)

  return (
    <div className="px-4 pt-4 pb-3 border-b border-zinc-800 flex-shrink-0">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase">
          Context Budget
        </span>
        {naive > 0 && (
          <span className="text-lg font-bold text-green-400 tabular-nums">
            {pct.toFixed(1)}% saved
          </span>
        )}
      </div>

      {/* NEXUS bar — fills relative to naive baseline */}
      <Bar
        label="NEXUS"
        tokens={nexus}
        max={naive > 0 ? naive : nexus || 1}
        color="bg-blue-500"
        labelColor="text-blue-400"
      />

      {/* Naive bar — always full when available */}
      <Bar
        label="Naive"
        tokens={naive}
        max={naive || 1}
        color="bg-zinc-600"
        labelColor="text-zinc-500"
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
    </div>
  )
}

export { DEFAULT_STATS }
