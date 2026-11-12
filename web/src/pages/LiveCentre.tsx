import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { MonitorPlayIcon } from '@phosphor-icons/react'
import { Page, Panel, Chips, Empty, ErrorRow, Skeleton, SkeletonRows, Stat } from '../components/ui'
import { Seam } from '../components/Seam'
import { Gauge, Tick, Worm } from '../components/charts'
import { useApi } from '../lib/hooks'
import { useLive } from '../lib/live'
import { useAdmin } from '../lib/admin'
import { api } from '../lib/api'
import { overs } from '../lib/format'
import { teamVars } from '../lib/teams'
import type { MatchRow, MatchState } from '../lib/types'

type Detail = MatchRow & { state: MatchState }

export function ShowOnCyd({ matchId, sim = false }: { matchId: number; sim?: boolean }) {
  const { guard } = useAdmin()
  const source = useLive(s => s.device?.source)
  const online = useLive(s => s.device?.online)
  const [busy, setBusy] = useState(false)
  const kind = sim ? 'sim' : 'match'
  const showing = source?.kind === kind && source.match_id === matchId
  return (
    <button className={`btn ${showing ? 'btn-primary' : ''}`} disabled={busy || showing}
            title={online ? '' : 'The CYD is offline; it will pick this up when it reconnects'}
            onClick={() => guard(async () => { setBusy(true); try { await api.post('/api/device/source', { kind, match_id: matchId }) } finally { setBusy(false) } })}>
      <MonitorPlayIcon size={16} weight="light" />{showing ? 'On the CYD' : 'Show on CYD'}
    </button>
  )
}

export function Scoreboard({ s }: { s: MatchState }) {
  const bat = s.battingIsA ? s.teamA : s.teamB
  const bowl = s.battingIsA ? s.teamB : s.teamA
  const batCls = s.battingIsA ? 'team-a' : 'team-b'
  const bowlCls = s.battingIsA ? 'team-b' : 'team-a'
  const chase = s.innings >= 2 && s.target > 0
  const sr = (r: number, b: number) => (b ? ((r * 100) / b).toFixed(1) : '-')
  const econ = s.bowler.balls ? ((s.bowler.runs * 6) / s.bowler.balls).toFixed(2) : '-'
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12" style={teamVars(s.teamA.short || s.teamA.name, s.teamB.short || s.teamB.name)}>
      <Panel className="lg:col-span-7" title={<span><span className={batCls}>{bat.name}</span> <span className="text-dim">batting</span></span>}
             meta={`${s.format} · Innings ${s.innings}`}>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-[1fr_auto]">
          <div className="grid gap-2">
            <div className="flex items-baseline gap-1 leading-none">
              <Tick value={s.runs} className="text-[56px] font-medium tracking-tight" />
              <span className={`${batCls} text-[44px] font-light`}>/</span>
              <Tick value={s.wkts} className="text-[56px] font-medium tracking-tight" />
              <span className="num ml-3 text-xl text-dim">{overs(s.balls)}<span className="label ml-1">ov</span></span>
            </div>
            <p className="text-[14px]">{s.status}</p>
          </div>
          <div className="grid grid-cols-3 gap-5 sm:grid-cols-1 sm:gap-3 sm:border-l sm:border-rule sm:pl-5">
            {chase ? <>
              <Stat label="Target" value={s.target} />
              <Stat label="Need" value={<Tick value={s.need} />} sub={`off ${s.ballsLeft} balls`} />
              <Stat label="Balls left" value={<Tick value={s.ballsLeft} />} />
            </> : <>
              <Stat label="Projected" value={s.projected ?? '-'} sub={`par ${s.par}`} />
              <Stat label="Balls left" value={<Tick value={s.ballsLeft} />} />
              <Stat label="Extras" value={s.cards.at(-1)?.extras ?? 0} />
            </>}
          </div>
        </div>
      </Panel>

      <Panel className="lg:col-span-5" title="Rates" bodyClass="panel-body grid grid-cols-2 gap-2">
        <Gauge value={s.crr} max={15} label="Current RR" display={s.crr.toFixed(2)} />
        <Gauge value={chase ? s.rrr ?? 0 : (s.par * 6) / (s.totalBalls || 120)} max={15} label={chase ? 'Required RR' : 'Par RR'} display={chase ? (s.rrr ?? 0).toFixed(2) : ((s.par * 6) / (s.totalBalls || 120)).toFixed(2)}
               warn={chase && (s.rrr ?? 0) > s.crr + 2} />
      </Panel>

      {s.hasPlayers ? (
        <Panel className="lg:col-span-7" title="At the crease" bodyClass="scroll-x">
          <table className="table">
            <thead><tr><th>Batter</th><th className="r">R</th><th className="r">B</th><th className="r">4s</th><th className="r">6s</th><th className="r">SR</th></tr></thead>
            <tbody>
              {[{ b: s.striker, on: true }, { b: s.nonStriker, on: false }].map(({ b, on }) => b.name ? (
                <tr key={b.name}><td className={on ? 'font-semibold' : 'text-dim'}>{b.name}{on && <span className="ml-1 text-teal">*</span>}</td>
                  <td className="num r text-ink">{b.runs}</td><td className="num r">{b.balls}</td><td className="num r">{b.fours ?? 0}</td><td className="num r">{b.sixes ?? 0}</td><td className="num r">{sr(b.runs, b.balls)}</td></tr>
              ) : null)}
            </tbody>
          </table>
          <div className="grid grid-cols-2 gap-4 border-t border-rule p-4 sm:grid-cols-3">
            <Stat label="Partnership" value={s.partnership ? `${s.partnership.runs}` : '-'} sub={s.partnership ? `${s.partnership.balls} balls` : undefined} />
            <Stat label="Next in" value={<span className="font-sans text-[15px]">{s.nextBat || '-'}</span>} />
            <Stat label="Next over" value={<span className="font-sans text-[15px]">{s.nextBowl || '-'}</span>} />
          </div>
        </Panel>
      ) : (
        <Panel className="lg:col-span-7" title="At the crease">
          <Empty title="Player detail not in the free feed" hint="CricketData's free endpoint gives team scores and status only. Scored and simulated matches show batters and bowlers here." />
        </Panel>
      )}

      <Panel className="lg:col-span-5" title={<span><span className={bowlCls}>{bowl.short}</span> <span className="text-dim">bowling</span></span>}>
        {s.hasPlayers && s.bowler.name ? (
          <div className="grid gap-4">
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-semibold">{s.bowler.name}</span>
              <span className="num text-lg">{overs(s.bowler.balls)}-{s.bowler.maidens}-{s.bowler.runs}-{s.bowler.wkts}</span>
            </div>
            <div className="grid grid-cols-2 gap-4"><Stat label="Economy" value={econ} /><Stat label="This over" value={s.thisOver.length} sub="deliveries" /></div>
          </div>
        ) : <p className="text-dim">No bowler data.</p>}
      </Panel>

      <Panel className="lg:col-span-12" title="Ball history" meta={`Last ${Math.min(18, s.recent.length)} deliveries`}
             bodyClass="panel-body grid grid-cols-1 gap-4 md:grid-cols-[1fr_auto] md:items-center">
        <Chips balls={s.recent} max={18} size="lg" />
        <div className="flex items-center gap-3"><span className="label">This over</span><Chips balls={s.thisOver} max={10} /></div>
      </Panel>
    </div>
  )
}

export default function LiveCentre() {
  const { id } = useParams()
  const nav = useNavigate()
  const list = useApi<MatchRow[]>('/api/matches')
  const mid = id ? +id : undefined
  const detail = useApi<Detail>(mid ? `/api/matches/${mid}` : null, [mid])
  const live = useLive(s => (mid ? s.matches[mid] : undefined))

  useEffect(() => {
    if (mid || !list.data?.length) return
    const pick = list.data.find(m => m.status === 'live') ?? list.data.find(m => m.status === 'completed')
    if (pick) nav(`/live/${pick.id}`, { replace: true })
  }, [mid, list.data, nav])

  const s = live ?? detail.data?.state
  const options = (list.data ?? []).filter(m => m.status !== 'scheduled')

  return (
    <Page title="Live Centre" revealKey={mid}
          sub={detail.data ? `${detail.data.teamA.name} v ${detail.data.teamB.name}${detail.data.venue ? ` · ${detail.data.venue}` : ''}` : 'Follow any match ball by ball.'}
          actions={<>
            <select className="select !w-auto min-w-56" value={mid ?? ''} onChange={e => nav(`/live/${e.target.value}`)} aria-label="Match">
              {!mid && <option value="">Choose a match</option>}
              {options.map(m => <option key={m.id} value={m.id}>{m.status === 'live' ? 'LIVE  ' : ''}{m.teamA.short} v {m.teamB.short} · {m.source}{m.result ? ` · ${m.result}` : ''}</option>)}
            </select>
            {mid && <ShowOnCyd matchId={mid} />}
            {detail.data?.source === 'local' && detail.data.status === 'live' && <Link to={`/score/${mid}`} className="btn">Open scorer</Link>}
          </>}>
      {list.error && <ErrorRow message={list.error} onRetry={() => list.reload()} />}
      {!mid && list.data && options.length === 0 && (
        <Empty title="No matches to follow yet" hint="Start scoring a fixture or run a simulation; it shows up here instantly." action={<Link className="btn btn-primary" to="/sim">Run a simulation</Link>} />
      )}
      {mid && !s && (detail.loading ? <div className="grid gap-4"><Skeleton h={130} /><SkeletonRows rows={3} h={120} /></div> :
        detail.error ? <ErrorRow message={detail.error} onRetry={() => detail.reload()} /> :
        <Empty title="This match has not started" hint="Open it in the scoring console to toss and start." action={<Link className="btn btn-primary" to={`/score/${mid}`}>Open scorer</Link>} />)}
      {s && s.teamA && (
        <div className="grid gap-4" style={teamVars(s.teamA.short || s.teamA.name, s.teamB.short || s.teamB.name)}>
          <section className="panel overflow-hidden" data-reveal>
            <div className="flex items-center justify-between gap-3 border-b border-rule px-4 py-2.5">
              <span className="flex items-baseline gap-2"><span className="team-a font-semibold">{s.teamA.short}</span><span className="text-dim">v</span><span className="team-b font-semibold">{s.teamB.short}</span></span>
              <span className="label">{s.live ? 'Momentum' : s.result || 'Final'}</span>
            </div>
            <Seam winA={s.winA} height={132} event={s.lastEvent} eventSeq={s.eventSeq} battingIsA={s.battingIsA} labelA={s.teamA.short} labelB={s.teamB.short} />
          </section>
          <Scoreboard s={s} />
          {s.cards?.some(c => c.worm?.length) && (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
              <Panel title="Worm" meta="Cumulative runs by over · squares mark wickets" className="lg:col-span-7">
                <Worm innings={s.cards.filter(c => c.worm).map(c => ({ batting: c.batting, worm: c.worm!, fow: c.fow }))} overs={s.totalBalls / 6 || 20} />
              </Panel>
              <Panel title="Fall of wickets" meta={s.cards.at(-1)?.team} className="lg:col-span-5" bodyClass="max-h-80 overflow-y-auto">
                {s.cards.at(-1)?.fow?.length ? <table className="table"><tbody>{s.cards.at(-1)!.fow!.map(f => (
                  <tr key={f.wkts}><td className="num text-dim">{f.wkts}-{f.runs}</td><td>{f.player}</td><td className="num r text-dim">{overs(f.balls)}</td></tr>
                ))}</tbody></table> : <p className="p-4 text-dim">No wickets yet.</p>}
              </Panel>
            </div>
          )}
        </div>
      )}
    </Page>
  )
}
