export type TeamRef = { id: number | null; name: string; short: string }
export type BatterLine = { id?: number | null; name: string; runs: number; balls: number; fours?: number; sixes?: number }
export type BowlerLine = { id?: number | null; name: string; balls: number; maidens: number; runs: number; wkts: number }

export type Card = {
  batting?: 'A' | 'B'; team: string; runs: number; wkts: number; balls: number; extras?: number
  batters?: (BatterLine & { out: boolean; how: string })[]
  bowlers?: (BowlerLine & { id: number })[]
  over_runs?: number[]; over_wkts?: number[]; worm?: number[]
  fow?: { runs: number; wkts: number; balls: number; player: string }[]
}

export type MatchState = {
  matchId?: number; source?: string; format: string; series: string; venue?: string
  teamA: TeamRef; teamB: TeamRef; battingIsA: boolean; innings: number
  runs: number; wkts: number; balls: number; totalBalls: number; target: number; need: number; ballsLeft: number
  crr: number; rrr: number | null; projected: number | null; par: number
  striker: BatterLine; nonStriker: BatterLine; bowler: BowlerLine
  partnership: { runs: number; balls: number } | null
  nextBat: string; nextBowl: string; thisOver: string[]; recent: string[]
  status: string; result: string; winner?: 'A' | 'B' | null
  live: boolean; ended: boolean; hasPlayers: boolean; winA: number
  lastEvent: string; eventSeq: number; inningsBreak?: boolean
  next?: { innings: number; striker: number; non_striker: number; bowler: number; new_over: boolean } | null
  cards: Card[]; seq?: number
}

export type MatchSummary = Pick<MatchState, 'runs' | 'wkts' | 'balls' | 'totalBalls' | 'target' | 'battingIsA' |
  'innings' | 'winA' | 'status' | 'live' | 'ended' | 'crr' | 'rrr' | 'cards'>

export type MatchRow = {
  id: number; source: 'local' | 'sim' | 'api'; status: 'scheduled' | 'live' | 'completed'; tournamentId: number | null
  teamA: TeamRef; teamB: TeamRef; venue: string; scheduledAt: string | null; overs: number; result: string
  series: string; toss: string; summary: MatchSummary | null; updatedAt: string | null
}

export type Player = {
  id: number; team_id: number; name: string; role: 'BAT' | 'BOWL' | 'AR' | 'WK'; bat: number; bowl: number; style: string
  team?: string; stats?: PlayerStats | null
}
export type PlayerStats = {
  id: number; name: string; team: string; teamId: number; role: string; matches: number; runs: number; balls: number
  fours: number; sixes: number; outs: number; avg: number | null; sr: number | null; wkts: number; overs: string
  conceded: number; econ: number | null
}
export type Team = { id: number; name: string; short: string; city: string; manager: string; players?: number }
export type Tournament = {
  id: number; name: string; format: string; overs: number; venue: string; start_date: string; end_date: string
  status: 'upcoming' | 'active' | 'completed'; teams?: number; played?: number; fixtures?: number; leader?: string | null
}
export type Activity = { id: number; ts: string; kind: string; text: string }
export type Usage = { hitsToday: number; hitsLimit: number; day: string; lastCall: string | null; ok: boolean; detail?: string; configured: boolean }
export type Telemetry = { fps?: number; heap?: number; maxblk?: number; rssi?: number; uptime?: number; brightness?: number; showing?: string; rot?: number; ts?: number }
export type DeviceStatus = {
  online: boolean; info: { fw?: string; mac?: string; ip?: string; board?: string; ssid?: string; wifi?: { ssid?: string; ip?: string; rssi?: number; saved?: string[] } }; lastSeen: number | null
  telemetry: Telemetry; source: { kind: 'live' | 'sim' | 'match'; match_id?: number }
}
export type CommandRow = { id: number; ts: string; name: string; args: Record<string, unknown>; status: string; detail: string; acked_at: string | null }

export type Overview = {
  live: MatchRow[]; upcoming: MatchRow[]; recent: MatchRow[]; tournaments: Tournament[]
  counts: { teams: number; players: number; matches: number }
  top: { batters: PlayerStats[]; bowlers: PlayerStats[]; strikeRate: PlayerStats[] }
  activity: Activity[]
}
