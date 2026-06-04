import { useState } from 'react'
import { api } from '../api'
import { toast } from '../toast'

export function AddMonitor({ onCreated, onClose }: { onCreated: () => void; onClose: () => void }) {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [interval, setInterval] = useState('300')
  const [status, setStatus] = useState('200')
  const [keyword, setKeyword] = useState('')
  const [webhook, setWebhook] = useState('')
  const [watch, setWatch] = useState(false)
  const [errs, setErrs] = useState<{ name?: string; url?: string }>({})
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const next: typeof errs = {}
    if (!name.trim()) next.name = 'Give the monitor a name.'
    if (!/^https?:\/\/.+/i.test(url.trim())) next.url = 'Enter a full URL (https://…).'
    setErrs(next)
    if (Object.keys(next).length) return

    setBusy(true)
    try {
      await api.createMonitor({
        name: name.trim(), url: url.trim(),
        interval_seconds: Number(interval) || 300,
        expected_status: Number(status) || 200,
        keyword: keyword.trim() || null,
        watch_content: watch,
        webhook_url: webhook.trim() || null,
      })
      toast('Monitor created.', 'ok')
      onCreated()
    } catch (e2) {
      toast((e2 as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card pad" style={{ marginTop: 'var(--s4)' }}>
      <h2 style={{ fontSize: 16, marginBottom: 'var(--s2)' }}>New monitor</h2>
      <form onSubmit={submit} noValidate>
        <div className="addform">
          <div className="field">
            <label className="label" htmlFor="m-name">Name <span className="req">*</span></label>
            <input className="input" id="m-name" placeholder="My API" value={name}
                   aria-invalid={!!errs.name} onChange={(e) => setName(e.target.value)} />
            <span className="err-text">{errs.name}</span>
          </div>
          <div className="field">
            <label className="label" htmlFor="m-url">URL <span className="req">*</span></label>
            <input className="input" id="m-url" placeholder="https://example.com/health" inputMode="url"
                   value={url} aria-invalid={!!errs.url} onChange={(e) => setUrl(e.target.value)} />
            <span className="err-text">{errs.url}</span>
          </div>
          <div className="field">
            <label className="label" htmlFor="m-int">Check interval</label>
            <input className="input mono" id="m-int" type="number" min={10} value={interval}
                   onChange={(e) => setInterval(e.target.value)} />
            <span className="hint">seconds between checks</span>
          </div>
          <div className="field">
            <label className="label" htmlFor="m-status">Expected status</label>
            <input className="input mono" id="m-status" type="number" value={status}
                   onChange={(e) => setStatus(e.target.value)} />
            <span className="hint">HTTP code that means healthy</span>
          </div>
          <div className="field">
            <label className="label" htmlFor="m-kw">Keyword <span className="subtle">(optional)</span></label>
            <input className="input" id="m-kw" placeholder="must appear in the body"
                   value={keyword} onChange={(e) => setKeyword(e.target.value)} />
          </div>
          <div className="field">
            <label className="label" htmlFor="m-hook">Alert webhook <span className="subtle">(optional)</span></label>
            <input className="input" id="m-hook" placeholder="https://hooks.slack.com/…" inputMode="url"
                   value={webhook} onChange={(e) => setWebhook(e.target.value)} />
          </div>
          <label className="check-row full" htmlFor="m-watch">
            <input type="checkbox" id="m-watch" checked={watch} onChange={(e) => setWatch(e.target.checked)} />
            <span>Alert me when the page content changes</span>
          </label>
        </div>
        <div className="row" style={{ marginTop: 'var(--s4)' }}>
          <button className="btn" type="submit" disabled={busy}>Create monitor</button>
          <button className="btn ghost" type="button" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </div>
  )
}
