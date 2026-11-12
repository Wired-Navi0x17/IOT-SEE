import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Page, Panel, Empty, ErrorRow, SkeletonRows, Segmented } from '../components/ui'
import { MatchRow } from '../components/MatchRow'
import { CreateTournament, ScheduleMatch } from '../components/forms'
import { useApi } from '../lib/hooks'
import { useAdmin } from '../lib/admin'
import { api } from '../lib/api'
import type { MatchRow as Row, Team, Tournament } from '../lib/types'

type Detail = Tournament & { teams: Team[]; fixtures: Row[]; table: { teamId: number; team: string; short: string; p: number; w: number; l: number; t: number; pts: number; nrr: number }[] }

function TournamentDetail({ id, onChanged }: { id: number; onChanged: () => void }) {
  const d = useApi<Detail>(`/api/tournaments/${id}`, [id])
  const all = useApi<Team[]>('/api/teams')
  const { guard } = useAdmin()
  const [modal, setModal] = useState(false)
  const [addTeam, setAddTeam] = useState(0)
  const [filter, setFilter] = useState<'all' | 'scheduled' | 'completed'>('all')
  if (d.loading && !d.data) return <SkeletonRows rows={4} h={90} />
  if (d.error) return <ErrorRow message={d.error} onRetry={() => d.reload()} />
  const t = d.data!
  const fixtures = t.fixtures.filter(f => filter === 'all' || f.status === filter || (filter === 'scheduled' && f.status === 'live'))
  const setStatus = (status: string) => guard(async () => { await api.post(`/api/tournaments/${id}/status`, { status }); d.reload(true); onChanged() })
  const link = () => guard(async () => { if (!addTeam) return; await api.post(`/api/tournaments/${id}/teams`, { team_id: addTeam }); setAddTeam(0); d.reload(true); onChanged() })
  const outside = (all.data ?? []).filter(x => !t.teams.some(y => y.id === x.id))
  return (
    <div className="grid gap-4">
      <Panel title={t.name} meta={`${t.format} · ${t.overs} overs${t.venue ? ` · ${t.venue}` : ''}`}
             actions={<Segmented value={t.status} onChange={setStatus} label="Status" options={[{ value: 'upcoming', label: 'Upcoming' }, { value: 'active', label: 'Active' }, { value: 'completed', label: 'Completed' }]} />}>
        <div className="flex flex-wrap gap-x-8 gap-y-2 text-[13px] text-dim">
          <span>Dates <span className="num text-ink">{t.start_date || 'TBC'} to {t.end_date || 'TBC'}</span></span>
          <span>Teams <span className="num text-ink">{t.teams.length}</span></span>
          <span>Fixtures <span className="num text-ink">{t.fixtures.length}</span></span>
          <span>Played <span className="num text-ink">{t.fixtures.filter(f => f.status === 'completed').length}</span></span>
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <Panel title="Points table" className="xl:col-span-7" bodyClass="scroll-x">
          {t.table.length ? (
            <table className="table">
              <thead><tr><th>#</th><th>Team</th><th className="r">P</th><th className="r">W</th><th className="r">L</th><th className="r">T</th><th className="r">Pts</th><th className="r">NRR</th></tr></thead>
              <tbody>{t.table.map((r, i) => (
                <tr key={r.teamId}><td className="num text-dim">{i + 1}</td><td><Link to={`/teams/${r.teamId}`} className="hover:text-teal">{r.team}</Link> <span className="num text-xs text-dim">{r.short}</span></td>
                  <td className="num r">{r.p}</td><td className="num r">{r.w}</td><td className="num r">{r.l}</td><td className="num r">{r.t}</td><td className="num r font-semibold">{r.pts}</td>
                  <td className={`num r ${r.nrr > 0 ? 'text-teal' : r.nrr < 0 ? 'text-dim' : ''}`}>{r.nrr > 0 ? '+' : ''}{r.nrr.toFixed(3)}</td></tr>
              ))}</tbody>
            </table>
          ) : <div className="p-4"><Empty title="No teams entered" hint="Add registered teams to this tournament to build the table." /></div>}
        </Panel>
        <Panel title="Teams" className="xl:col-span-5" bodyClass="">
          {t.teams.map(x => (
            <Link key={x.id} to={`/teams/${x.id}`} className="flex items-baseline justify-between border-b border-rule px-4 py-2.5 hover:bg-raised">
              <span>{x.name}</span><span className="num text-xs text-dim">{x.short} · {x.city}</span>
            </Link>
          ))}
          <div className="flex gap-2 p-3">
            <select className="select" value={addTeam} onChange={e => setAddTeam(+e.target.value)} aria-label="Add team">
              <option value={0}>Add a registered team</option>{outside.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}
            </select>
            <button className="btn" disabled={!addTeam} onClick={link}>Add</button>
          </div>
        </Panel>
      </div>

      <Panel title="Fixtures" bodyClass="" actions={<>
        <Segmented value={filter} onChange={setFilter} label="Fixture filter" options={[{ value: 'all', label: 'All' }, { value: 'scheduled', label: 'Upcoming' }, { value: 'completed', label: 'Results' }]} />
        <button className="btn btn-sm btn-primary" onClick={() => guard(() => setModal(true))}>Schedule</button></>}>
        {fixtures.length ? fixtures.map(f => <MatchRow key={f.id} m={f} to={f.status === 'completed' ? `/analytics/${f.id}` : f.status === 'live' ? `/live/${f.id}` : `/score/${f.id}`} />) :
          <div className="p-4"><Empty title="No fixtures here" hint="Schedule a match between two of this tournament's teams." /></div>}
      </Panel>
      {modal && <ScheduleMatch tournamentId={id} onClose={() => setModal(false)} onDone={() => { setModal(false); d.reload(true) }} />}
    </div>
  )
}

export default function Tournaments() {
  const { id } = useParams()
  const nav = useNavigate()
  const list = useApi<Tournament[]>('/api/tournaments')
  const { guard } = useAdmin()
  const [create, setCreate] = useState(false)
  const tid = id ? +id : list.data?.[list.data.length - 1]?.id
  return (
    <Page title="Tournaments & fixtures" revealKey={tid} actions={<button className="btn btn-primary" onClick={() => guard(() => setCreate(true))}>Create tournament</button>}>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
        <Panel title="All tournaments" bodyClass="">
          {list.loading ? <div className="p-4"><SkeletonRows rows={3} /></div> : list.data?.length ? list.data.map(t => (
            <button key={t.id} onClick={() => nav(`/tournaments/${t.id}`)} className={`grid w-full gap-1 border-b border-rule px-4 py-3 text-left hover:bg-raised ${t.id === tid ? 'bg-raised text-teal' : ''}`}>
              <span className="font-medium">{t.name}</span>
              <span className="num text-xs text-dim">{t.format} · {t.teams} teams · {t.status}</span>
            </button>
          )) : <div className="p-4"><Empty title="No tournaments" hint="Create the first one." /></div>}
        </Panel>
        <div className="min-w-0">{tid ? <TournamentDetail id={tid} onChanged={() => list.reload(true)} /> : null}</div>
      </div>
      {create && <CreateTournament onClose={() => setCreate(false)} onDone={t => { setCreate(false); list.reload(true); nav(`/tournaments/${t.id}`) }} />}
    </Page>
  )
}
