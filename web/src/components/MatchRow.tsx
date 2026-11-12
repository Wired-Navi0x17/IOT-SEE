import { Link } from 'react-router-dom'
import type { MatchRow as Row } from '../lib/types'
import { overs, when } from '../lib/format'
import { MiniSeam } from './Seam'
import { useLive } from '../lib/live'
import { teamVars } from '../lib/teams'

const SOURCE: Record<string, string> = { local: 'Local', sim: 'Sim', api: 'CricketData' }

export function MatchRow({ m, to, right }: { m: Row; to?: string; right?: React.ReactNode }) {
  const live = useLive(s => s.matches[m.id])
  const s = live ?? m.summary
  const cards = s?.cards ?? []
  const body = (
    <div className="grid gap-2 px-3 py-3 hover:bg-raised" style={teamVars(m.teamA.short || m.teamA.name, m.teamB.short || m.teamB.name)}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="team-a font-semibold">{m.teamA.short}</span>
          <span className="text-xs text-dim">v</span>
          <span className="team-b font-semibold">{m.teamB.short}</span>
          <span className="label ml-2 hidden truncate sm:inline">{SOURCE[m.source]}{m.series ? ` · ${m.series}` : ''}</span>
        </div>
        {right ?? (m.status === 'live' && <span className="flex items-center gap-1.5"><span className="dot live-dot" /><span className="label text-ink">Live</span></span>)}
      </div>
      {m.status === 'scheduled' ? (
        <div className="flex flex-wrap justify-between gap-2 text-[13px] text-dim">
          <span className="num">{when(m.scheduledAt)}</span><span className="truncate">{m.venue}</span>
        </div>
      ) : s ? (
        <>
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <div className="flex gap-4">
              {cards.length ? cards.map((c, i) => (
                <span key={i} className="num text-[15px]">
                  <span className={(c.batting ?? (i ? 'B' : 'A')) === 'A' ? 'team-a' : 'team-b'}>{c.runs}/{c.wkts}</span>
                  <span className="ml-1 text-xs text-dim">({overs(c.balls)})</span>
                </span>
              )) : <span className="num text-[15px]">{s.runs}/{s.wkts} <span className="text-xs text-dim">({overs(s.balls)})</span></span>}
            </div>
            <span className="max-w-full truncate text-[13px] text-dim">{m.status === 'completed' ? m.result || s.status : s.status}</span>
          </div>
          {m.status === 'live' && <MiniSeam winA={s.winA ?? 0.5} />}
        </>
      ) : <span className="text-[13px] text-dim">Waiting for first update</span>}
    </div>
  )
  return to ? <Link to={to} className="block border-b border-rule last:border-b-0">{body}</Link> : <div className="border-b border-rule last:border-b-0">{body}</div>
}
