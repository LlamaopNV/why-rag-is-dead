import { useState } from 'react'
import type { IndexStatusResponse } from '../services/api'

interface Props {
  onIndex: (path: string) => Promise<void>
  indexStatus: IndexStatusResponse | null
}

export function Settings({ onIndex, indexStatus }: Props) {
  const [path,    setPath]    = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const handle = async () => {
    if (!path.trim() || loading) return
    setLoading(true)
    setError('')
    try {
      await onIndex(path.trim())
    } catch (e: unknown) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border-t border-zinc-800 px-4 py-3 flex-shrink-0">
      <div className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase mb-2">
        Codebase
      </div>

      <div className="flex gap-2 mb-1.5">
        <input
          type="text"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handle()}
          placeholder="/path/to/codebase or C:\path\to\repo"
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-500 font-mono min-w-0"
        />
        <button
          onClick={handle}
          disabled={loading || !path.trim()}
          className="px-3 py-1.5 text-xs bg-zinc-700 hover:bg-zinc-600 disabled:opacity-40 rounded transition-colors flex-shrink-0"
        >
          {loading ? '…' : 'Index'}
        </button>
      </div>

      {error && <div className="text-xs text-red-400 mb-1">{error}</div>}

      {indexStatus?.indexed && (
        <div className="text-[11px] text-zinc-500 flex flex-wrap gap-x-3 gap-y-0.5">
          <span className="text-green-500">✓ indexed</span>
          <span>{indexStatus.file_count?.toLocaleString()} files</span>
          <span>{indexStatus.total_lines?.toLocaleString()} lines</span>
          <span>
            ~{Math.round((indexStatus.naive_token_estimate ?? 0) / 1000)}K naive tokens
          </span>
        </div>
      )}
    </div>
  )
}
