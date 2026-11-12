import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowCounterClockwiseIcon, ArrowsLeftRightIcon } from '@phosphor-icons/react'
import { Page, Panel, Chips, Empty, ErrorRow, Field, Segmented, SkeletonRows, Stat } from '../components/ui'
import { MatchRow } from '../components/MatchRow'
import { ShowOnCyd } from './LiveCentre'
import { useApi } from '../lib/hooks'
import { useLive } from '../lib/live'
import { useAdmin } from '../lib/admin'
import { api } from '../lib/api'
import { overs } from '../lib/format'
import { teamVars } from '../lib/teams'
import type { MatchRow as Row, MatchState, Player } from '../lib/types'

type Detail = Row & { state: MatchState; xiA: number[]; xiB: number[]; squadA: Player[]; squadB: Player[]; pendingBowler: number | null; swapPending: boolean }
type Extra = 'none' | 'wd' | 'nb' | 'b' | 'lb'
const KINDS = ['caught', 'bowled', 'lbw', 'run out', 'stumped', 'hit wicket']

function StartForm({ d, onStarted }: { d: Detail; onStarted: () => void }) {
  const { guard } = useAdmin()
  const [toss, setToss] = useState<'A' | 'B'>('A')
  const [elected, setElected] = useState<'bat' | 'bowl'>('bat')
  const [pick, setPick] = useState(false)
  const [xi, setXi] = useState<{ A: number[]; B: number[] }>({ A: [], B: [] })
  const [err, setErr] = useState<string | null>(null)
  const toggle = (k: 'A' | 'B', id: number) => setXi(v => ({ ...v, [k]: v[k].includes(id) ? v[k].filter(x => x !== id) : v[k].length < 11 ? [...v[k], id] : v[k] }))
  const start = () => guard(async () => {
    setErr(null)
    try {
      await api.post(`/api/matches/${d.id}/start`, { toss_winner: toss, elected, xi_a: pick && xi.A.length ? xi.A : null, xi_b: pick && xi.B.length ? xi.B : null })
      onStarted()
    } catch (e) { setErr((e as Error).message) }
  })
  return (
    <Panel title="Toss and playing XI" meta={`${d.teamA.name} v ${d.teamB.name}`}>
      <div className="grid gap-5" style={teamVars(d.teamA.short || d.teamA.name, d.teamB.short || d.teamB.name)}>
        <div className="flex flex-wrap gap-6">
          <Field label="Toss won by"><Segmented value={toss} onChange={setToss} label="Toss" options={[{ value: 'A', label: d.teamA.short }, { value: 'B', label: d.teamB.short }]} /></Field>
          <Field label="Elected to"><Segmented value={elected} onChange={setElected} label="Elected" options={[{ value: 'bat', label: 'Bat' }, { value: 'bowl', label: 'Bowl' }]} /></Field>
          <Field label="Playing XI"><Segmented value={pick ? 'pick' : 'auto'} onChange={v => setPick(v === 'pick')} label="XI" options={[{ value: 'auto', label: 'Auto-pick' }, { value: 'pick', label: 'Choose' }]} /></Field>
        </div>
        {pick && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {(['A', 'B'] as const).map(k => {
              const squad = k === 'A' ? d.squadA : d.squadB
              return (
                <div key={k} className="border border-rule">
                  <div className="flex justify-between border-b border-rule px-3 py-2"><span className={k === 'A' ? 'team-a font-semibold' : 'team-b font-semibold'}>{k === 'A' ? d.teamA.short : d.teamB.short}</span><span className="num text-xs text-dim">{xi[k].length}/11 in batting order</span></div>
                  {squad.map(p => {
                    const pos = xi[k].indexOf(p.id)
                    return (
                      <button key={p.id} onClick={() => toggle(k, p.id)} className={`grid w-full grid-cols-[28px_1fr_48px_70px] items-center gap-2 border-b border-rule px-3 py-2 text-left text-[13px] last:border-b-0 hover:bg-raised ${pos >= 0 ? 'text-ink' : 'text-dim'}`}>
                        <span className="num text-teal">{pos >= 0 ? pos + 1 : ''}</span><span>{p.name}</span><span className="label">{p.role}</span><span className="num text-xs">{p.bat}/{p.bowl}</span>
                      </button>
                    )
                  })}
                </div>
              )
            })}
          </div>
        )}
        {err && <ErrorRow message={err} />}
        <div><button className="btn btn-primary" onClick={start}>Start live scoring</button></div>
      </div>
    </Panel>
  )
}

function Console({ d, s, reload }: { d: Detail; s: MatchState; reload: () => void }) {
  const { guard } = useAdmin()
  const [extra, setExtra] = useState<Extra>('none')
  const [wkt, setWkt] = useState(false)
  const [kind, setKind] = useState('caught')
  const [who, setWho] = useState<'striker' | 'non_striker'>('striker')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const bowlingXi = s.next?.innings === 2 || (s.innings === 2 && !s.inningsBreak) ? (s.battingIsA ? d.xiB : d.xiA) : (s.battingIsA ? d.xiB : d.xiA)
  const nextInnings2 = s.inningsBreak
  const bowlIds = nextInnings2 ? (s.battingIsA ? d.xiA : d.xiB) : bowlingXi
  const squad = useMemo(() => Object.fromEntries([...d.squadA, ...d.squadB].map(p => [p.id, p])), [d])
  const card = s.cards.at(-1)
  const figures = (pid: number) => card?.bowlers?.find(b => b.id === pid)
  const nextBowler = s.next?.bowler ?? null
  const strikerName = s.next ? squad[s.next.striker]?.name : s.striker.name
  const nonName = s.next ? squad[s.next.non_striker]?.name : s.nonStriker.name

  const send = useCallback((path: string, body: unknown = {}) => guard(async () => {
    setBusy(true); setErr(null)
    try { await api.post(`/api/matches/${d.id}/${path}`, body); setExtra('none'); setWkt(false); reload() }
    catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }), [d.id, guard, reload])

  const runs = (n: number) => {
    if (extra === 'wd') return send('ball', { extra_type: 'wd', extras: 1 + n })
    if (extra === 'nb') return send('ball', { extra_type: 'nb', runs_bat: n })
    if (extra === 'b' || extra === 'lb') return send('ball', { extra_type: extra, extras: Math.max(1, n) })
    return send('ball', { runs_bat: n })
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('input,select,textarea') || busy || s.ended) return
      if (/^[0-6]$/.test(e.key) && e.key !== '5') runs(+e.key)
      else if (e.key === 'w') setExtra(x => (x === 'wd' ? 'none' : 'wd'))
      else if (e.key === 'n') setExtra(x => (x === 'nb' ? 'none' : 'nb'))
      else if (e.key === 'x') setWkt(true)
      else if (e.key === 'u') send('undo')
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const batCls = s.battingIsA ? 'team-a' : 'team-b'
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12" style={teamVars(s.teamA.short || s.teamA.name, s.teamB.short || s.teamB.name)}>
      <Panel className="lg:col-span-5" title={<span className={batCls}>{s.battingIsA ? s.teamA.name : s.teamB.name}</span>} meta={s.inningsBreak ? 'Innings break' : `Innings ${s.innings}`}>
        <div className="grid gap-4">
          <div className="flex items-baseline gap-3"><span className="num text-[44px] font-medium leading-none">{s.runs}/{s.wkts}</span><span className="num text-lg text-dim">{overs(s.balls)} ov</span></div>
          <p>{s.status}</p>
          <div className="grid grid-cols-3 gap-4">
            <Stat label="CRR" value={s.crr.toFixed(2)} />
            <Stat label={s.target ? 'RRR' : 'Projected'} value={s.target ? (s.rrr ?? 0).toFixed(2) : s.projected ?? '-'} />
            <Stat label="Partnership" value={s.partnership ? s.partnership.runs : '-'} sub={s.partnership ? `${s.partnership.balls} b` : undefined} />
          </div>
          <div className="flex flex-wrap items-center gap-3"><span className="label">This over</span><Chips balls={s.thisOver} /></div>
        </div>
      </Panel>

      <Panel className="lg:col-span-7" title="Next delivery" meta={s.ended ? 'Match over' : s.next?.new_over ? 'New over, confirm the bowler' : 'Keys: 0-6 runs, w wide, n no-ball, x wicket, u undo'}>
        {s.ended ? (
          <Empty title={s.result} hint="The match is complete. Undo the last ball if it was entered by mistake." action={<div className="flex gap-2"><button className="btn" onClick={() => send('undo')}>Undo last ball</button><Link className="btn btn-primary" to={`/analytics/${d.id}`}>Analysis</Link></div>} />
        ) : (
          <div className="grid gap-5">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="grid gap-1"><span className="label">On strike</span><span className="font-semibold">{strikerName}<span className="text-teal"> *</span></span></div>
              <div className="grid gap-1"><span className="label">Non-striker</span><span className="text-dim">{nonName}</span></div>
              <div className="grid gap-1">
                <label className="label" htmlFor="bowler">Bowler</label>
                <select id="bowler" className="select" value={nextBowler ?? ''} disabled={!s.next?.new_over && !nextInnings2}
                        onChange={e => send('pending', { bowler: +e.target.value })}>
                  {bowlIds.map(pid => {
                    const f = figures(pid)
                    return <option key={pid} value={pid}>{squad[pid]?.name} {f ? `${overs(f.balls)}-${f.runs}-${f.wkts}` : ''}</option>
                  })}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
              {[0, 1, 2, 3, 4, 6].map(n => (
                <button key={n} disabled={busy} onClick={() => runs(n)}
                  className={`btn h-16 text-2xl num ${n === 4 || n === 6 ? 'btn-primary' : ''}`} aria-label={`${n} runs`}>{n === 0 ? '0' : n}</button>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <span className="label">Extra</span>
              <Segmented value={extra} onChange={setExtra} label="Extra" options={[
                { value: 'none', label: 'None' }, { value: 'wd', label: 'Wide' }, { value: 'nb', label: 'No-ball' }, { value: 'b', label: 'Bye' }, { value: 'lb', label: 'Leg bye' }]} />
              {extra !== 'none' && <span className="text-xs text-dim">{extra === 'wd' ? 'Pick runs run in addition to the wide' : extra === 'nb' ? 'Pick runs off the bat' : 'Pick runs run'}</span>}
            </div>

            {wkt ? (
              <div className="grid gap-3 border border-wicket/50 p-3">
                <div className="flex flex-wrap gap-1.5">{KINDS.map(k => <button key={k} className={`btn btn-sm ${kind === k ? 'btn-danger' : ''}`} onClick={() => setKind(k)}>{k}</button>)}</div>
                {kind === 'run out' && <Segmented value={who} onChange={setWho} label="Who is out" options={[{ value: 'striker', label: `${strikerName ?? 'Striker'} out` }, { value: 'non_striker', label: `${nonName ?? 'Non-striker'} out` }]} />}
                <div className="flex gap-2"><button className="btn" onClick={() => setWkt(false)}>Cancel</button>
                  <button className="btn btn-danger" disabled={busy} onClick={() => send('ball', { wicket: true, wicket_kind: kind, dismissed: kind === 'run out' ? who : 'striker' })}>Confirm wicket</button></div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                <button className="btn btn-danger" onClick={() => setWkt(true)}>Wicket</button>
                <button className="btn" onClick={() => send('pending', { swap: true })}><ArrowsLeftRightIcon size={16} weight="light" />Swap strike</button>
                <button className="btn" onClick={() => send('undo')} disabled={busy}><ArrowCounterClockwiseIcon size={16} weight="light" />Undo</button>
              </div>
            )}
            {err && <ErrorRow message={err} />}
          </div>
        )}
      </Panel>

      <Panel className="lg:col-span-12" title="Ball history"><Chips balls={s.recent} max={18} size="lg" /></Panel>
    </div>
  )
}

export default function Scoring() {
  const { id } = useParams()
  const nav = useNavigate()
  const mid = id ? +id : undefined
  const sched = useApi<Row[]>('/api/matches?status=scheduled')
  const live = useApi<Row[]>('/api/matches?status=live&source=local')
  const detail = useApi<Detail>(mid ? `/api/matches/${mid}` : null, [mid])
  const pushed = useLive(s => (mid ? s.matches[mid] : undefined))
  const s = pushed && detail.data?.status !== 'scheduled' ? pushed : detail.data?.state

  if (!mid) {
    const scorable = (sched.data ?? []).filter(m => m.source === 'local')
    return (
      <Page title="Scoring" sub="Pick a fixture to toss and score ball by ball. Every delivery goes live to the dashboard and, if selected, the CYD.">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Panel title="In progress" bodyClass="">
            {live.loading ? <div className="p-4"><SkeletonRows rows={2} /></div> : live.data?.length ? live.data.map(m => <MatchRow key={m.id} m={m} to={`/score/${m.id}`} />) :
              <div className="p-4"><Empty title="No match being scored" hint="Start one of the scheduled fixtures." /></div>}
          </Panel>
          <Panel title="Scheduled fixtures" bodyClass="">
            {sched.loading ? <div className="p-4"><SkeletonRows rows={4} /></div> : scorable.length ? scorable.map(m => <MatchRow key={m.id} m={m} to={`/score/${m.id}`} right={<span className="label">Toss</span>} />) :
              <div className="p-4"><Empty title="No fixtures scheduled" hint="Schedule a match from Overview or a tournament page first." action={<Link to="/" className="btn btn-sm">Overview</Link>} /></div>}
          </Panel>
        </div>
      </Page>
    )
  }

  return (
    <Page title="Scoring" revealKey={`${mid}-${detail.data?.status}`}
          sub={detail.data ? `${detail.data.teamA.name} v ${detail.data.teamB.name}${detail.data.toss ? ` · ${detail.data.toss}` : ''}` : undefined}
          actions={<><button className="btn" onClick={() => nav('/score')}>All fixtures</button>{detail.data && detail.data.status !== 'scheduled' && <ShowOnCyd matchId={mid} />}</>}>
      {detail.loading && !detail.data ? <SkeletonRows rows={3} h={140} /> :
        detail.error ? <ErrorRow message={detail.error} onRetry={() => detail.reload()} /> :
        detail.data?.source === 'api' ? <Empty title="CricketData matches are read-only" hint="Live international matches come from the API. Follow them in the Live Centre." action={<Link className="btn" to={`/live/${mid}`}>Live Centre</Link>} /> :
        detail.data?.status === 'scheduled' ? <StartForm d={detail.data} onStarted={() => detail.reload()} /> :
        detail.data && s ? <Console d={detail.data} s={s} reload={() => detail.reload(true)} /> : null}
    </Page>
  )
}
