import { useCallback, useEffect, useState } from 'react'
import { indexStatus, type IndexStatus, rescan } from '../lib/api'

const POLL_BUSY_MS = 700
const POLL_IDLE_MS = 10_000

export function Sidebar({ backendUrl }: { backendUrl: string }) {
  const [status, setStatus] = useState<IndexStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setStatus(await indexStatus(backendUrl))
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }, [backendUrl])

  // Poll quickly while indexing so progress feels live, slowly otherwise.
  useEffect(() => {
    const delay = status?.state === 'indexing' ? POLL_BUSY_MS : POLL_IDLE_MS
    const timer = setTimeout(refresh, status ? delay : 0)
    return () => clearTimeout(timer)
  }, [status, refresh])

  async function onRescan() {
    await rescan(backendUrl)
    await refresh()
  }

  const failures = Object.entries(status?.failures ?? {})

  return (
    <aside className="sidebar">
      <div className="brand">IndexMind</div>

      <section>
        <h2>Library</h2>
        {status ? <Summary status={status} /> : <p className="muted">Connecting…</p>}
        {error && <p className="error">{error}</p>}
      </section>

      {failures.length > 0 && (
        <section>
          <h2>Skipped files</h2>
          <ul className="failures">
            {failures.map(([file, reason]) => (
              <li key={file} title={reason}>
                {file}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="actions">
        <button onClick={() => void window.indexmind.openDocsFolder()}>Open folder</button>
        <button onClick={onRescan} disabled={status?.state === 'indexing'}>
          Rescan
        </button>
      </div>
      {status && (
        <p className="path" title={status.docs_dir}>
          {status.docs_dir}
        </p>
      )}
    </aside>
  )
}

function Summary({ status }: { status: IndexStatus }) {
  if (status.state === 'indexing') {
    return (
      <>
        <p>
          Indexing {Math.min(status.processed + 1, status.pending)} of {status.pending}…
        </p>
        {status.current && <p className="muted ellipsis">{status.current}</p>}
        <progress value={status.processed} max={Math.max(status.pending, 1)} />
      </>
    )
  }
  if (status.state === 'error') {
    return <p className="error">Indexing failed: {status.error}</p>
  }
  if (status.files === 0) {
    return <p className="muted">No documents yet. Add PDF, Markdown or text files to your folder, then rescan.</p>
  }
  return (
    <p>
      {status.files} {status.files === 1 ? 'document' : 'documents'}
      <span className="muted"> · {status.chunks} passages</span>
    </p>
  )
}
