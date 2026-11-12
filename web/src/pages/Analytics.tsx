import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Page, Panel, Empty, ErrorRow, Segmented, SkeletonRows, Stat } from '../components/ui'
import { Bars, Manhattan, Worm } from '../components/charts'
import { useApi } from '../lib/hooks'
import { overs } from '../lib/format'
import { teamVars } from '../lib/teams'
import type { MatchRow, PlayerStats, Usage } from '../lib/types'

type Inn = {
  team: string; batting: 'A' | 'B'; runs: number; wkts: number; worm: number[]; manhattan: number[]; wicketsPerOver: number[]
  phases: Record<'powerplay' | 'middle' | 'death', { runs: number; overs: number; rate: number | null }>
  fow: { runs: number; wkts: number; balls: number; player: string }[]
}

function MatchAnalysis({ id }: { id: number }) {
  const a = useApi<{ match: MatchRow; innings: Inn[] }>(`/api/matches/${id}/analytics`, [id])
  const [inn, setInn] = useState(0)
  if (a.loading && !a.data) return <SkeletonRows rows={3} h={160} />
  if (a.error) return <ErrorRow message={a.error} onRetry={() => a.reload()} />
  const { match, innings } = a.data!
  if (!innings.length || !innings.some(i => i.worm.length)) return <Empty title="No ball data for this match" hint="Analysis needs ball-by-ball data: scored or simulated matches. API matches carry totals only." />
  const cur = innings[Math.min(inn, innings.length - 1)]
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12" style={teamVars(match.teamA.short || match.teamA.name, match.teamB.short || match.teamB.name)}>
      <Panel title="Worm" meta={match.result || match.summary?.status} className="lg:col-span-7">
        <Worm innings={innings.map(i => ({ batting: i.batting, worm: i.worm, fow: i.fow }))} overs={match.overs} />
        <div className="mt-3 flex flex-wrap gap-5 text-[13px]">
          {innings.map((i, k) => <span key={k} className={i.batting === 'A' ? 'team-a' : 'team-b'}><span className="num">{i.runs}/{i.wkts}</span> <span className="text-dim">{i.team}</span></span>)}
        </div>
      </Panel>
      <Panel title="Phases" className="lg:col-span-5" bodyClass="scroll-x">
        <table className="table">
          <thead><tr><th>Phase</th>{innings.map((i, k) => <th key={k} className="r">{i.team}</th>)}</tr></thead>
          <tbody>{(['powerplay', 'middle', 'death'] as const).map(ph => (
            <tr key={ph}><td className="capitalize">{ph}</td>{innings.map((i, k) => <td key={k} className="num r">{i.phases[ph].overs ? `${i.phases[ph].runs} @ ${i.phases[ph].rate}` : '-'}</td>)}</tr>
          ))}</tbody>
        </table>
      </Panel>
      <Panel title="Runs per over" className="lg:col-span-7" actions={innings.length > 1 && <Segmented value={String(inn)} onChange={v => setInn(+v)} label="Innings" options={innings.map((i, k) => ({ value: String(k), label: i.team }))} />}>
        <Manhattan runs={cur.manhattan} wkts={cur.wicketsPerOver} batting={cur.batting} />
      </Panel>
      <Panel title="Fall of wickets" meta={cur.team} className="lg:col-span-5" bodyClass="max-h-80 overflow-y-auto">
        {cur.fow.length ? <table className="table"><tbody>{cur.fow.map(f => (
          <tr key={f.wkts}><td className="num text-dim">{f.wkts}</td><td>{f.player}</td><td className="num r">{f.runs}</td><td className="num r text-dim">{overs(f.balls)}</td></tr>
        ))}</tbody></table> : <p className="p-4 text-dim">No wickets fell.</p>}
      </Panel>
    </div>
  )
}

export default function Analytics() {
  const { id } = useParams()
  const nav = useNavigate()
  const ms = useApi<MatchRow[]>('/api/matches')
  const leaders = useApi<{ batters: PlayerStats[]; bowlers: PlayerStats[] }>('/api/leaders')
  const usage = useApi<{ current: Usage; byDay: { day: string; hits: number }[] }>('/api/usage')
  const options = (ms.data ?? []).filter(m => m.source !== 'api' && m.status !== 'scheduled')
  const mid = id ? +id : undefined
  useEffect(() => { if (!mid && options.length) nav(`/analytics/${options[0].id}`, { replace: true }) }, [mid, options, nav])
  return (
    <Page title="Analytics" revealKey={mid}
          actions={<select className="select !w-auto min-w-56" value={mid ?? ''} onChange={e => nav(`/analytics/${e.target.value}`)} aria-label="Match">
            {options.map(m => <option key={m.id} value={m.id}>{m.teamA.short} v {m.teamB.short} · {m.source} · {m.result || m.status}</option>)}
          </select>}>
      <div className="grid gap-4">
        {mid ? <MatchAnalysis id={mid} /> : ms.loading ? <SkeletonRows rows={2} h={160} /> :
          <Empty title="Nothing to analyse yet" hint="Complete a scored or simulated match." action={<Link className="btn btn-primary" to="/sim">Run a simulation</Link>} />}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <Panel title="Run leaders" className="lg:col-span-5" bodyClass="scroll-x">
            <table className="table"><thead><tr><th>Player</th><th className="r">Runs</th><th className="r">Avg</th><th className="r">SR</th></tr></thead>
              <tbody>{(leaders.data?.batters ?? []).map(p => <tr key={p.id}><td>{p.name} <span className="num text-xs text-dim">{p.team}</span></td><td className="num r">{p.runs}</td><td className="num r">{p.avg ?? '-'}</td><td className="num r">{p.sr ?? '-'}</td></tr>)}</tbody></table>
          </Panel>
          <Panel title="Wicket leaders" className="lg:col-span-4" bodyClass="scroll-x">
            <table className="table"><thead><tr><th>Player</th><th className="r">Wkts</th><th className="r">Econ</th></tr></thead>
              <tbody>{(leaders.data?.bowlers ?? []).map(p => <tr key={p.id}><td>{p.name} <span className="num text-xs text-dim">{p.team}</span></td><td className="num r">{p.wkts}</td><td className="num r">{p.econ ?? '-'}</td></tr>)}</tbody></table>
          </Panel>
          <Panel title="API credits" meta="Per day" className="lg:col-span-3">
            {usage.data?.byDay.length ? <Bars data={usage.data.byDay.map(d => ({ label: d.day.slice(5), value: d.hits }))} max={usage.data.current.hitsLimit} /> :
              <div className="grid gap-2"><Stat label="Today" value={`${usage.data?.current.hitsToday ?? 0}/${usage.data?.current.hitsLimit ?? 100}`} /><p className="text-xs text-dim">History appears after the first API call.</p></div>}
          </Panel>
        </div>
      </div>
    </Page>
  )
}
