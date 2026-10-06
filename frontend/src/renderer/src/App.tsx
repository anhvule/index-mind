import { useEffect, useState } from 'react'
import type { BackendInfo } from '../../shared/bridge'
import { Chat } from './components/Chat'
import { Sidebar } from './components/Sidebar'

export function App() {
  const [backend, setBackend] = useState<BackendInfo>({ state: 'starting' })

  useEffect(() => {
    window.indexmind.backend().then(setBackend)
  }, [])

  if (backend.state === 'starting') {
    return <div className="empty">Starting IndexMind…</div>
  }
  if (backend.state === 'failed') {
    return (
      <div className="empty">
        <h1>IndexMind couldn't start</h1>
        <pre className="error">{backend.message}</pre>
      </div>
    )
  }
  return (
    <div className="layout">
      <Sidebar backendUrl={backend.url} />
      <Chat backendUrl={backend.url} />
    </div>
  )
}
