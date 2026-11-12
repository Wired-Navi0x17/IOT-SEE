import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Page, Panel, Empty, ErrorRow, SkeletonRows, Segmented } from '../components/ui'
import { AddPlayer, RegisterTeam } from '../components/forms'
import { useApi } from '../lib/hooks'
import { useAdmin } from '../lib/admin'
import type { Player, Team } from '../lib/types'

type Detail = Team & { players: Player[] }
const ROLE: Record<string, string> = { BAT: 'Batter', BOWL: 'Bowler', AR: 'All-rounder', WK: 'Keeper' }

function Rating({ v }: { v: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="relative h-1 w-14 bg-raised"><span className="absolute inset-0 origin-left bg-teal/80" style={{ transform: `scaleX(${v / 100})` }} /></span>
      <span className="num w-6 text-right text-xs">{v}</span>
    </span>
  )
}

function TeamDetail({ id }: { id: number }) {
  const d = useApi<Detail>(`/api/teams/${id}`, [id])
  const { guard } = useAdmin()
  const [add, setAdd] = useState(false)
  const [view, setView] = useState<'squad' | 'figures'>('squad')
  if (d.loading && !d.data) return <SkeletonRows rows={6} h={36} />
  if (d.error) return <ErrorRow message={d.error} onRetry={() => d.reload()} />
  const t = d.data!
  return (
    <Panel title={t.name} meta={`${t.short} · ${t.city || 'No city'}${t.manager ? ` · Manager ${t.manager}` : ''}`} bodyClass="scroll-x"
           actions={<><Segmented value={view} onChange={setView} label="View" options={[{ value: 'squad', label: 'Squad' }, { value: 'figures', label: 'Figures' }]} />
             <button className="btn btn-sm btn-primary" onClick={() => guard(() => setAdd(true))}>Add player</button></>}>
      {t.players.length === 0 ? <div className="p-4"><Empty title="No players registered" hint="Add at least 11 players so the team can play and be simulated." /></div> : (
        <table className="table">
          {view === 'squad' ? <>
            <thead><tr><th>Player</th><th>Role</th><th>Style</th><th>Batting</th><th>Bowling</th></tr></thead>
            <tbody>{t.players.map(p => (
              <tr key={p.id}><td className="font-medium">{p.name}</td><td className="text-dim">{ROLE[p.role]}</td><td className="num text-dim">{p.style || '-'}</td><td><Rating v={p.bat} /></td><td><Rating v={p.bowl} /></td></tr>
            ))}</tbody>
          </> : <>
            <thead><tr><th>Player</th><th className="r">M</th><th className="r">Runs</th><th className="r">Avg</th><th className="r">SR</th><th className="r">4s/6s</th><th className="r">Wkts</th><th className="r">Econ</th></tr></thead>
            <tbody>{t.players.map(p => {
              const s = p.stats
              return (
                <tr key={p.id}><td className="font-medium">{p.name}</td><td className="num r">{s?.matches ?? 0}</td><td className="num r">{s?.runs ?? 0}</td><td className="num r">{s?.avg ?? '-'}</td>
                  <td className="num r">{s?.sr ?? '-'}</td><td className="num r">{s ? `${s.fours}/${s.sixes}` : '-'}</td><td className="num r">{s?.wkts ?? 0}</td><td className="num r">{s?.econ ?? '-'}</td></tr>
              )
            })}</tbody>
          </>}
        </table>
      )}
      {add && <AddPlayer teamId={id} onClose={() => setAdd(false)} onDone={() => { setAdd(false); d.reload(true) }} />}
    </Panel>
  )
}

export default function Teams() {
  const { id } = useParams()
  const nav = useNavigate()
  const list = useApi<Team[]>('/api/teams')
  const { guard } = useAdmin()
  const [reg, setReg] = useState(false)
  const tid = id ? +id : list.data?.[0]?.id
  return (
    <Page title="Teams & players" revealKey={tid} actions={<button className="btn btn-primary" onClick={() => guard(() => setReg(true))}>Register team</button>}>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
        <Panel title="Registered teams" meta={list.data ? `${list.data.length}` : undefined} bodyClass="">
          {list.loading ? <div className="p-4"><SkeletonRows rows={6} h={30} /></div> : list.data?.length ? list.data.map(t => (
            <button key={t.id} onClick={() => nav(`/teams/${t.id}`)} className={`flex w-full items-baseline justify-between border-b border-rule px-4 py-2.5 text-left hover:bg-raised ${t.id === tid ? 'bg-raised text-teal' : ''}`}>
              <span>{t.name}</span><span className="num text-xs text-dim">{t.players} pl</span>
            </button>
          )) : <div className="p-4"><Empty title="No teams" hint="Register the first team." /></div>}
        </Panel>
        <div className="min-w-0">{tid ? <TeamDetail id={tid} /> : null}</div>
      </div>
      {reg && <RegisterTeam onClose={() => setReg(false)} onDone={t => { setReg(false); list.reload(true); nav(`/teams/${t.id}`) }} />}
    </Page>
  )
}
