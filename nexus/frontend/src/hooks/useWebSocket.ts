import { useCallback, useEffect, useRef, useState } from 'react'
import type { NexusEvent } from '../types/events'

const WS_BASE = 'ws://localhost:8000'

export function useWebSocket() {
  const [connected, setConnected] = useState(false)
  const wsRef    = useRef<WebSocket | null>(null)
  const cbRef    = useRef<((e: NexusEvent) => void) | null>(null)

  // Connect to /ws/{session_id}.
  // Pass the event callback here — stored in a ref so it never goes stale.
  const connect = useCallback((sessionId: string, onEvent: (e: NexusEvent) => void) => {
    wsRef.current?.close()
    cbRef.current = onEvent

    const ws = new WebSocket(`${WS_BASE}/ws/${sessionId}`)
    wsRef.current = ws

    ws.onopen  = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)
    ws.onmessage = (evt) => {
      if (evt.data === 'pong') return
      try {
        const event = JSON.parse(evt.data as string) as NexusEvent
        cbRef.current?.(event)
      } catch {/* malformed frame — ignore */}
    }
  }, [])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    setConnected(false)
  }, [])

  // 25-second keepalive ping (backend responds with "pong")
  useEffect(() => {
    const id = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 25_000)
    return () => clearInterval(id)
  }, [])

  return { connected, connect, disconnect }
}
