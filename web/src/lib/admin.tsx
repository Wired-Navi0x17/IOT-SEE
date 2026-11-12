import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { api, ApiError } from './api'

type Ctx = { admin: boolean; ask: () => void; guard: (fn: () => unknown) => void; lock: () => void }
const AdminCtx = createContext<Ctx>({ admin: false, ask: () => {}, guard: () => {}, lock: () => {} })

export function AdminProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState(false)
  const [open, setOpen] = useState(false)
  const [pin, setPin] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const after = useRef<(() => unknown) | null>(null)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => { api.get<{ admin: boolean }>('/api/auth').then(r => setAdmin(r.admin)).catch(() => {}) }, [])
  useEffect(() => { if (open) setTimeout(() => input.current?.focus(), 30) }, [open])

  const guard = useCallback((fn: () => unknown) => {
    if (admin) { fn(); return }
    after.current = fn
    setOpen(true)
  }, [admin])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.post('/api/auth/unlock', { pin })
      setAdmin(true); setOpen(false); setPin(''); setErr(null)
      const fn = after.current; after.current = null
      fn?.()
    } catch (e) {
      setErr(e instanceof ApiError && e.status === 403 ? 'That PIN is not right.' : (e as Error).message)
    }
  }
  const lock = async () => { await api.post('/api/auth/lock'); setAdmin(false) }

  return (
    <AdminCtx.Provider value={{ admin, ask: () => setOpen(true), guard, lock }}>
      {children}
      {open && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-charcoal/80 p-4" onMouseDown={() => setOpen(false)}>
          <form className="panel w-full max-w-sm" onMouseDown={e => e.stopPropagation()} onSubmit={submit}>
            <div className="panel-head"><span className="h2">Admin PIN</span><span className="label">Writes and CYD commands</span></div>
            <div className="panel-body grid gap-4">
              <div className="field">
                <label className="label" htmlFor="pin">PIN</label>
                <input id="pin" ref={input} className="input num tracking-[0.4em]" inputMode="numeric" autoComplete="off"
                       value={pin} onChange={e => setPin(e.target.value)} maxLength={12} />
                {err ? <span className="error-text">{err}</span> : <span className="helper">Set in hub/.env as HUB_PIN.</span>}
              </div>
              <div className="flex justify-end gap-2">
                <button type="button" className="btn" onClick={() => setOpen(false)}>Cancel</button>
                <button className="btn btn-primary">Unlock</button>
              </div>
            </div>
          </form>
        </div>
      )}
    </AdminCtx.Provider>
  )
}

export const useAdmin = () => useContext(AdminCtx)
