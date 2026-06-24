import { useEffect, useRef, useState } from 'react'
import type { BenchmarkResult } from '../types/events'
import { fmtTokens } from '../types/events'

interface Props {
  isRunning: boolean
  currentTool: string       // last tool call seen
  toolCount: number
  startedAt: number         // Date.now() when benchmark started
  result: BenchmarkResult | null
  response: string          // streamed text from Claude Code CLI
}

export function BenchmarkStatus({ isRunning, currentTool, toolCount, startedAt, result, response }: Props) {
  const [elapsed, setElapsed] = useState(0)
  const [expanded, setExpanded] = useState(false)
  const responseRef = useRef<HTMLDivElement>(null)

  // Tick elapsed timer while running
  useEffect(() => {
    if (!isRunning || startedAt === 0) return
    const id = setInterval(() => setElapsed(Math.round((Date.now() - startedAt) / 1000)), 500)
    return () => clearInterval(id)
  }, [isRunning, startedAt])

  // Auto-scroll benchmark response
  useEffect(() => {
    if (responseRef.current) responseRef.current.scrollTop = responseRef.current.scrollHeight
  }, [response])

  // Auto-expand when response starts coming in
  useEffect(() => {
    if (response) setExpanded(true)
  }, [!!response])

  const visible = isRunning || result !== null
  if (!visible) return null

  return (
    <div className="border-b border-zinc-800 flex-shrink-0">
      {/* Header row */}
      <div
        className="flex items-center gap-2 px-4 py-2 cursor-pointer hover:bg-zinc-900/40 select-none"
        onClick={() => setExpanded((e) => !e)}
      >
        <span className={`text-[10px] font-bold tracking-widest uppercase ${isRunning ? 'text-sky-400' : 'text-zinc-500'}`}>
          Claude Code CLI
        </span>
        {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse flex-shrink-0" />}

        <span className="text-[10px] text-zinc-600 flex-1 truncate ml-1 font-mono">
          {isRunning && currentTool ? currentTool : (result ? 'done' : '')}
        </span>

        <div className="flex items-center gap-2 text-[10px] text-zinc-600 flex-shrink-0">
          {toolCount > 0 && <span>{toolCount} tools</span>}
          {isRunning  && <span className="text-sky-600 tabular-nums">{elapsed}s</span>}
          {result     && <span className="text-zinc-500 tabular-nums">{fmtTokens(result.tokens)} tok · {result.timeSeconds}s</span>}
          <span className={`ml-1 transition-transform ${expanded ? 'rotate-180' : ''}`}>▾</span>
        </div>
      </div>

      {/* Expandable response area */}
      {expanded && (
        <div
          ref={responseRef}
          className="px-4 pb-3 max-h-48 overflow-y-auto font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed border-t border-zinc-800/60"
        >
          {response ? (
            <>
              {response}
              {isRunning && <span className="inline-block w-1.5 h-3 bg-sky-400 ml-0.5 align-middle animate-pulse" />}
            </>
          ) : (
            <span className="text-zinc-700 italic">Waiting for response…</span>
          )}
        </div>
      )}
    </div>
  )
}
