// One WebSocket to the hub, shared by every screen.
import { useSyncExternalStore } from 'react'
import type { Activity, CommandRow, DeviceStatus, MatchState, Telemetry, Usage } from './types'

type LiveState = {
  connected: boolean
  device: DeviceStatus | null
  usage: Usage | null
  matches: Record<number, MatchState>
  activity: Activity[]
  commands: Record<number, CommandRow>
  telemetry: Telemetry[]
  tick: number
}

let state: LiveState = { connected: false, device: null, usage: null, matches: {}, activity: [], commands: {}, telemetry: [], tick: 0 }
const listeners = new Set<() => void>()
const set = (patch: Partial<LiveState>) => { state = { ...state, ...patch, tick: state.tick + 1 }; listeners.forEach(l => l()) }

let ws: WebSocket | null = null
let retry = 800

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws/ui`)
  ws.onopen = () => { retry = 800; set({ connected: true }) }
  ws.onclose = () => {
    set({ connected: false })
    setTimeout(connect, retry)
    retry = Math.min(retry * 1.7, 8000)
  }
  ws.onmessage = ev => {
    const { type, data } = JSON.parse(ev.data)
    switch (type) {
      case 'hello': set({ device: data.device, usage: data.usage }); break
      case 'match.update': set({ matches: { ...state.matches, [data.id]: data.state } }); break
      case 'device.status': set({ device: data }); break
      case 'device.telemetry':
        set({ device: state.device ? { ...state.device, telemetry: data } : state.device,
              telemetry: [...state.telemetry, data].slice(-120) })
        break
      case 'api.usage': set({ usage: data }); break
      case 'activity': set({ activity: [data, ...state.activity].slice(0, 40) }); break
      case 'command.update': set({ commands: { ...state.commands, [data.id]: data } }); break
    }
  }
}
connect()

export function useLive<T>(select: (s: LiveState) => T): T {
  return useSyncExternalStore(cb => { listeners.add(cb); return () => listeners.delete(cb) }, () => select(state))
}
export const liveSnapshot = () => state
