import { useCallback, useEffect, useState } from 'react'
import { api, auth, setUnauthorizedHandler } from './api'
import { Auth } from './components/Auth'
import { AddMonitor } from './components/AddMonitor'
import { MonitorRow } from './components/MonitorRow'
import { Icon } from './icons'
import { Toasts, toast } from './toast'
import type { Monitor } from './types'

function Nav({ username, onLogout }: { username?: string | null; onLogout?: () => void }) {
  return (
    <nav className="nav">
      <span className="brand"><span className="dot" aria-hidden="true" />vigil</span>
      {username && (
        <div className="who">
          <span className="mono">{username}</span>
          <button className="btn ghost sm" onClick={onLogout}>Log out</button>
        </div>
      )}
    </nav>
  )
}

function Summary({ list }: { list: Monitor[] }) {
  const up = list.filter((m) => m.last_status === 'up' || m.last_status === 'changed').length
  const down = list.filter((m) => m.last_status === 'down').length
  return (
    <div className="stats" style={{ marginTop: 'var(--s4)' }}>
      <div className="card stat"><div className="k">Monitors</div><div className="v">{list.length}</div></div>
      <div className="card stat"><div className="k">Up</div><div className="v up">{up}</div></div>
      <div className="card stat"><div className="k">Down</div><div className="v down">{down}</div></div>
    </div>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(!!auth.token)
  const [monitors, setMonitors] = useState<Monitor[] | null>(null) // null = loading
  const [showAdd, setShowAdd] = useState(false)

  const load = useCallback(async () => {
    try { setMonitors(await api.listMonitors()) } catch (e) { toast((e as Error).message) }
  }, [])

  useEffect(() => { setUnauthorizedHandler(() => setAuthed(false)) }, [])

  useEffect(() => {
    if (!authed) return
    setMonitors(null)
    load()
    const t = window.setInterval(load, 15000)
    return () => window.clearInterval(t)
  }, [authed, load])

  function logout() { auth.clear(); setAuthed(false); setMonitors(null) }

  if (!authed) {
    return (<><Nav /><Auth onAuthed={() => setAuthed(true)} /><Toasts /></>)
  }

  return (
    <>
      <Nav username={auth.username} onLogout={logout} />
      <main>
        <div className="between">
          <div>
            <h1 style={{ fontSize: 24 }}>Monitors</h1>
            <p className="muted" style={{ fontSize: 14 }}>Auto-refreshing every 15s</p>
          </div>
          <button className="btn" onClick={() => setShowAdd((s) => !s)}>{Icon.plus} Add monitor</button>
        </div>

        {monitors && <Summary list={monitors} />}

        {showAdd && (
          <AddMonitor
            onClose={() => setShowAdd(false)}
            onCreated={() => { setShowAdd(false); load() }}
          />
        )}

        <div className="section-title">Your monitors</div>
        <div className="monitors" aria-live="polite">
          {monitors === null && [0, 1, 2].map((i) => <div key={i} className="skeleton" />)}
          {monitors?.length === 0 && (
            <div className="card empty">
              <svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 18 0 9 9 0 0 0-18 0zM12 8v4l3 2" /></svg>
              <p>No monitors yet.</p>
              <p className="subtle">Add one to start tracking uptime and changes.</p>
            </div>
          )}
          {monitors?.map((m) => <MonitorRow key={m.id} monitor={m} onChanged={load} />)}
        </div>
      </main>
      <Toasts />
    </>
  )
}
