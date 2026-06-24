import { useEffect, useRef, useState } from 'react'

interface Props {
  response: string
  benchmarkResponse: string
  isRunning: boolean
  isBenchmarkRunning: boolean
  claudeCliAvailable: boolean
  error: string | null
  benchmarkResult: { tokens: number; timeSeconds: number } | null
  onQuery: (query: string) => void
  onRace: (query: string) => void
  onClear: () => void
}

const DEMO_QUERIES = [
  'Which graph traversal algorithms are implemented, and how do they handle cycle detection?',
  'How does binary search work in this codebase?',
  'Find all sorting algorithm implementations and compare their approaches.',
  'How is recursion used in tree traversal?',
]

export function ChatPanel({
  response, benchmarkResponse, isRunning, isBenchmarkRunning,
  claudeCliAvailable, error, benchmarkResult, onQuery, onRace, onClear,
}: Props) {
  const [query, setQuery] = useState('')
  const nexusRef     = useRef<HTMLDivElement>(null)
  const benchRef     = useRef<HTMLDivElement>(null)
  const busy         = isRunning || isBenchmarkRunning

  // Show the split view whenever a race is active or has completed
  const showSplit = isBenchmarkRunning || benchmarkResponse !== '' || benchmarkResult !== null

  useEffect(() => {
    if (nexusRef.current) nexusRef.current.scrollTop = nexusRef.current.scrollHeight
  }, [response])

  useEffect(() => {
    if (benchRef.current) benchRef.current.scrollTop = benchRef.current.scrollHeight
  }, [benchmarkResponse])

  const submit = () => { if (query.trim() && !busy) onQuery(query.trim()) }
  const race   = () => { if (query.trim() && !busy) onRace(query.trim()) }

  return (
    <div className="flex flex-col w-[42%] border-r border-zinc-800 overflow-hidden">

      {/* ── NEXUS response ────────────────────────────────────────────── */}
      <div className={`flex flex-col overflow-hidden min-h-0 ${showSplit ? 'flex-1 border-b border-zinc-800' : 'flex-1'}`}>
        {showSplit && (
          <div className="px-4 py-1.5 flex-shrink-0 border-b border-zinc-800/60 flex items-center gap-2">
            <span className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase">NEXUS</span>
            {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />}
          </div>
        )}

        <div ref={nexusRef} className="flex-1 overflow-y-auto p-4">
          {!response && !error && !isRunning && !showSplit && (
            <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
              <div>
                <div className="text-4xl font-bold tracking-widest text-white mb-1">NEXUS</div>
                <div className="text-xs text-zinc-600">verified multi-agent code search</div>
              </div>
              <div className="w-full max-w-xs space-y-1.5">
                {DEMO_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => setQuery(q)}
                    className="w-full text-left text-xs text-zinc-500 hover:text-zinc-300 px-3 py-1.5 rounded border border-zinc-800 hover:border-zinc-700 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="text-red-400 text-sm p-3 rounded border border-red-900 bg-red-950/30 font-mono">
              ✗ {error}
            </div>
          )}

          {(response || isRunning) && (
            <div className="text-zinc-100 text-sm leading-relaxed font-mono whitespace-pre-wrap">
              {response}
              {isRunning && !response && <span className="text-zinc-600">Waiting for response…</span>}
              {isRunning && response && (
                <span className="inline-block w-2 h-4 bg-zinc-400 ml-0.5 align-middle animate-pulse" />
              )}
            </div>
          )}

          {!response && !error && !isRunning && showSplit && (
            <span className="text-zinc-700 text-xs">No NEXUS response yet</span>
          )}
        </div>
      </div>

      {/* ── Claude Code CLI response ──────────────────────────────────── */}
      {showSplit && (
        <div className="flex flex-col flex-1 overflow-hidden min-h-0">
          <div className="px-4 py-1.5 flex-shrink-0 border-b border-zinc-800/60 flex items-center gap-2">
            <span className="text-[10px] font-bold tracking-widest text-sky-500 uppercase">
              Claude Code CLI
            </span>
            {isBenchmarkRunning && (
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
            )}
            {benchmarkResult && (
              <span className="text-[10px] text-zinc-600 ml-auto">
                {benchmarkResult.tokens.toLocaleString()} tok · {benchmarkResult.timeSeconds}s
              </span>
            )}
          </div>

          <div ref={benchRef} className="flex-1 overflow-y-auto p-4">
            {benchmarkResponse ? (
              <div className="text-zinc-200 text-sm leading-relaxed font-mono whitespace-pre-wrap">
                {benchmarkResponse}
                {isBenchmarkRunning && (
                  <span className="inline-block w-2 h-4 bg-sky-400 ml-0.5 align-middle animate-pulse" />
                )}
              </div>
            ) : (
              <span className="text-zinc-700 text-xs italic">
                {isBenchmarkRunning ? 'Claude Code CLI is working…' : 'No response'}
              </span>
            )}
          </div>
        </div>
      )}

      {/* ── Input ─────────────────────────────────────────────────────── */}
      <div className="border-t border-zinc-800 p-3 flex-shrink-0">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit() }}
          placeholder="Ask about the codebase…   Ctrl+Enter to run"
          disabled={busy}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-md p-2.5 text-sm text-zinc-100 placeholder-zinc-600 resize-none focus:outline-none focus:border-zinc-500 disabled:opacity-40 font-mono"
          rows={2}
        />

        <div className="flex items-center justify-between mt-2 gap-2">
          <div>
            {(response || error) && !busy && (
              <button onClick={onClear} className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">
                Clear
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <div className="relative group">
              <button
                onClick={race}
                disabled={busy || !query.trim() || !claudeCliAvailable}
                className="px-3 py-1.5 text-xs bg-sky-900 hover:bg-sky-800 disabled:bg-zinc-800 disabled:text-zinc-600 rounded font-medium transition-colors border border-sky-700 disabled:border-zinc-700"
                title={!claudeCliAvailable ? 'Install Claude Code CLI: npm i -g @anthropic-ai/claude-code' : undefined}
              >
                {isBenchmarkRunning ? 'Racing…' : '⚡ Race'}
              </button>
              {claudeCliAvailable && (
                <div className="absolute bottom-full right-0 mb-1 hidden group-hover:block text-[10px] text-zinc-500 bg-zinc-900 border border-zinc-800 rounded px-2 py-1 whitespace-nowrap z-10">
                  ⚠ Costs API tokens (runs NEXUS + Claude Code CLI)
                </div>
              )}
            </div>

            <button
              onClick={submit}
              disabled={busy || !query.trim()}
              className="px-4 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 rounded font-medium transition-colors"
            >
              {isRunning ? 'Running…' : 'Run NEXUS →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
