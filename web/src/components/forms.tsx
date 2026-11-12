import { useState } from 'react'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import type { Team, Tournament } from '../lib/types'
import { Field, Modal } from './ui'

function useSubmit<T>(fn: () => Promise<T>, onDone: (r: T) => void) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setError(null)
    try { onDone(await fn()) } catch (err) { setError((err as Error).message) } finally { setBusy(false) }
  }
  return { busy, error, submit }
}

export function CreateTournament({ onClose, onDone }: { onClose: () => void; onDone: (t: Tournament) => void }) {
  const teams = useApi<Team[]>('/api/teams')
  const [f, setF] = useState({ name: '', format: 'T20', overs: 20, venue: '', start_date: '', end_date: '', team_ids: [] as number[] })
  const { busy, error, submit } = useSubmit(() => api.post<Tournament>('/api/tournaments', f), onDone)
  const toggle = (id: number) => setF(v => ({ ...v, team_ids: v.team_ids.includes(id) ? v.team_ids.filter(x => x !== id) : [...v.team_ids, id] }))
  return (
    <Modal title="Create tournament" onClose={onClose} wide>
      <form onSubmit={submit} className="grid gap-4">
        <Field label="Name" htmlFor="tn" helper="Shown on the CYD header, keep it under 40 characters.">
          <input id="tn" className="input" required minLength={3} value={f.name} onChange={e => setF({ ...f, name: e.target.value })} placeholder="Konkan Coast T20 League 2027" />
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Format" htmlFor="tf">
            <select id="tf" className="select" value={f.format} onChange={e => setF({ ...f, format: e.target.value, overs: e.target.value === 'ODI' ? 50 : e.target.value === 'T10' ? 10 : 20 })}>
              <option>T20</option><option>T10</option><option>ODI</option>
            </select>
          </Field>
          <Field label="Overs" htmlFor="to"><input id="to" type="number" min={1} max={50} className="input num" value={f.overs} onChange={e => setF({ ...f, overs: +e.target.value })} /></Field>
          <Field label="Venue" htmlFor="tv"><input id="tv" className="input" value={f.venue} onChange={e => setF({ ...f, venue: e.target.value })} /></Field>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Starts" htmlFor="ts"><input id="ts" type="date" className="input num" value={f.start_date} onChange={e => setF({ ...f, start_date: e.target.value })} /></Field>
          <Field label="Ends" htmlFor="te"><input id="te" type="date" className="input num" value={f.end_date} onChange={e => setF({ ...f, end_date: e.target.value })} /></Field>
        </div>
        <Field label="Teams" helper={`${f.team_ids.length} selected. You can add more later.`}>
          <div className="flex flex-wrap gap-1.5">
            {(teams.data ?? []).map(t => (
              <button type="button" key={t.id} onClick={() => toggle(t.id)}
                className={`btn btn-sm ${f.team_ids.includes(t.id) ? 'btn-primary' : ''}`} aria-pressed={f.team_ids.includes(t.id)}>{t.short} <span className="text-dim">{t.name}</span></button>
            ))}
          </div>
        </Field>
        {error && <span className="error-text">{error}</span>}
        <div className="flex justify-end gap-2"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy}>Create tournament</button></div>
      </form>
    </Modal>
  )
}

export function ScheduleMatch({ onClose, onDone, tournamentId }: { onClose: () => void; onDone: () => void; tournamentId?: number }) {
  const teams = useApi<Team[]>('/api/teams')
  const tours = useApi<Tournament[]>('/api/tournaments')
  const tomorrow = new Date(Date.now() + 86400000); tomorrow.setHours(19, 0, 0, 0)
  const local = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
  const [f, setF] = useState({ team_a_id: 0, team_b_id: 0, tournament_id: tournamentId ?? 0, overs: 20, venue: '', scheduled_at: local })
  const { busy, error, submit } = useSubmit(() => api.post('/api/matches', {
    ...f, tournament_id: f.tournament_id || null, scheduled_at: new Date(f.scheduled_at).toISOString(),
  }), onDone)
  const list = teams.data ?? []
  return (
    <Modal title="Schedule match" onClose={onClose}>
      <form onSubmit={submit} className="grid gap-4">
        <Field label="Tournament" htmlFor="mt">
          <select id="mt" className="select" value={f.tournament_id} onChange={e => {
            const t = (tours.data ?? []).find(x => x.id === +e.target.value)
            setF({ ...f, tournament_id: +e.target.value, overs: t?.overs ?? f.overs, venue: t?.venue ?? f.venue })
          }}>
            <option value={0}>Friendly (no tournament)</option>
            {(tours.data ?? []).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Team A (purple)" htmlFor="ma">
            <select id="ma" className="select" required value={f.team_a_id} onChange={e => setF({ ...f, team_a_id: +e.target.value })}>
              <option value={0} disabled>Choose</option>{list.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </Field>
          <Field label="Team B (turquoise)" htmlFor="mb">
            <select id="mb" className="select" required value={f.team_b_id} onChange={e => setF({ ...f, team_b_id: +e.target.value })}>
              <option value={0} disabled>Choose</option>{list.filter(t => t.id !== f.team_a_id).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </Field>
        </div>
        <div className="grid grid-cols-[1fr_96px] gap-4">
          <Field label="Start" htmlFor="ms"><input id="ms" type="datetime-local" className="input num" value={f.scheduled_at} onChange={e => setF({ ...f, scheduled_at: e.target.value })} /></Field>
          <Field label="Overs" htmlFor="mo"><input id="mo" type="number" min={1} max={50} className="input num" value={f.overs} onChange={e => setF({ ...f, overs: +e.target.value })} /></Field>
        </div>
        <Field label="Venue" htmlFor="mv"><input id="mv" className="input" value={f.venue} onChange={e => setF({ ...f, venue: e.target.value })} /></Field>
        {error && <span className="error-text">{error}</span>}
        <div className="flex justify-end gap-2"><button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={busy || !f.team_a_id || !f.team_b_id}>Schedule</button></div>
      </form>
    </Modal>
  )
}

export function RegisterTeam({ onClose, onDone }: { onClose: () => void; onDone: (t: Team) => void }) {
  const tours = useApi<Tournament[]>('/api/tournaments')
  const [f, setF] = useState({ name: '', short: '', city: '', manager: '', tournament_id: 0 })
  const { busy, error, submit } = useSubmit(() => api.post<Team>('/api/teams', { ...f, tournament_id: f.tournament_id || null }), onDone)
  return (
    <Modal title="Register team" onClose={onClose}>
      <form onSubmit={submit} className="grid gap-4">
        <div className="grid grid-cols-[1fr_96px] gap-4">
          <Field label="Team name" htmlFor="rn"><input id="rn" className="input" required minLength={3} value={f.name} onChange={e => setF({ ...f, name: e.target.value })} placeholder="Dapoli Dolphins" /></Field>
          <Field label="Code" htmlFor="rs" helper="2-4 letters"><input id="rs" className="input num uppercase" required minLength={2} maxLength={4} value={f.short} onChange={e => setF({ ...f, short: e.target.value.toUpperCase() })} /></Field>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="City" htmlFor="rc"><input id="rc" className="input" value={f.city} onChange={e => setF({ ...f, city: e.target.value })} /></Field>
          <Field label="Team manager" htmlFor="rm"><input id="rm" className="input" value={f.manager} onChange={e => setF({ ...f, manager: e.target.value })} /></Field>
        </div>
        <Field label="Enter in tournament" htmlFor="rt">
          <select id="rt" className="select" value={f.tournament_id} onChange={e => setF({ ...f, tournament_id: +e.target.value })}>
            <option value={0}>Not yet</option>{(tours.data ?? []).filter(t => t.status !== 'completed').map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </Field>
        {error && <span className="error-text">{error}</span>}
        <div className="flex justify-end gap-2"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy}>Register team</button></div>
      </form>
    </Modal>
  )
}

export function AddPlayer({ teamId, onClose, onDone }: { teamId: number; onClose: () => void; onDone: () => void }) {
  const [f, setF] = useState({ name: '', role: 'BAT', bat: 55, bowl: 20, style: '' })
  const { busy, error, submit } = useSubmit(() => api.post(`/api/teams/${teamId}/players`, f), onDone)
  return (
    <Modal title="Register player" onClose={onClose}>
      <form onSubmit={submit} className="grid gap-4">
        <Field label="Full name" htmlFor="pn"><input id="pn" className="input" required minLength={3} value={f.name} onChange={e => setF({ ...f, name: e.target.value })} /></Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Role" htmlFor="pr">
            <select id="pr" className="select" value={f.role} onChange={e => setF({ ...f, role: e.target.value })}>
              <option value="BAT">Batter</option><option value="WK">Wicketkeeper</option><option value="AR">All-rounder</option><option value="BOWL">Bowler</option>
            </select>
          </Field>
          <Field label="Bowling style" htmlFor="ps" helper="RF, RFM, OB, LB, SLA..."><input id="ps" className="input" value={f.style} onChange={e => setF({ ...f, style: e.target.value })} /></Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label={`Batting rating ${f.bat}`} htmlFor="pb" helper="Drives the simulator"><input id="pb" type="range" min={1} max={100} value={f.bat} onChange={e => setF({ ...f, bat: +e.target.value })} className="accent-[#4DB6C4]" /></Field>
          <Field label={`Bowling rating ${f.bowl}`} htmlFor="pw"><input id="pw" type="range" min={1} max={100} value={f.bowl} onChange={e => setF({ ...f, bowl: +e.target.value })} className="accent-[#4DB6C4]" /></Field>
        </div>
        {error && <span className="error-text">{error}</span>}
        <div className="flex justify-end gap-2"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy}>Add player</button></div>
      </form>
    </Modal>
  )
}
