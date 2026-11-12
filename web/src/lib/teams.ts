// The 10 IPL franchises and their match colours.
// Team A shows its primary; Team B shows its primary unless it is too close to Team A's,
// then its alternate (MI v DC = blue v red, RCB v PBKS = red v silver).
// Keep identical to hub/src/cricket_hub/ipl.py and cricket_scoreboard/ipl_teams.cpp.
import type { CSSProperties } from 'react'

type Team = { name: string; primary: string; alt: string; aliases?: string[] }
export const IPL: Record<string, Team> = {
  CSK: { name: 'Chennai Super Kings', primary: '#F9CD05', alt: '#3E6FD9' },
  DC: { name: 'Delhi Capitals', primary: '#2F6FE0', alt: '#E5323B', aliases: ['Delhi Daredevils'] },
  GT: { name: 'Gujarat Titans', primary: '#6F8FD4', alt: '#D9B65C' },
  KKR: { name: 'Kolkata Knight Riders', primary: '#9B5CF0', alt: '#E0B23A' },
  LSG: { name: 'Lucknow Super Giants', primary: '#2EA8E6', alt: '#F28B30' },
  MI: { name: 'Mumbai Indians', primary: '#1F7FE8', alt: '#D9AE3E' },
  PBKS: { name: 'Punjab Kings', primary: '#E5323B', alt: '#C3CAD1', aliases: ['Kings XI Punjab', 'KXIP'] },
  RR: { name: 'Rajasthan Royals', primary: '#EA1A85', alt: '#3D6BE0' },
  RCB: { name: 'Royal Challengers Bengaluru', primary: '#D9262C', alt: '#D4AF37', aliases: ['Royal Challengers Bangalore'] },
  SRH: { name: 'Sunrisers Hyderabad', primary: '#F7752A', alt: '#B8BEC4' },
}
export const FALLBACK = { A: '#A974E8', B: '#38C9B4' }
const CLASH = 150

const key = (s: string) => s.toLowerCase().replace(/[^a-z]/g, '')
const ALIAS = new Map<string, string>()
for (const [code, t] of Object.entries(IPL)) for (const k of [code, t.name, ...(t.aliases ?? [])]) ALIAS.set(key(k), code)

export function teamCode(nameOrShort?: string | null) { return nameOrShort ? ALIAS.get(key(nameOrShort)) ?? null : null }

const rgb = (h: string) => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16))
export function distance(c1: string, c2: string) {
  const [r1, g1, b1] = rgb(c1), [r2, g2, b2] = rgb(c2), rm = (r1 + r2) / 2
  const dr = r1 - r2, dg = g1 - g2, db = b1 - b2
  return Math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db)
}

export function pairColors(a?: string | null, b?: string | null): { A: string; B: string } {
  const ca = teamCode(a), cb = teamCode(b)
  const A = ca ? IPL[ca].primary : FALLBACK.A
  if (!cb) return { A, B: distance(A, FALLBACK.B) >= CLASH ? FALLBACK.B : FALLBACK.A }
  const { primary, alt } = IPL[cb]
  if (distance(A, primary) >= CLASH) return { A, B: primary }
  return { A, B: distance(A, alt) >= distance(A, primary) ? alt : primary }
}

/** Inline style that re-points .team-a / .team-b / bg-team-* for everything inside one match. */
export function teamVars(a?: string | null, b?: string | null): CSSProperties {
  const c = pairColors(a, b)
  return { '--color-team-a': c.A, '--color-team-b': c.B } as CSSProperties
}

export const hexToInt = (h: string) => parseInt(h.slice(1), 16)
