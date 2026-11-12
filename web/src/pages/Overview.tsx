import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CalendarPlusIcon, ChartLineIcon, ClipboardTextIcon, TrophyIcon, UsersThreeIcon, type Icon } from '@phosphor-icons/react'
import { Page, Panel, Empty, ErrorRow, SkeletonRows, Segmented, Stat } from '../components/ui'
import { MatchRow } from '../components/MatchRow'
import { Gauge, Tick } from '../components/charts'
import { CreateTournament, RegisterTeam, ScheduleMatch } from '../components/forms'
import { useApi, useRefreshOn } from '../lib/hooks'
import { useLive } from '../lib/live'
import { useAdmin } from '../lib/admin'
import { ago } from '../lib/format'
import type { Overview as OV, PlayerStats } from '../lib/types'

function QuickAction({ icon: I, label, hint, onClick }: { icon: Icon; label: string; hint: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="group flex min-h-16 items-center gap-3 border-r border-b border-rule px-4 py-3 text-left hover:bg-raised active:translate-y-px sm:border-b-0">
      <I size={22} weight="light" className="shrink-0 text-teal" />
      <span className="grid">
        <span className="text-[14px] font-medium">{label}</span>
        <span className="text-xs text-dim">{hint}</span>
      </span>
    </button>
  )
}

function Leaders({ top }: { top: OV['top'] }) {
  const [tab, setTab] = useState<'runs' | 'wkts' | 'sr'>('runs')
  const rows: PlayerStats[] = tab === 'runs' ? top.batters : tab === 'wkts' ? top.bowlers : top.strikeRate
  return (
    <Panel title="Top performers" meta="All scored and simulated matches"
           actions={<Segmented value={tab} onChange={setTab} label="Leaderboard" options={[{ value: 'runs', label: 'Runs' }, { value: 'wkts', label: 'Wickets' }, { value: 'sr', label: 'Strike rate' }]} />}
           bodyClass="scroll-x">
      {rows.length === 0 ? <div className="p-4"><Empty title="No figures yet" hint="Score or simulate a match and the leaders appear here." /></div> : (
        <table className="table">
          <thead><tr><th>#</th><th>Player</th><th>Team</th><th className="r">M</th>
            {tab === 'wkts' ? <><th className="r">Wkts</th><th className="r">Overs</th><th className="r">Econ</th></> :
              <><th className="r">Runs</th><th className="r">Balls</th><th className="r">SR</th></>}</tr></thead>
          <tbody>{rows.map((p, i) => (
            <tr key={p.id}><td className="num text-dim">{i + 1}</td><td className="font-medium">{p.name}</td><td className="num text-dim">{p.team}</td><td className="num r">{p.matches}</td>
              {tab === 'wkts' ? <><td className="num r text-ink">{p.wkts}</td><td className="num r">{p.overs}</td><td className="num r">{p.econ ?? '-'}</td></> :
                <><td className="num r text-ink">{p.runs}</td><td className="num r">{p.balls}</td><td className="num r">{p.sr ?? '-'}</td></>}</tr>
          ))}</tbody>
        </table>
      )}
    </Panel>
  )
}

export default function Overview() {
  const { data, error, loading, reload } = useApi<OV>('/api/overview')
  const activityTick = useLive(s => s.activity.length)
  const liveActivity = useLive(s => s.activity)
  const usage = useLive(s => s.usage)
  const device = useLive(s => s.device)
  const { guard } = useAdmin()
  const nav = useNavigate()
  const [modal, setModal] = useState<null | 'tournament' | 'match' | 'team'>(null)
  useRefreshOn(activityTick, () => reload(true))

  const activity = [...liveActivity, ...(data?.activity ?? [])].filter((a, i, arr) => arr.findIndex(b => b.id === a.id) === i).slice(0, 14)
  const done = () => { setModal(null); reload(true) }

  return (
    <Page title="Overview" sub="Every match, tournament and device on the platform, as it happens.">
      <div className="panel mb-4 grid grid-cols-1 sm:grid-cols-5" data-reveal>
        <QuickAction icon={TrophyIcon} label="Create tournament" hint="Format, teams, dates" onClick={() => guard(() => setModal('tournament'))} />
        <QuickAction icon={CalendarPlusIcon} label="Schedule match" hint="Add a fixture" onClick={() => guard(() => setModal('match'))} />
        <QuickAction icon={ClipboardTextIcon} label="Start live scoring" hint="Ball-by-ball console" onClick={() => nav('/score')} />
        <QuickAction icon={UsersThreeIcon} label="Register team" hint="Squad and manager" onClick={() => guard(() => setModal('team'))} />
        <QuickAction icon={ChartLineIcon} label="View analytics" hint="Worms, phases, leaders" onClick={() => nav('/analytics')} />
      </div>

      {error && <div className="mb-4"><ErrorRow message={`Could not load the overview: ${error}`} onRetry={() => reload()} /></div>}

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-12">
        <Panel title="Live now" meta={data ? `${data.live.length} in progress` : undefined} className="lg:col-span-8" bodyClass=""
               actions={<Link className="btn btn-sm" to="/live">Live Centre</Link>}>
          {loading && !data ? <div className="p-4"><SkeletonRows rows={3} h={54} /></div> :
            data && data.live.length === 0 ? <div className="p-4"><Empty title="Nothing live right now"
              hint="Start scoring a scheduled fixture, run a simulation, or add a CricketData key to follow international matches."
              action={<div className="flex gap-2"><Link to="/score" className="btn btn-primary btn-sm">Start scoring</Link><Link to="/sim" className="btn btn-sm">Run a simulation</Link></div>} /></div> :
            data?.live.map(m => <MatchRow key={m.id} m={m} to={`/live/${m.id}`} />)}
        </Panel>

        <div className="grid gap-4 lg:col-span-4">
          <Panel title="Platform">
            {data ? (
              <div className="grid grid-cols-3 gap-4">
                <Stat label="Teams" value={<Tick value={data.counts.teams} />} />
                <Stat label="Players" value={<Tick value={data.counts.players} />} />
                <Stat label="Matches" value={<Tick value={data.counts.matches} />} />
              </div>
            ) : <SkeletonRows rows={1} h={44} />}
          </Panel>
          <Panel title="Links" bodyClass="panel-body grid grid-cols-2 items-center gap-4">
            <Gauge value={usage?.hitsToday ?? 0} max={usage?.hitsLimit ?? 100} label="API credits today"
                   display={`${usage?.hitsToday ?? 0}/${usage?.hitsLimit ?? 100}`} warn={(usage?.hitsToday ?? 0) / (usage?.hitsLimit || 100) > 0.8} />
            <div className="grid gap-3">
              <Stat label="CYD" value={<span className={`font-sans text-[15px] ${device?.online ? 'text-teal' : 'text-dim'}`}>{device?.online ? 'Online' : 'Offline'}</span>}
                    sub={device?.online ? `${device.telemetry?.fps ?? '-'} fps, ${device.telemetry?.rssi ?? '-'} dBm` : 'Waiting for the scoreboard to connect'} />
              <Stat label="Showing" value={<span className="font-sans text-[15px]">{device?.source?.kind === 'sim' ? 'Screen 2 · simulation' : device?.source?.kind === 'match' ? (device.telemetry?.showing || 'Match') : 'Screen 1 · live'}</span>} />
              <Link to="/device" className="btn btn-sm">Device control</Link>
            </div>
          </Panel>
        </div>

        <Panel title="Upcoming fixtures" className="lg:col-span-7" bodyClass="" actions={<button className="btn btn-sm" onClick={() => guard(() => setModal('match'))}>Schedule</button>}>
          {loading && !data ? <div className="p-4"><SkeletonRows rows={4} /></div> :
            data?.upcoming.length ? data.upcoming.map(m => <MatchRow key={m.id} m={m} to={`/score/${m.id}`} right={<span className="label">Score it</span>} />) :
            <div className="p-4"><Empty title="No fixtures scheduled" hint="Schedule a match between two registered teams to see it here." /></div>}
        </Panel>

        <Panel title="Recent results" className="lg:col-span-5" bodyClass="">
          {loading && !data ? <div className="p-4"><SkeletonRows rows={4} /></div> :
            data?.recent.length ? data.recent.map(m => <MatchRow key={m.id} m={m} to={`/analytics/${m.id}`} right={<span className="label">Analysis</span>} />) :
            <div className="p-4"><Empty title="No completed matches" hint="Results appear here when a scored or simulated match ends." /></div>}
        </Panel>

        <Panel title="Active tournaments" className="lg:col-span-5" bodyClass="">
          {data?.tournaments.length ? data.tournaments.map(t => (
            <Link key={t.id} to={`/tournaments/${t.id}`} className="grid gap-2 border-b border-rule px-4 py-3 last:border-b-0 hover:bg-raised">
              <div className="flex items-baseline justify-between gap-3"><span className="font-medium">{t.name}</span><span className={`label ${t.status === 'active' ? 'text-teal' : ''}`}>{t.status}</span></div>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-[13px] text-dim">
                <span className="num">{t.format} · {t.overs} ov</span><span className="num">{t.teams} teams</span>
                <span className="num">{t.played}/{t.fixtures} played</span>{t.leader && <span>Leader <span className="num text-ink">{t.leader}</span></span>}
              </div>
              <div className="h-1 bg-raised"><div className="h-full origin-left bg-teal" style={{ transform: `scaleX(${t.fixtures ? (t.played ?? 0) / t.fixtures : 0})` }} /></div>
            </Link>
          )) : loading ? <div className="p-4"><SkeletonRows rows={2} h={60} /></div> :
            <div className="p-4"><Empty title="No active tournaments" hint="Create one and enter registered teams." action={<button className="btn btn-sm btn-primary" onClick={() => guard(() => setModal('tournament'))}>Create tournament</button>} /></div>}
        </Panel>

        <div className="lg:col-span-7">{data ? <Leaders top={data.top} /> : <Panel title="Top performers"><SkeletonRows rows={5} h={30} /></Panel>}</div>

        <Panel title="Recent activity" className="lg:col-span-12" bodyClass="">
          {activity.length ? (
            <ol className="grid grid-cols-1 sm:grid-cols-2">
              {activity.map(a => (
                <li key={a.id} className="grid grid-cols-[78px_84px_1fr] items-baseline gap-3 border-b border-rule px-4 py-2 text-[13px] sm:odd:border-r">
                  <span className="num text-xs text-dim">{ago(a.ts)}</span><span className="label">{a.kind}</span><span className="truncate">{a.text}</span>
                </li>
              ))}
            </ol>
          ) : <div className="p-4"><SkeletonRows rows={3} h={24} /></div>}
        </Panel>
      </div>

      {modal === 'tournament' && <CreateTournament onClose={() => setModal(null)} onDone={done} />}
      {modal === 'match' && <ScheduleMatch onClose={() => setModal(null)} onDone={done} />}
      {modal === 'team' && <RegisterTeam onClose={() => setModal(null)} onDone={done} />}
    </Page>
  )
}
