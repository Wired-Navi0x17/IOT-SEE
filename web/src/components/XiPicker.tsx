import { ArrowDownIcon, ArrowUpIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { useApi } from '../lib/hooks'
import { api } from '../lib/api'
import type { Player, Team } from '../lib/types'

export type XiChoice = { xi: number[]; bowlers: number[] }

const ROLE: Record<string, string> = { BAT: 'Bat', BOWL: 'Bowl', AR: 'All-rounder', WK: 'Keeper' }

/** Pick a team's playing XI, its batting order (top = opener) and who is allowed to bowl. */
export function XiPicker({ teamId, label, value, onChange }: {
  teamId: number; label: string; value: XiChoice | null; onChange: (v: XiChoice) => void
}) {
  const team = useApi<Team & { players: Player[] }>(teamId ? `/api/teams/${teamId}` : null, [teamId])
  const [loaded, setLoaded] = useState(0)
  useEffect(() => {
    if (!teamId || loaded === teamId) return
    api.get<XiChoice>(`/api/teams/${teamId}/default_xi`).then(v => { setLoaded(teamId); onChange(v) }).catch(() => {})
  }, [teamId, loaded, onChange])

  const players = team.data?.players ?? []
  const byId = new Map(players.map(p => [p.id, p]))
  const xi = value?.xi ?? []
  const bowlers = new Set(value?.bowlers ?? [])
  const bench = players.filter(p => !xi.includes(p.id))
  const set = (next: number[], bw = bowlers) => onChange({ xi: next, bowlers: [...bw].filter(id => next.includes(id)) })
  const move = (i: number, d: number) => { const n = [...xi]; [n[i], n[i + d]] = [n[i + d], n[i]]; set(n) }
  const toggleBowl = (id: number) => { const b = new Set(bowlers); if (b.has(id)) b.delete(id); else b.add(id); set(xi, b) }

  return (
    <div className="grid gap-2">
      <div className="flex items-baseline justify-between">
        <span className="label">{label}</span>
        <span className={`label ${xi.length === 11 ? 'text-dim' : 'text-warn'}`}>{xi.length}/11 · {bowlers.size} bowling</span>
      </div>
      <ol className="grid gap-1">
        {xi.map((id, i) => {
          const p = byId.get(id)
          return (
            <li key={id} className="flex items-center gap-2 rounded border border-rule px-2 py-1 text-[13px]">
              <span className="num w-5 text-right text-dim">{i + 1}</span>
              <span className="min-w-0 flex-1 truncate">{p?.name ?? `#${id}`} <span className="text-dim">{p ? ROLE[p.role] : ''}</span></span>
              <label className="flex items-center gap-1 text-xs text-dim" title="Allowed to bowl">
                <input type="checkbox" checked={bowlers.has(id)} onChange={() => toggleBowl(id)} className="accent-[#4DB6C4]" />bowls
              </label>
              <button className="btn btn-sm px-1" disabled={i === 0} onClick={() => move(i, -1)} aria-label="Bat earlier"><ArrowUpIcon size={12} /></button>
              <button className="btn btn-sm px-1" disabled={i === xi.length - 1} onClick={() => move(i, 1)} aria-label="Bat later"><ArrowDownIcon size={12} /></button>
              <button className="btn btn-sm px-1.5" onClick={() => set(xi.filter(x => x !== id))} aria-label="Drop from XI">×</button>
            </li>
          )
        })}
      </ol>
      {bench.length > 0 && (
        <select className="select" value="" disabled={xi.length >= 11} onChange={e => e.target.value && set([...xi, +e.target.value])} aria-label={`Add to ${label}`}>
          <option value="">{xi.length >= 11 ? 'XI full' : 'Add player from squad…'}</option>
          {bench.map(p => <option key={p.id} value={p.id}>{p.name} · {ROLE[p.role]}</option>)}
        </select>
      )}
    </div>
  )
}
