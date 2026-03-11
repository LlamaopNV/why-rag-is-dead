import { useCallback, useEffect, useRef, useState } from 'react'
import { AgentActivity }  from './components/AgentActivity'
import { ChatPanel }      from './components/ChatPanel'
import { ContextBudget }  from './components/ContextBudget'
import { Settings }       from './components/Settings'
import { StatusBar }      from './components/StatusBar'
import { useWebSocket }   from './hooks/useWebSocket'
import { api }            from './services/api'
import type { IndexStatusResponse, HealthResponse } from './services/api'
import { DEFAULT_STATS }  from './types/events'
import type { NexusEvent, TokenStats } from './types/events'

export default function App() {
  const [isRunning,   setIsRunning]   = useState(false)
  const [response,    setResponse]    = useState('')
  const [tokenStats,  setTokenStats]  = useState<TokenStats>(DEFAULT_STATS)
  const [feedEvents,  setFeedEvents]  = useState<NexusEvent[]>([])
  const [error,       setError]       = useState<string | null>(null)
  const [health,      setHealth]      = useState<HealthResponse | null>(null)
  const [indexStatus, setIndexStatus] = useState<IndexStatusResponse | null>(null)

  const { connected, connect } = useWebSocket()
  const responseAccum = useRef('')   // accumulate stream chunks without triggering renders per char

  // ── Poll health + index status on mount and every 15s ────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const h = await api.health()
        setHealth(h)
        if (h.codebase_indexed) {
          const s = await api.indexStatus()
          setIndexStatus(s)
        }
      } catch { /* backend not up yet */ }
    }
    poll()
    const id = setInterval(poll, 15_000)
    return () => clearInterval(id)
  }, [])

  // ── Submit a query ────────────────────────────────────────────────────────
  // Pattern:
  //   1. Generate UUID for session_id
  //   2. Connect WebSocket (before POST so we don't miss early events)
  //   3. Wait 100ms for WS handshake
  //   4. POST /api/query with that session_id
  //   5. All results (including streamed response) come through WebSocket
  const handleQuery = useCallback(async (query: string, naiveMode: boolean) => {
    const sid = crypto.randomUUID()
    setIsRunning(true)
    setResponse('')
    setFeedEvents([])
    setError(null)
    setTokenStats(DEFAULT_STATS)
    responseAccum.current = ''

    connect(sid, (event: NexusEvent) => {
      switch (event.type) {

        // ── Token updates ─────────────────────────────────────────────────
        case 'token.update':
          setTokenStats(event.data as unknown as TokenStats)
          break

        // ── Streaming response ────────────────────────────────────────────
        case 'main_llm.stream': {
          const chunk = event.data.chunk as string
          responseAccum.current += chunk
          setResponse(responseAccum.current)
          break
        }

        // ── Final token tally from main LLM ──────────────────────────────
        case 'main_llm.done':
          if (event.data.tokens) {
            setTokenStats(event.data.tokens as unknown as TokenStats)
          }
          setFeedEvents((prev) => [...prev, event])
          break

        // ── Session complete ──────────────────────────────────────────────
        case 'session.done':
          setIsRunning(false)
          if (event.data.tokens) {
            // Merge session.done's top-level naive_estimate (may be more accurate
            // than the one inside tokens from naive comparison scaling)
            const t = event.data.tokens as unknown as TokenStats
            setTokenStats({
              ...t,
              naive_estimate: (event.data.naive_estimate as number) ?? t.naive_estimate,
            })
          }
          setFeedEvents((prev) => [...prev, event])
          break

        // ── Error ─────────────────────────────────────────────────────────
        case 'system.error':
          setIsRunning(false)
          setError(event.data.error as string)
          setFeedEvents((prev) => [...prev, event])
          break

        // ── All other events → activity feed (skip silent stream events) ──
        default:
          setFeedEvents((prev) => [...prev, event])
      }
    })

    // Small delay for WS handshake to complete
    await new Promise((r) => setTimeout(r, 100))

    try {
      await api.query(query, sid, naiveMode)
    } catch (e: unknown) {
      setIsRunning(false)
      setError((e as Error).message)
    }
  }, [connect])

  // ── Index a codebase path ─────────────────────────────────────────────────
  const handleIndex = useCallback(async (path: string) => {
    await api.index(path)
    const status = await api.indexStatus()
    setIndexStatus(status)
    setHealth((h) => h ? { ...h, codebase_indexed: true } : h)
  }, [])

  // ── Clear chat ────────────────────────────────────────────────────────────
  const handleClear = useCallback(() => {
    setResponse('')
    setFeedEvents([])
    setError(null)
    setTokenStats(DEFAULT_STATS)
    responseAccum.current = ''
  }, [])

  return (
    <div className="h-screen flex flex-col bg-zinc-950 text-zinc-100 font-mono overflow-hidden">
      <StatusBar health={health} connected={connected} isRunning={isRunning} />

      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left — Chat */}
        <ChatPanel
          response={response}
          isRunning={isRunning}
          error={error}
          onQuery={handleQuery}
          onClear={handleClear}
        />

        {/* Right — Agent panel */}
        <div className="flex flex-col flex-1 overflow-hidden min-h-0">
          <ContextBudget stats={tokenStats} />
          <AgentActivity events={feedEvents} isRunning={isRunning} />
          <Settings onIndex={handleIndex} indexStatus={indexStatus} />
        </div>
      </div>
    </div>
  )
}
