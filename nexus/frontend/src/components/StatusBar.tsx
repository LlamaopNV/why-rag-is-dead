import type { HealthResponse } from '../services/api'

interface Props {
  health: HealthResponse | null
  connected: boolean
  isRunning: boolean
}

export function StatusBar({ health, connected, isRunning }: Props) {
  return (
    <div className="flex items-center justify-between px-4 h-10 border-b border-zinc-800 bg-zinc-950 flex-shrink-0">
      <div className="flex items-center gap-3">
        <span className="text-sm font-bold tracking-widest text-white">NEXUS</span>
        <span className="text-xs text-zinc-600">multi-agent verified code search</span>
      </div>

      <div className="flex items-center gap-4 text-xs">
        {isRunning && (
          <span className="text-yellow-400 flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
            running
          </span>
        )}

        <span className={connected ? 'text-green-400' : 'text-zinc-600'}>
          {connected ? '● ws' : '○ ws'}
        </span>

        {health && (
          <>
            <span className={health.anthropic ? 'text-green-400' : 'text-red-500'}>
              ● anthropic
            </span>
            <span className={health.ollama ? 'text-green-400' : 'text-red-500'}>
              ● ollama
            </span>
            {Object.entries(health.models).map(([model, ok]) => (
              <span key={model} className={ok ? 'text-green-400' : 'text-red-500'}>
                ● {model}
              </span>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
