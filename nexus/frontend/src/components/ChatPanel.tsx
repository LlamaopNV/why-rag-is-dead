import { useEffect, useRef, useState } from 'react'

interface Props {
  response: string
  isRunning: boolean
  error: string | null
  onQuery: (query: string, naiveMode: boolean) => void
  onClear: () => void
}

const DEMO_QUERIES = [
  'How does binary search work in this codebase?',
  'Find all sorting algorithm implementations',
  'How is recursion used in tree traversal?',
  'What graph algorithms are implemented?',
]

export function ChatPanel({ response, isRunning, error, onQuery, onClear }: Props) {
  const [query, setQuery]       = useState('')
  const [naiveMode, setNaive]   = useState(true)
  const responseRef             = useRef<HTMLDivElement>(null)
  const textareaRef             = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll response as it streams in
  useEffect(() => {
    if (responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight
    }
  }, [response])

  const submit = () => {
    if (!query.trim() || isRunning) return
    onQuery(query.trim(), naiveMode)
  }

  return (
    <div className="flex flex-col w-[42%] border-r border-zinc-800 overflow-hidden">

      {/* Response area */}
      <div ref={responseRef} className="flex-1 overflow-y-auto p-5">
        {!response && !error && !isRunning && (
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
            {isRunning && !response && (
              <span className="text-zinc-600">Waiting for response...</span>
            )}
            {isRunning && response && (
              <span className="inline-block w-2 h-4 bg-zinc-400 ml-0.5 align-middle animate-pulse" />
            )}
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-zinc-800 p-4 flex-shrink-0">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit() }}
          placeholder="Ask about the codebase...   Ctrl+Enter to run"
          disabled={isRunning}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-md p-3 text-sm text-zinc-100 placeholder-zinc-600 resize-none focus:outline-none focus:border-zinc-500 disabled:opacity-40 font-mono"
          rows={3}
        />

        <div className="flex items-center justify-between mt-2">
          <label className="flex items-center gap-2 text-xs text-zinc-500 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={naiveMode}
              onChange={(e) => setNaive(e.target.checked)}
              className="accent-blue-500"
            />
            Compare naive mode
          </label>

          <div className="flex gap-2">
            {(response || error) && !isRunning && (
              <button
                onClick={onClear}
                className="px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                Clear
              </button>
            )}
            <button
              onClick={submit}
              disabled={isRunning || !query.trim()}
              className="px-4 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 rounded font-medium transition-colors"
            >
              {isRunning ? 'Running…' : 'Run →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
