import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PauseIcon, PlayIcon } from '@phosphor-icons/react'
import { Page, Panel, Empty, ErrorRow, Field, Segmented, SkeletonRows } from '../components/ui'
import { Seam } from '../components/Seam'
import { XiPicker, type XiChoice } from '../components/XiPicker'
import { MatchRow } from '../components/MatchRow'
import { Scoreboard, ShowOnCyd } from './LiveCentre'
import { useApi } from '../lib/hooks'
import { useLive } from '../lib/live'
import { useAdmin } from '../lib/admin'
import { api } from '../lib/api'
import { teamVars } from '../lib/teams'
import type { MatchRow as Row, MatchState, Team } from '../lib/types'

type Speed = 'broadcast' | 'quick' | 'turbo'
const SPEEDS: { value: Speed; label: string }[] = [{ value: 'broadcast', label: '4 s/ball' }, { value: 'quick', label: '1.2 s/ball' }, { value: 'turbo', label: '0.25 s/ball' }]

function Setup({ onStarted }: { onStarted: (id: number) => void }) {
  const teams = useApi<Team[]>('/api/teams')
  const { guard } = useAdmin()
  const [f, setF] = useState({ team_a_id: 0, team_b_id: 0, overs: 20, toss_winner: 'A', elected: 'bat', speed: 'quick' as Speed, show_on_cyd: true })
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [xa, setXa] = useState<XiChoice | null>(null)
  const [xb, setXb] = useState<XiChoice | null>(null)
  const onA = useCallback((v: XiChoice) => setXa(v), [])
  const onB = useCallback((v: XiChoice) => setXb(v), [])
  useEffect(() => {
    if (teams.data && teams.data.length > 1 && !f.team_a_id) setF(v => ({ ...v, team_a_id: teams.data![0].id, team_b_id: teams.data![1].id }))
  }, [teams.data, f.team_a_id])
  const go = () => guard(async () => {
    setBusy(true); setErr(null)
    try { const r = await api.post<{ id: number }>('/api/sim', { ...f, xi_a: xa?.xi, xi_b: xb?.xi, bowlers_a: xa?.bowlers, bowlers_b: xb?.bowlers }); onStarted(r.id) } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  })
  const list = teams.data ?? []
  return (
    <Panel title="New simulation" meta="Ratings-driven ball model">
      <div className="grid gap-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Team A" htmlFor="sa"><select id="sa" className="select" value={f.team_a_id} onChange={e => { const a = +e.target.value; setF({ ...f, team_a_id: a, team_b_id: a === f.team_b_id ? (list.find(t => t.id !== a)?.id ?? 0) : f.team_b_id }) }}>{list.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field>
          <Field label="Team B" htmlFor="sb"><select id="sb" className="select" value={f.team_b_id} onChange={e => setF({ ...f, team_b_id: +e.target.value })}>{list.filter(t => t.id !== f.team_a_id).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <XiPicker teamId={f.team_a_id} label={`${list.find(t => t.id === f.team_a_id)?.short ?? 'A'} XI · batting order`} value={xa} onChange={onA} />
          <XiPicker teamId={f.team_b_id} label={`${list.find(t => t.id === f.team_b_id)?.short ?? 'B'} XI · batting order`} value={xb} onChange={onB} />
        </div>
        <div className="flex flex-wrap gap-5">
          <Field label="Overs"><Segmented value={String(f.overs)} onChange={v => setF({ ...f, overs: +v })} label="Overs" options={[{ value: '5', label: '5' }, { value: '10', label: '10' }, { value: '20', label: '20' }]} /></Field>
          <Field label="Toss"><Segmented value={f.toss_winner} onChange={v => setF({ ...f, toss_winner: v })} label="Toss" options={[{ value: 'A', label: 'A wins' }, { value: 'B', label: 'B wins' }]} /></Field>
          <Field label="Elected"><Segmented value={f.elected} onChange={v => setF({ ...f, elected: v })} label="Elected" options={[{ value: 'bat', label: 'Bat' }, { value: 'bowl', label: 'Bowl' }]} /></Field>
        </div>
        <div className="flex flex-wrap items-end gap-5">
          <Field label="Pace"><Segmented value={f.speed} onChange={v => setF({ ...f, speed: v })} label="Pace" options={SPEEDS} /></Field>
          <label className="flex min-h-9 items-center gap-2 text-[13px]"><input type="checkbox" checked={f.show_on_cyd} onChange={e => setF({ ...f, show_on_cyd: e.target.checked })} className="accent-[#4DB6C4]" />Show on CYD</label>
        </div>
        <p className="text-xs text-dim">Top of each list opens the batting. Only ticked players bowl (max {Math.max(1, Math.floor((f.overs + 4) / 5))} overs each); if they run out of overs the rest of the XI fills in. Each ball comes from batter-vs-bowler ratings, the match phase and the required rate, computed on the UNO Q. Show on CYD puts it on Screen 2.</p>
        {err && <ErrorRow message={err} />}
        <div><button className="btn btn-primary" disabled={busy || !f.team_a_id || !f.team_b_id || (xa?.xi.length ?? 0) < 2 || (xb?.xi.length ?? 0) < 2} onClick={go}><PlayIcon size={16} weight="light" />Simulate match</button></div>
      </div>
    </Panel>
  )
}

function Running({ id }: { id: number }) {
  const d = useApi<Row & { state: MatchState }>(`/api/matches/${id}`, [id])
  const pushed = useLive(s => s.matches[id])
  const running = useApi<{ running: number[]; speed: Record<string, Speed> }>('/api/sim/running', [pushed?.ended])
  const { guard } = useAdmin()
  const s = pushed ?? d.data?.state
  const isRunning = running.data?.running.includes(id)
  const speed = running.data?.speed[String(id)] ?? 'quick'
  const call = (path: string, body: unknown = {}) => guard(async () => { await api.post(`/api/sim/${id}/${path}`, body); running.reload(true) })
  if (!s) return d.error ? <ErrorRow message={d.error} /> : <SkeletonRows rows={3} h={120} />
  return (
    <div className="grid gap-4" style={teamVars(s.teamA.short || s.teamA.name, s.teamB.short || s.teamB.name)}>
      <section className="panel overflow-hidden" data-reveal>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-4 py-2.5">
          <span className="flex items-baseline gap-2"><span className="team-a font-semibold">{s.teamA.name}</span><span className="text-dim">v</span><span className="team-b font-semibold">{s.teamB.name}</span></span>
          <div className="flex flex-wrap items-center gap-2">
            {!s.ended && <Segmented value={speed} onChange={v => call('speed', { speed: v })} label="Pace" options={SPEEDS} />}
            {!s.ended && (isRunning ? <button className="btn btn-sm" onClick={() => call('pause')}><PauseIcon size={14} weight="light" />Pause</button>
              : <button className="btn btn-sm btn-primary" onClick={() => call('resume')}><PlayIcon size={14} weight="light" />Resume</button>)}
            <ShowOnCyd matchId={id} sim />
          </div>
        </div>
        <Seam winA={s.winA} height={150} event={s.lastEvent} eventSeq={s.eventSeq} battingIsA={s.battingIsA} labelA={s.teamA.short} labelB={s.teamB.short} />
      </section>
      <Scoreboard s={s} />
    </div>
  )
}

export default function Simulation() {
  const { id } = useParams()
  const nav = useNavigate()
  const sims = useApi<Row[]>('/api/matches?source=sim')
  const mid = id ? +id : undefined
  return (
    <Page title="Simulation" revealKey={mid} sub="Pick two squads and play a match out ball by ball. The result feeds the leaderboards like any scored match."
          actions={mid ? <button className="btn" onClick={() => nav('/sim')}>New simulation</button> : undefined}>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <div className="min-w-0">{mid ? <Running id={mid} /> : <Setup onStarted={i => { sims.reload(true); nav(`/sim/${i}`) }} />}</div>
        <Panel title="Simulated matches" bodyClass="" actions={<button className="btn btn-sm" onClick={() => sims.reload()}>Refresh</button>}>
          {sims.loading && !sims.data ? <div className="p-4"><SkeletonRows rows={4} /></div> : sims.data?.length ? sims.data.slice(0, 12).map(m => <MatchRow key={m.id} m={m} to={`/sim/${m.id}`} />) :
            <div className="p-4"><Empty title="No simulations yet" hint="Run one on the left. It takes about four minutes for a T20 at 1.2 s per ball." /></div>}
        </Panel>
      </div>
    </Page>
  )
}
