import type { MatchState, MatchSummary } from './types'

export const overs = (balls: number) => `${Math.floor(balls / 6)}.${balls % 6}`
export const pct = (p: number) => `${(p * 100).toFixed(1)}%`

export function battingShort(s: Pick<MatchState, 'battingIsA' | 'teamA' | 'teamB'>) {
  return s.battingIsA ? s.teamA.short : s.teamB.short
}

export function when(iso: string | null) {
  if (!iso) return 'TBC'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function ago(iso: string | number | null) {
  if (!iso) return 'never'
  const t = typeof iso === 'number' ? iso * 1000 : new Date(iso).getTime()
  const s = Math.max(0, Math.round((Date.now() - t) / 1000))
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

export function scoreLine(s: MatchSummary | null) {
  if (!s) return null
  return `${s.runs}/${s.wkts}`
}

export function chipClass(c: string) {
  if (c === 'W') return 'chip chip-wkt'
  if (c === '.') return 'chip chip-dot'
  if (/[a-z]/i.test(c)) return 'chip chip-extra'
  return 'chip'
}

export const uptime = (s?: number) => {
  if (!s && s !== 0) return '-'
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return h ? `${h}h ${m}m` : `${m}m ${s % 60}s`
}
