import { useEffect, useState } from 'react'
import { ArrowClockwiseIcon, CircleHalfIcon, CrosshairIcon, PowerIcon, SunIcon } from '@phosphor-icons/react'
import { Page, Panel, ErrorRow, Field, SkeletonRows, Stat } from '../components/ui'
import { Bars, Gauge, Spark } from '../components/charts'
import { useApi, useRefreshOn } from '../lib/hooks'
import { useLive } from '../lib/live'
import { useAdmin } from '../lib/admin'
import { api } from '../lib/api'
import { ago, uptime } from '../lib/format'
import type { CommandRow, DeviceStatus, MatchRow, Usage } from '../lib/types'

type DeviceDetail = DeviceStatus & {
  history: { ts: string; fps: number; heap: number; rssi: number }[]
  commands: CommandRow[]
  snapshots: { id: number; ts: string; origin: string; summary: string; matchId: number | null }[]
}

const STATUS_CLS: Record<string, string> = { acked: 'text-teal', sent: 'text-dim', timeout: 'text-warn', failed: 'text-wicket', offline: 'text-dim' }

export default function Device() {
  const d = useApi<DeviceDetail>('/api/device')
  const usage = useApi<{ current: Usage; byDay: { day: string; hits: number }[] }>('/api/usage')
  const sys = useApi<{ apiPolling: boolean; lan: string; port: number }>('/api/system')
  const matches = useApi<MatchRow[]>('/api/matches')
  const live = useLive(s => s.device)
  const liveTm = useLive(s => s.telemetry)
  const liveCmds = useLive(s => s.commands)
  const liveUsage = useLive(s => s.usage)
  const { guard } = useAdmin()
  const [bri, setBri] = useState(200)
  const [net, setNet] = useState({ ssid: '', pass: '' })
  const [busy, setBusy] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useRefreshOn(Object.keys(liveCmds).length, () => d.reload(true), 300)
  useRefreshOn(liveUsage?.hitsToday, () => usage.reload(true))

  const dev = live ?? d.data
  useEffect(() => { if (dev?.telemetry?.brightness) setBri(dev.telemetry.brightness) }, [dev?.telemetry?.brightness])

  const cmd = (name: string, args: Record<string, unknown> = {}) => guard(async () => {
    setBusy(name); setErr(null)
    try {
      const r = await api.post<{ status: string; detail?: string }>('/api/device/command', { name, args })
      if (r.status !== 'acked') setErr(`${name}: ${r.status}${r.detail ? ` (${r.detail})` : ''}`)
    } catch (e) { setErr((e as Error).message) } finally { setBusy(null); d.reload(true) }
  })
  const setSource = (v: string) => guard(async () => {
    await api.post('/api/device/source', v === 'live' || v === 'sim' ? { kind: v } : { kind: 'match', match_id: +v }); d.reload(true)
  })
  const polling = (on: boolean) => guard(async () => { await api.post('/api/cricapi/polling', { on }); sys.reload(true) })
  const refresh = () => guard(async () => { try { await api.post('/api/cricapi/refresh'); setErr(null) } catch (e) { setErr((e as Error).message) } })

  const hist = [...(d.data?.history ?? []), ...liveTm.map(t => ({ ts: String(t.ts), fps: t.fps ?? 0, heap: t.heap ?? 0, rssi: t.rssi ?? 0 }))].slice(-90)
  const commands = (d.data?.commands ?? []).map(c => liveCmds[c.id] ?? c)
  const tm = dev?.telemetry ?? {}
  const src = dev?.source
  const u = liveUsage ?? usage.data?.current
  const sourceOptions = (matches.data ?? []).filter(m => m.status !== 'scheduled').slice(0, 30)

  return (
    <Page title="Device control" sub="The CYD scoreboard and the CricketData link. Commands are acknowledged by the device once applied.">
      {err && <div className="mb-4"><ErrorRow message={err} /></div>}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Panel title="CYD scoreboard" className="lg:col-span-7" meta={dev?.info?.board || 'ESP32-2432S028R'}
               actions={<span className={`label ${dev?.online ? 'text-teal' : 'text-warn'}`}>{dev?.online ? 'Online' : 'Offline'}</span>}>
          {!dev ? <SkeletonRows rows={2} h={50} /> : (
            <div className="grid gap-5">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <Stat label="Frame rate" value={tm.fps ? `${tm.fps}` : '-'} sub="fps, liquid band" />
                <Stat label="Free heap" value={tm.heap ? `${(tm.heap / 1024).toFixed(1)}` : '-'} sub={tm.maxblk ? `KB, block ${(tm.maxblk / 1024).toFixed(0)} KB` : 'KB'} />
                <Stat label="WiFi" value={tm.rssi ?? '-'} sub="dBm" />
                <Stat label="Uptime" value={<span className="text-[17px]">{uptime(tm.uptime)}</span>} sub={dev.lastSeen ? `seen ${ago(dev.lastSeen)}` : 'never seen'} />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div><span className="label">fps</span><Spark values={hist.map(h => h.fps)} label="Frame rate history" /></div>
                <div><span className="label">heap</span><Spark values={hist.map(h => h.heap)} color="#7F8D99" label="Heap history" /></div>
                <div><span className="label">rssi</span><Spark values={hist.map(h => h.rssi)} color="#D9A441" label="Signal history" /></div>
              </div>
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-dim">
                <span>IP <span className="num text-ink">{dev.info?.ip || '-'}</span></span>
                <span>MAC <span className="num text-ink">{dev.info?.mac || '-'}</span></span>
                <span>Firmware <span className="num text-ink">{dev.info?.fw || '-'}</span></span>
                <span>Hub <span className="num text-ink">{sys.data ? `${sys.data.lan}:${sys.data.port}` : '-'}</span></span>
              </div>
            </div>
          )}
        </Panel>

        <Panel title="Display source" className="lg:col-span-5" meta={tm.showing ? `Now: ${tm.showing}` : undefined}>
          <div className="grid gap-3">
            <select className="select" value={src?.kind === 'match' ? String(src.match_id) : (src?.kind ?? 'live')} onChange={e => setSource(e.target.value)} aria-label="Display source">
              <option value="live">Screen 1 · live IPL match</option>
              <option value="sim">Screen 2 · simulation</option>
              {sourceOptions.map(m => <option key={m.id} value={m.id}>{m.status === 'live' ? 'LIVE ' : ''}{m.teamA.short} v {m.teamB.short} · {m.source}</option>)}
            </select>
            <p className="text-xs text-dim">The CYD redraws within a second of each change. Live API matches update every 90 s, which is set by the free credit budget.</p>
          </div>
        </Panel>

        <Panel title="WiFi networks" className="lg:col-span-12" meta={dev?.info?.wifi?.ssid ? `On ${dev.info.wifi.ssid}` : undefined}
               bodyClass="panel-body grid grid-cols-1 gap-6 md:grid-cols-[1fr_1fr]">
          <div className="grid content-start gap-3">
            <p className="text-[13px] text-dim">The CYD remembers up to 5 networks and joins whichever is in range. If none is, it opens its own
              hotspot <span className="num text-ink">SEEv2-CYD</span> (password <span className="num text-ink">scoreboard</span>) and shows a QR code; the setup page is at
              <span className="num text-ink"> 192.168.4.1</span>. The laptop must be on the same network. The CYD finds it by its broadcast beacon.</p>
            <table className="table"><tbody>
              {(dev?.info?.wifi?.saved ?? []).map(n => (
                <tr key={n}><td>{n}</td><td className="label">{n === dev?.info?.wifi?.ssid ? <span className="text-teal">Connected</span> : 'Saved'}</td>
                  <td className="r"><button className="btn btn-sm" disabled={!!busy || n === dev?.info?.wifi?.ssid} onClick={() => cmd('wifi_forget', { ssid: n })}>Forget</button></td></tr>
              ))}
              {!dev?.info?.wifi?.saved?.length && <tr><td className="text-dim">{dev?.online ? 'No list reported yet' : 'Connect the CYD to see its saved networks'}</td></tr>}
            </tbody></table>
          </div>
          <form className="grid content-start gap-3" onSubmit={e => { e.preventDefault(); cmd('wifi_add', net); setNet({ ssid: '', pass: '' }) }}>
            <Field label="Network name" htmlFor="wssid" helper="Add your phone hotspot here while the CYD is online, before you switch.">
              <input id="wssid" className="input" required maxLength={32} value={net.ssid} onChange={e => setNet({ ...net, ssid: e.target.value })} autoCapitalize="off" />
            </Field>
            <Field label="Password" htmlFor="wpass" helper="Sent to the CYD over your local network and kept only on the device.">
              <input id="wpass" type="password" className="input" maxLength={64} value={net.pass} onChange={e => setNet({ ...net, pass: e.target.value })} />
            </Field>
            <div><button className="btn btn-primary" disabled={!dev?.online || !!busy}>Save to CYD</button></div>
          </form>
        </Panel>

        <Panel title="Commands" className="lg:col-span-7">
          <div className="grid gap-5">
            <div className="grid gap-2">
              <label className="label" htmlFor="bri">Backlight <span className="num text-ink">{bri}</span></label>
              <div className="flex items-center gap-3">
                <SunIcon size={18} weight="light" className="text-dim" />
                <input id="bri" type="range" min={10} max={255} value={bri} onChange={e => setBri(+e.target.value)} className="flex-1 accent-[#4DB6C4]" />
                <button className="btn btn-sm btn-primary" disabled={busy === 'brightness'} onClick={() => cmd('brightness', { value: bri })}>Apply</button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <button className="btn" disabled={!!busy} onClick={() => cmd('identify')}><CrosshairIcon size={16} weight="light" />Identify</button>
              <button className="btn" disabled={!!busy} onClick={() => cmd('rotate')}><ArrowClockwiseIcon size={16} weight="light" />Rotate 180</button>
              <button className="btn" disabled={!!busy} onClick={() => cmd('invert')}><CircleHalfIcon size={16} weight="light" />Invert</button>
              <button className="btn btn-danger" disabled={!!busy} onClick={() => { if (confirm('Reboot the CYD?')) cmd('reboot') }}><PowerIcon size={16} weight="light" />Reboot</button>
            </div>
          </div>
        </Panel>

        <Panel title="Command log" className="lg:col-span-5" bodyClass="max-h-72 overflow-y-auto">
          {commands.length ? (
            <table className="table">
              <tbody>{commands.map(c => (
                <tr key={c.id}><td className="num text-xs text-dim">{ago(c.ts)}</td><td className="font-medium">{c.name}</td>
                  <td className="text-xs text-dim">{c.detail || (Object.keys(c.args || {}).length ? JSON.stringify(c.args) : '')}</td>
                  <td className={`label r ${STATUS_CLS[c.status] ?? ''}`}>{c.status}</td></tr>
              ))}</tbody>
            </table>
          ) : <p className="p-4 text-dim">No commands sent yet. Try Identify: the seam flashes three times.</p>}
        </Panel>

        <Panel title="CricketData API" className="lg:col-span-7" meta="Free plan" bodyClass="panel-body grid grid-cols-1 gap-5 sm:grid-cols-[170px_1fr]">
          <div id="api"><Gauge value={u?.hitsToday ?? 0} max={u?.hitsLimit ?? 100} label="Credits used today" display={`${u?.hitsToday ?? 0}/${u?.hitsLimit ?? 100}`} warn={(u?.hitsToday ?? 0) > (u?.hitsLimit ?? 100) * 0.8} /></div>
          <div className="grid content-start gap-4">
            {!u?.configured && <p className="text-[13px] text-warn">No key configured. Get a free key at cricketdata.org, add <span className="num">CRICAPI_KEY=...</span> to <span className="num">hub/.env</span>, then restart the hub.</p>}
            <div className="grid grid-cols-2 gap-4">
              <Stat label="Last call" value={<span className="font-sans text-[15px]">{ago(u?.lastCall ?? null)}</span>} sub={u && !u.ok ? u.detail : undefined} />
              <Stat label="Polling" value={<span className={`font-sans text-[15px] ${sys.data?.apiPolling ? 'text-teal' : 'text-dim'}`}>{sys.data?.apiPolling ? 'Every 90 s live, 10 min idle' : 'Paused'}</span>} />
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="btn btn-sm" onClick={() => polling(!sys.data?.apiPolling)}>{sys.data?.apiPolling ? 'Pause polling' : 'Resume polling'}</button>
              <button className="btn btn-sm" disabled={!u?.configured} onClick={refresh}>Fetch now (1 credit)</button>
            </div>
            {usage.data?.byDay.length ? <Bars data={usage.data.byDay.slice(-7).map(x => ({ label: x.day.slice(5), value: x.hits }))} max={u?.hitsLimit ?? 100} /> : null}
          </div>
        </Panel>

        <Panel title="Snapshots" className="lg:col-span-5" meta="What the CYD was sent" bodyClass="max-h-72 overflow-y-auto">
          {d.data?.snapshots.length ? (
            <table className="table"><tbody>{d.data.snapshots.map(x => (
              <tr key={x.id}><td className="num text-xs text-dim">{ago(x.ts)}</td><td className="num">{x.summary}</td><td className="label r">{x.origin}</td></tr>
            ))}</tbody></table>
          ) : <p className="p-4 text-dim">Nothing pushed yet. Pick a match as the display source.</p>}
        </Panel>
      </div>
    </Page>
  )
}
