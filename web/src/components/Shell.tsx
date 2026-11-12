import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  BroadcastIcon, ChartLineIcon, ClipboardTextIcon, CpuIcon, DotsThreeIcon, LockIcon, LockOpenIcon, MonitorIcon,
  SquaresFourIcon, TrophyIcon, UsersThreeIcon, type Icon,
} from '@phosphor-icons/react'
import { useLive } from '../lib/live'
import { useAdmin } from '../lib/admin'

type Tab = { to: string; label: string; icon: Icon; primary?: boolean }
const TABS: Tab[] = [
  { to: '/', label: 'Overview', icon: SquaresFourIcon, primary: true },
  { to: '/live', label: 'Live Centre', icon: BroadcastIcon, primary: true },
  { to: '/score', label: 'Scoring', icon: ClipboardTextIcon, primary: true },
  { to: '/tournaments', label: 'Tournaments', icon: TrophyIcon },
  { to: '/teams', label: 'Teams', icon: UsersThreeIcon },
  { to: '/sim', label: 'Simulation', icon: CpuIcon, primary: true },
  { to: '/device', label: 'Device', icon: MonitorIcon },
  { to: '/analytics', label: 'Analytics', icon: ChartLineIcon },
]

function Clock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 15000); return () => clearInterval(t) }, [])
  return <span className="num text-[13px]">{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
}

function Credits() {
  const usage = useLive(s => s.usage)
  if (!usage) return <span className="skel inline-block h-3 w-24" />
  const frac = usage.hitsLimit ? usage.hitsToday / usage.hitsLimit : 0
  const warn = frac > 0.8
  return (
    <NavLink to="/device#api" className="flex items-center gap-2" title={usage.configured ? 'CricketData credits used today' : 'No CricketData key configured'}>
      <span className="label hidden sm:inline">API</span>
      <span className={`num text-[13px] ${warn ? 'text-warn' : ''}`}>{usage.hitsToday}<span className="text-dim">/{usage.hitsLimit}</span></span>
      <span className="relative hidden h-1.5 w-14 bg-raised sm:inline-block" aria-hidden>
        <span className={`absolute inset-0 origin-left ${warn ? 'bg-warn' : 'bg-teal'}`} style={{ transform: `scaleX(${Math.min(1, frac)})` }} />
      </span>
      {!usage.configured && <span className="label hidden text-warn sm:inline">no key</span>}
    </NavLink>
  )
}

function StatusStrip() {
  const connected = useLive(s => s.connected)
  const device = useLive(s => s.device)
  const { admin, ask, lock } = useAdmin()
  return (
    <div className="sticky top-0 z-20 flex h-11 items-center justify-between gap-3 border-b border-rule bg-charcoal/95 px-4 backdrop-blur-none md:px-6">
      <div className="flex min-w-0 items-center gap-3 sm:gap-4">
        <span className="flex items-center gap-2 text-[13px] font-semibold tracking-tight md:hidden">SEEv2</span>
        <span className="flex items-center gap-2" title="Dashboard link to hub">
          <span className={`dot ${connected ? 'bg-teal' : 'bg-wicket'}`} />
          <span className="label hidden sm:inline">{connected ? 'Hub' : 'Hub offline'}</span><span className="label sm:hidden">Hub</span>
        </span>
        <NavLink to="/device" className="flex items-center gap-2" title="CYD scoreboard link">
          <span className={`dot ${device?.online ? 'bg-teal' : 'bg-faint'}`} />
          <span className="label hidden sm:inline">{device?.online ? 'CYD' : 'CYD offline'}</span><span className="label sm:hidden">CYD</span>
        </NavLink>
      </div>
      <div className="flex items-center gap-4">
        <Credits />
        <span className="hidden sm:inline"><Clock /></span>
        <button className="btn btn-sm" onClick={admin ? lock : ask} aria-label={admin ? 'Lock admin' : 'Unlock admin'}>
          {admin ? <LockOpenIcon size={15} weight="light" className="text-teal" /> : <LockIcon size={15} weight="light" />}
          <span className="hidden sm:inline">{admin ? 'Admin' : 'Viewer'}</span>
        </button>
      </div>
    </div>
  )
}

function RailLink({ t }: { t: Tab }) {
  return (
    <NavLink to={t.to} end={t.to === '/'}
      className={({ isActive }) => `relative flex h-14 flex-col items-center justify-center gap-1 text-[10px] font-semibold uppercase tracking-[0.06em] lg:h-auto lg:flex-row lg:justify-start lg:gap-3 lg:px-4 lg:py-2.5 lg:text-[13px] lg:normal-case lg:tracking-normal ${
        isActive ? 'bg-raised text-ink [&>svg]:text-teal' : 'text-dim hover:bg-graphite hover:text-ink'}`}>
      <t.icon size={20} weight="light" />
      <span className="hidden md:inline lg:inline">{t.label}</span>
    </NavLink>
  )
}

export function Shell({ children }: { children: ReactNode }) {
  const [more, setMore] = useState(false)
  const loc = useLocation()
  useEffect(() => setMore(false), [loc.pathname])
  return (
    <div className="min-h-[100dvh] md:grid md:grid-cols-[84px_1fr] lg:grid-cols-[208px_1fr]">
      <aside className="sticky top-0 hidden h-[100dvh] flex-col border-r border-rule bg-charcoal md:flex">
        <div className="flex h-11 items-center gap-2 border-b border-rule px-4">
          <svg width="18" height="18" viewBox="0 0 32 32" aria-hidden><path d="M3 18c5-6 9 4 13-2" stroke="#A974E8" strokeWidth="2.5" fill="none" /><path d="M16 16c3 4 8-4 13 0" stroke="#38C9B4" strokeWidth="2.5" fill="none" /><path d="M16 5v22" stroke="#4DB6C4" strokeWidth="1.5" /></svg>
          <span className="hidden text-[13px] font-semibold tracking-tight lg:inline">SEEv2 Control Room</span>
        </div>
        <nav className="flex flex-1 flex-col py-2" aria-label="Main">{TABS.map(t => <RailLink key={t.to} t={t} />)}</nav>
        <div className="hidden border-t border-rule p-4 text-xs text-dim lg:block">Stage 1: laptop hub. Stage 2: Arduino UNO Q.</div>
      </aside>

      <div className="min-w-0">
        <StatusStrip />
        <main>{children}</main>
      </div>

      {/* mobile bottom tabs */}
      <nav className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-5 border-t border-rule bg-charcoal pb-[env(safe-area-inset-bottom)] md:hidden" aria-label="Main">
        {TABS.filter(t => t.primary).map(t => (
          <NavLink key={t.to} to={t.to} end={t.to === '/'}
            className={({ isActive }) => `flex h-14 flex-col items-center justify-center gap-1 text-[10px] font-semibold uppercase tracking-[0.05em] ${isActive ? 'bg-raised text-ink [&>svg]:text-teal' : 'text-dim'}`}>
            <t.icon size={20} weight="light" /><span>{t.label.split(' ')[0]}</span>
          </NavLink>
        ))}
        <button onClick={() => setMore(m => !m)} className={`flex h-14 flex-col items-center justify-center gap-1 text-[10px] font-semibold uppercase tracking-[0.05em] ${more ? 'bg-raised text-ink' : 'text-dim'}`} aria-expanded={more}>
          <DotsThreeIcon size={20} weight="light" /><span>More</span>
        </button>
      </nav>
      {more && (
        <div className="fixed inset-x-0 bottom-14 z-20 border-t border-rule bg-graphite pb-[env(safe-area-inset-bottom)] md:hidden">
          {TABS.filter(t => !t.primary).map(t => (
            <NavLink key={t.to} to={t.to} className="flex h-12 items-center gap-3 border-b border-rule px-4 text-[14px]">
              <t.icon size={18} weight="light" className="text-dim" />{t.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}
