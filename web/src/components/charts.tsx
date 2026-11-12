// Hand-built SVG instruments. Thin strokes, no glow, numbers in mono.
import { useRef } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'
import { reducedMotion } from '../lib/hooks'

// team colours come from the --color-team-a/b variables set by the match container (lib/teams.ts)
const TEAM = { A: 'var(--color-team-a)', B: 'var(--color-team-b)' }

/** Thin-arc gauge. The needle rotates (transform) to the value. */
export function Gauge({ value, max, label, display, warn }: { value: number; max: number; label: string; display: string; warn?: boolean }) {
  const frac = Math.max(0, Math.min(1, max ? value / max : 0))
  const r = 44, c = 2 * Math.PI * r, arc = c * 0.75
  const needle = useRef<SVGGElement>(null)
  const prev = useRef(0)
  useGSAP(() => {
    const deg = -135 + 270 * frac
    if (!needle.current) return
    if (reducedMotion()) { gsap.set(needle.current, { rotation: deg, svgOrigin: '60 60' }); return }
    gsap.fromTo(needle.current, { rotation: prev.current }, { rotation: deg, svgOrigin: '60 60', duration: 0.9, ease: 'power3.out' })
    prev.current = deg
  }, { dependencies: [frac] })
  const color = warn ? '#D9A441' : '#4DB6C4'
  return (
    <figure className="grid justify-items-center gap-1">
      <svg viewBox="0 0 120 112" className="w-full max-w-[150px]" role="img" aria-label={`${label} ${display}`}>
        <circle cx="60" cy="60" r={r} fill="none" stroke="#26303A" strokeWidth="2" strokeDasharray={`${arc} ${c}`} transform="rotate(135 60 60)" />
        <circle cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="2" strokeDasharray={`${arc * frac} ${c}`} transform="rotate(135 60 60)" />
        {Array.from({ length: 11 }, (_, i) => {
          const a = ((135 + 27 * i) * Math.PI) / 180
          return <line key={i} x1={60 + Math.cos(a) * 49} y1={60 + Math.sin(a) * 49} x2={60 + Math.cos(a) * 52} y2={60 + Math.sin(a) * 52} stroke="#4A5763" strokeWidth="1" />
        })}
        <g ref={needle}><line x1="60" y1="20" x2="60" y2="34" stroke="#E3E9EE" strokeWidth="1.5" /></g>
        <text x="60" y="66" textAnchor="middle" className="num" fill="#E3E9EE" fontSize="17" fontWeight="500">{display}</text>
      </svg>
      <figcaption className="label -mt-3">{label}</figcaption>
    </figure>
  )
}

/** Cumulative runs per over for each innings. */
export function Worm({ innings, overs }: { innings: { batting?: string; worm: number[]; fow?: { balls: number; runs: number }[] }[]; overs: number }) {
  const W = 560, H = 220, P = { l: 34, r: 10, t: 10, b: 24 }
  const maxR = Math.max(40, ...innings.flatMap(i => i.worm)) * 1.08
  const x = (o: number) => P.l + (o / Math.max(1, overs)) * (W - P.l - P.r)
  const y = (r: number) => H - P.b - (r / maxR) * (H - P.t - P.b)
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(f => Math.round(maxR * f / 10) * 10)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-h-[320px]" role="img" aria-label="Worm chart">
      {ticks.map(t => <g key={t}><line x1={P.l} x2={W - P.r} y1={y(t)} y2={y(t)} stroke="#26303A" /><text x={P.l - 6} y={y(t) + 4} textAnchor="end" fill="#7F8D99" fontSize="10" className="num">{t}</text></g>)}
      {Array.from({ length: overs + 1 }, (_, o) => o % (overs > 20 ? 10 : 5) === 0 && (
        <text key={o} x={x(o)} y={H - 6} textAnchor="middle" fill="#7F8D99" fontSize="10" className="num">{o}</text>))}
      {innings.map((inn, k) => {
        const col = TEAM[(inn.batting as 'A' | 'B') ?? (k ? 'B' : 'A')]
        const pts = [[0, 0], ...inn.worm.map((r, i) => [i + 1, r])]
        return (
          <g key={k}>
            <polyline fill="none" style={{ stroke: col }} strokeWidth="1.75" points={pts.map(([o, r]) => `${x(o)},${y(r)}`).join(' ')} />
            {(inn.fow || []).map((f, i) => <rect key={i} x={x(f.balls / 6) - 2.5} y={y(f.runs) - 2.5} width="5" height="5" fill="#0E1114" style={{ stroke: col }} />)}
          </g>
        )
      })}
    </svg>
  )
}

/** Runs per over, wickets as squares above the bar. */
export function Manhattan({ runs, wkts, batting }: { runs: number[]; wkts: number[]; batting?: string }) {
  const W = 560, H = 180, P = { l: 28, r: 6, t: 10, b: 22 }
  const max = Math.max(12, ...runs) * 1.1
  const bw = (W - P.l - P.r) / Math.max(1, runs.length)
  const col = TEAM[(batting as 'A' | 'B') ?? 'A']
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-h-[260px]" role="img" aria-label="Runs per over">
      {[0, 6, 12, 18, 24].filter(t => t < max).map(t => (
        <g key={t}><line x1={P.l} x2={W - P.r} y1={H - P.b - (t / max) * (H - P.t - P.b)} y2={H - P.b - (t / max) * (H - P.t - P.b)} stroke="#26303A" />
          <text x={P.l - 5} y={H - P.b - (t / max) * (H - P.t - P.b) + 4} textAnchor="end" fill="#7F8D99" fontSize="10" className="num">{t}</text></g>))}
      {runs.map((r, i) => {
        const h = (r / max) * (H - P.t - P.b)
        const x0 = P.l + i * bw + 1.5
        return (
          <g key={i}>
            <rect x={x0} y={H - P.b - h} width={Math.max(2, bw - 3)} height={h} style={{ fill: col }} fillOpacity="0.75" />
            {Array.from({ length: wkts[i] || 0 }, (_, k) => <rect key={k} x={x0 + bw / 2 - 4} y={H - P.b - h - 9 - k * 9} width="6" height="6" fill="#C0476E" />)}
            {(i + 1) % 5 === 0 && <text x={x0 + bw / 2} y={H - 6} textAnchor="middle" fill="#7F8D99" fontSize="10" className="num">{i + 1}</text>}
          </g>
        )
      })}
    </svg>
  )
}

export function Spark({ values, color = '#4DB6C4', height = 36, label }: { values: number[]; color?: string; height?: number; label: string }) {
  if (values.length < 2) return <div className="text-xs text-dim" style={{ height }}>Collecting samples</div>
  const W = 200, min = Math.min(...values), max = Math.max(...values), span = max - min || 1
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * W},${height - 3 - ((v - min) / span) * (height - 6)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none" className="w-full" style={{ height }} role="img" aria-label={label}>
      <polyline fill="none" stroke={color} strokeWidth="1.25" vectorEffect="non-scaling-stroke" points={pts} />
    </svg>
  )
}

export function Bars({ data, max, color = '#4DB6C4' }: { data: { label: string; value: number }[]; max: number; color?: string }) {
  return (
    <div className="grid gap-1.5">
      {data.map(d => (
        <div key={d.label} className="grid grid-cols-[84px_1fr_44px] items-center gap-3 text-xs">
          <span className="num text-dim">{d.label}</span>
          <div className="h-2 bg-raised"><div className="h-full origin-left" style={{ background: color, transform: `scaleX(${Math.min(1, d.value / (max || 1))})` }} /></div>
          <span className="num text-right">{d.value}</span>
        </div>
      ))}
    </div>
  )
}

/** Number that ticks up/down when it changes. */
export function Tick({ value, className = '' }: { value: number; className?: string }) {
  const el = useRef<HTMLSpanElement>(null)
  const prev = useRef(value)
  useGSAP(() => {
    if (!el.current) return
    const from = prev.current
    prev.current = value
    if (from === value || reducedMotion()) { el.current.textContent = String(value); return }
    const o = { v: from }
    gsap.to(o, { v: value, duration: 0.6, ease: 'power2.out', onUpdate: () => { if (el.current) el.current.textContent = String(Math.round(o.v)) } })
    gsap.fromTo(el.current, { y: -3, opacity: 0.6 }, { y: 0, opacity: 1, duration: 0.4 })
  }, { dependencies: [value] })
  return <span ref={el} className={`num ${className}`}>{value}</span>
}
