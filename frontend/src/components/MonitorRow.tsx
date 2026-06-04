import { useState } from 'react'
import { api } from '../api'
import { Icon, statusIcon } from '../icons'
import { toast } from '../toast'
import type { Monitor } from '../types'

const pct = (r: number | null) => (r == null ? '—' : `${(r * 100).toFixed(1)}%`)
const ms = (v: number | null) => (v == null ? '—' : `${Math.round(v)} ms`)
function ago(iso: string | null) {
  if (!iso) return 'never'
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${Math.floor(s)}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  return `${Math.floor(s / 3600)}h ago`
}

export function MonitorRow({ monitor: m, onChanged }: { monitor: Monitor; onChanged: () => void }) {
  const [busy, setBusy] = useState(false)
  const [checking, setChecking] = useState(false)
  const status = m.last_status || 'none'

  async function run(fn: () => Promise<unknown>) {
    setBusy(true)
    try { await fn(); onChanged() } catch (e) { toast((e as Error).message) } finally { setBusy(false) }
  }

  return (
    <div className="card monitor">
      <span className={`badge ${status}`}>{statusIcon(status)}{status}</span>
      <div className="meta">
        <div className="name">
          {m.name}
          {m.paused && <span className="pausedtag">paused</span>}
          {m.open_incidents > 0 && (
            <span className="badge down" title="open incidents">
              {m.open_incidents} incident{m.open_incidents > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="url" title={m.url}>{m.url}</div>
        <div className="subtle" style={{ fontSize: 12 }}>checked {ago(m.last_checked_at)}</div>
      </div>
      <div className="tile"><div className="tv">{pct(m.uptime_ratio)}</div><div className="tk">uptime</div></div>
      <div className="tile lat"><div className="tv">{ms(m.avg_latency_ms)}</div><div className="tk">latency</div></div>
      <div className="actions">
        <button className="btn ghost sm" title="Check now" aria-label="Check now" disabled={busy}
                onClick={() => { setChecking(true); run(() => api.checkNow(m.id)).finally(() => setChecking(false)) }}>
          <span className={checking ? 'spin' : ''}>{Icon.refresh}</span>
        </button>
        <button className="btn ghost sm" title={m.paused ? 'Resume' : 'Pause'} aria-label={m.paused ? 'Resume' : 'Pause'}
                disabled={busy} onClick={() => run(() => api.updateMonitor(m.id, { paused: !m.paused }))}>
          {m.paused ? Icon.play : Icon.pause}
        </button>
        <button className="btn danger sm" title="Delete" aria-label="Delete monitor" disabled={busy}
                onClick={() => { if (confirm('Delete this monitor and its history?')) run(() => api.deleteMonitor(m.id).then(() => toast('Monitor deleted.', 'ok'))) }}>
          {Icon.trash}
        </button>
      </div>
    </div>
  )
}
