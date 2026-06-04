import { useState } from 'react'
import { api, auth } from '../api'
import { Icon } from '../icons'

export function Auth({ onAuthed }: { onAuthed: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(action: 'login' | 'register') {
    setErr('')
    if (!username.trim() || !password) { setErr('Username and password are required.'); return }
    setBusy(true)
    try {
      const token = await api[action](username.trim(), password)
      auth.set(token)
      onAuthed()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-wrap">
      <div className="card pad auth">
        <h1>Sign in to vigil</h1>
        <p className="lede">Uptime &amp; change monitoring for your endpoints.</p>
        <form onSubmit={(e) => { e.preventDefault(); submit('login') }} noValidate>
          <div className="field">
            <label className="label" htmlFor="u">Username <span className="req" aria-hidden="true">*</span></label>
            <input className="input" id="u" autoComplete="username" value={username}
                   onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="field">
            <label className="label" htmlFor="p">Password <span className="req" aria-hidden="true">*</span></label>
            <div className="pw-wrap">
              <input className="input" id="p" type={show ? 'text' : 'password'} autoComplete="current-password"
                     value={password} onChange={(e) => setPassword(e.target.value)} />
              <button className="pw-toggle" type="button" aria-label={show ? 'Hide password' : 'Show password'}
                      onClick={() => setShow((s) => !s)}>{Icon.eye}</button>
            </div>
          </div>
          <p className="err-text" role="alert" aria-live="polite">{err}</p>
          <div className="row" style={{ marginTop: 'var(--s4)' }}>
            <button className="btn" type="submit" disabled={busy} style={{ flex: 1 }}>Log in</button>
            <button className="btn ghost" type="button" disabled={busy} style={{ flex: 1 }}
                    onClick={() => submit('register')}>Create account</button>
          </div>
        </form>
      </div>
    </section>
  )
}
