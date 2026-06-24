import { useCallback, useEffect, useRef, useState } from 'react'
import { AgentActivity }     from './components/AgentActivity'
import { BenchmarkStatus }   from './components/BenchmarkStatus'
import { ChatPanel }         from './components/ChatPanel'
import { ContextBudget }     from './components/ContextBudget'
import { Settings }          from './components/Settings'
import { StatusBar }         from './components/StatusBar'
import { useWebSocket }   from './hooks/useWebSocket'
import { api }            from './services/api'
import type { IndexStatusResponse, HealthResponse } from './services/api'
import { DEFAULT_STATS }  from './types/events'
import type { NexusEvent, TokenStats, BenchmarkResult } from './types/events'

export default function App() {
  const [isRunning,          setIsRunning]          = useState(false)
  const [isBenchmarkRunning, setIsBenchmarkRunning] = useState(false)
  const [response,           setResponse]           = useState('')
  const [tokenStats,         setTokenStats]         = useState<TokenStats>(DEFAULT_STATS)
  const [benchmarkResult,    setBenchmarkResult]    = useState<BenchmarkResult | null>(null)
  const [feedEvents,         setFeedEvents]         = useState<NexusEvent[]>([])
  const [error,              setError]              = useState<string | null>(null)
  const [health,             setHealth]             = useState<HealthResponse | null>(null)
  const [indexStatus,        setIndexStatus]        = useState<IndexStatusResponse | null>(null)
  const [claudeCliAvailable, setClaudeCliAvailable] = useState(false)
  const [sessionStartMs,     setSessionStartMs]     = useState(0)
  const [nexusEndMs,         setNexusEndMs]         = useState(0)
  const [benchmarkStartMs,   setBenchmarkStartMs]   = useState(0)
  const [benchmarkTool,      setBenchmarkTool]      = useState('')
  const [benchmarkToolCount, setBenchmarkToolCount] = useState(0)
  const [benchmarkResponse,  setBenchmarkResponse]  = useState('')

  const benchmarkResponseAccum = useRef('')

  const { connected, connect } = useWebSocket()
  const responseAccum = useRef('')

  // ── Startup polling ───────────────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const h = await api.health()
        setHealth(h)
        if (h.codebase_indexed) {
          const s = await api.indexStatus()
          setIndexStatus(s)
        }
        const bs = await api.benchmarkStatus()
        setClaudeCliAvailable(bs.available)
      } catch { /* backend not up yet */ }
    }
    poll()
    const id = setInterval(poll, 15_000)
    return () => clearInterval(id)
  }, [])

  // ── Shared event handler (used by both NEXUS-only and Race) ───────────────
  const makeEventHandler = useCallback(() => {
    return (event: NexusEvent) => {
      switch (event.type) {

        case 'token.update':
          setTokenStats(event.data as unknown as TokenStats)
          break

        case 'main_llm.stream':
          responseAccum.current += (event.data.chunk as string)
          setResponse(responseAccum.current)
          break

        case 'main_llm.done':
          if (event.data.tokens) setTokenStats(event.data.tokens as unknown as TokenStats)
          setFeedEvents((p) => [...p, event])
          break

        case 'session.done':
          setIsRunning(false)
          setNexusEndMs(Date.now())
          if (event.data.tokens) {
            setTokenStats(event.data.tokens as unknown as TokenStats)
          }
          setFeedEvents((p) => [...p, event])
          break

        case 'benchmark.started':
          setIsBenchmarkRunning(true)
          setBenchmarkStartMs(Date.now())
          setBenchmarkTool('')
          setBenchmarkToolCount(0)
          setBenchmarkResponse('')
          benchmarkResponseAccum.current = ''
          setFeedEvents((p) => [...p, event])
          break

        case 'benchmark.stream': {
          benchmarkResponseAccum.current += (event.data.chunk as string)
          setBenchmarkResponse(benchmarkResponseAccum.current)
          break
        }

        case 'benchmark.progress': {
          const d = event.data
          if (d.type === 'tool_use') {
            setBenchmarkTool(`${d.tool_name}  ${d.preview ?? ''}`)
            setBenchmarkToolCount((n) => n + 1)
          }
          setFeedEvents((p) => [...p, event])
          break
        }

        case 'benchmark.complete':
          setIsBenchmarkRunning(false)
          setBenchmarkResult({
            tokens:      event.data.tokens as number,
            toolCalls:   event.data.tool_calls as number,
            timeSeconds: event.data.time_seconds as number,
            model:       event.data.model as string | undefined,
          })
          setFeedEvents((p) => [...p, event])
          break

        case 'benchmark.timeout':
        case 'benchmark.error':
          setIsBenchmarkRunning(false)
          setFeedEvents((p) => [...p, event])
          break

        case 'system.error':
          setIsRunning(false)
          setIsBenchmarkRunning(false)
          setError(event.data.error as string)
          setFeedEvents((p) => [...p, event])
          break

        default:
          setFeedEvents((p) => [...p, event])
      }
    }
  }, [])

  // ── Reset state for a new session ─────────────────────────────────────────
  const resetSession = (sid: string) => {
    setIsRunning(true)
    setResponse('')
    setFeedEvents([])
    setError(null)
    setTokenStats(DEFAULT_STATS)
    setBenchmarkResult(null)
    setBenchmarkResponse('')
    setBenchmarkTool('')
    setBenchmarkToolCount(0)
    setBenchmarkStartMs(0)
    setNexusEndMs(0)
    setSessionStartMs(Date.now())
    responseAccum.current = ''
    benchmarkResponseAccum.current = ''
    connect(sid, makeEventHandler())
  }

  // ── NEXUS only ────────────────────────────────────────────────────────────
  const handleQuery = useCallback(async (query: string) => {
    const sid = crypto.randomUUID()
    resetSession(sid)
    await new Promise((r) => setTimeout(r, 100))
    try {
      await api.query(query, sid)
    } catch (e: unknown) {
      setIsRunning(false)
      setError((e as Error).message)
    }
  }, [makeEventHandler, connect])  // eslint-disable-line

  // ── NEXUS + Claude Code CLI race ──────────────────────────────────────────
  const handleRace = useCallback(async (query: string) => {
    const sid = crypto.randomUUID()
    resetSession(sid)
    setIsBenchmarkRunning(true)
    await new Promise((r) => setTimeout(r, 100))
    try {
      await api.race(query, sid)
    } catch (e: unknown) {
      setIsRunning(false)
      setIsBenchmarkRunning(false)
      setError((e as Error).message)
    }
  }, [makeEventHandler, connect])  // eslint-disable-line

  const handleIndex = useCallback(async (path: string) => {
    await api.index(path)
    const status = await api.indexStatus()
    setIndexStatus(status)
    setHealth((h) => h ? { ...h, codebase_indexed: true } : h)
  }, [])

  const handleClear = useCallback(() => {
    setResponse('')
    setFeedEvents([])
    setError(null)
    setTokenStats(DEFAULT_STATS)
    setBenchmarkResult(null)
    setNexusEndMs(0)
    responseAccum.current = ''
  }, [])

  const nexusTimeMs = nexusEndMs > 0 ? nexusEndMs - sessionStartMs : 0

  return (
    <div className="h-screen flex flex-col bg-zinc-950 text-zinc-100 font-mono overflow-hidden">
      <StatusBar health={health} connected={connected} isRunning={isRunning || isBenchmarkRunning} />

      <div className="flex-1 flex overflow-hidden min-h-0">
        <ChatPanel
          response={response}
          benchmarkResponse={benchmarkResponse}
          isRunning={isRunning}
          isBenchmarkRunning={isBenchmarkRunning}
          claudeCliAvailable={claudeCliAvailable}
          error={error}
          benchmarkResult={benchmarkResult}
          onQuery={handleQuery}
          onRace={handleRace}
          onClear={handleClear}
        />

        <div className="flex flex-col flex-1 overflow-hidden min-h-0">
          <ContextBudget
            stats={tokenStats}
            benchmark={benchmarkResult}
            nexusTimeMs={nexusTimeMs}
            isBenchmarkRunning={isBenchmarkRunning}
          />
          <BenchmarkStatus
            isRunning={isBenchmarkRunning}
            currentTool={benchmarkTool}
            toolCount={benchmarkToolCount}
            startedAt={benchmarkStartMs}
            result={benchmarkResult}
            response={benchmarkResponse}
          />
          <AgentActivity events={feedEvents} isRunning={isRunning || isBenchmarkRunning} />
          <Settings onIndex={handleIndex} indexStatus={indexStatus} />
        </div>
      </div>
    </div>
  )
}
