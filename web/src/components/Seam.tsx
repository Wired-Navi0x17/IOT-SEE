// The momentum seam: the same two-liquid band as the CYD, driven by the same win model.
import { useEffect, useRef } from 'react'
import { reducedMotion } from '../lib/hooks'
import { hexToInt, pairColors, teamVars } from '../lib/teams'

const W = 420
type Rib = [amp: number, f1: number, s1: number, ph1: number, amp2: number, f2: number, s2: number, ph2: number, k: number, gain: number]
// one stream per team: a soft body and a bright core on the same path
const RIB_A: Rib[] = [[11, 0.020, 1.1, 0.0, 4, 0.047, 0.7, 1.0, 1.3, 0.5], [11, 0.020, 1.1, 0.0, 4, 0.047, 0.7, 1.0, 4.5, 0.6]]
const RIB_B: Rib[] = [[11, 0.019, 1.0, 3.3, 4, 0.044, 0.8, 0.4, 1.3, 0.5], [11, 0.019, 1.0, 3.3, 4, 0.044, 0.8, 0.4, 4.5, 0.6]]
const NR = RIB_A.length

function lut(deep: number, bright: number, hot: number) {
  const c = (v: number, s: number) => (v >> s) & 255
  const out = new Uint8Array(256 * 3)
  for (let i = 0; i < 256; i++) {
    const v = i / 255
    for (let ch = 0; ch < 3; ch++) {
      const s = 16 - ch * 8, d = c(deep, s), b = c(bright, s), h = c(hot, s)
      const o = v < 0.45 ? d * (v / 0.45) : v < 0.82 ? d + (b - d) * ((v - 0.45) / 0.37) : b + (h - b) * ((v - 0.82) / 0.18)
      out[i * 3 + ch] = Math.min(255, o)
    }
  }
  return out
}
/** deep / bright / hot ramp from one team colour */
function teamLut(hex: string) {
  const c = hexToInt(hex), mix = (f: (v: number) => number) => [16, 8, 0].reduce((o, s) => o | (Math.min(255, Math.round(f((c >> s) & 255))) << s), 0)
  return lut(mix(v => v * 0.45), c, mix(v => v + (255 - v) * 0.85))
}
const GLOW = new Uint8Array(64).map((_, k) =>
  255 * Math.max(0, 0.72 * Math.exp(-((k / 6) ** 2) * 0.7) + 0.28 * Math.exp(-k / 14) - 0.28 * Math.exp(-63 / 14)))

type Props = {
  winA: number; height?: number; event?: string; eventSeq?: number; battingIsA?: boolean
  labelA?: string; labelB?: string; showPill?: boolean; className?: string
}

export function Seam({ winA, height = 84, event, eventSeq, battingIsA = true, labelA = 'A', labelB = 'B', showPill = true, className = '' }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const pill = useRef<HTMLDivElement>(null)
  const pctA = useRef<HTMLSpanElement>(null)
  const pctB = useRef<HTMLSpanElement>(null)
  const target = useRef(winA)
  const energy = useRef({ a: 0, b: 0, flash: 0 })
  target.current = winA
  const cols = pairColors(labelA, labelB)
  const luts = useRef({ A: '', B: '', a: new Uint8Array(0), b: new Uint8Array(0) })
  if (luts.current.A !== cols.A || luts.current.B !== cols.B)
    luts.current = { A: cols.A, B: cols.B, a: teamLut(cols.A), b: teamLut(cols.B) }

  useEffect(() => {
    if (!eventSeq) return
    const e = energy.current
    if (event === 'four' || event === 'six') {
      const amt = event === 'six' ? 1 : 0.7
      if (battingIsA) e.a = amt; else e.b = amt
    } else if (event === 'wicket') {
      if (battingIsA) e.b = 1; else e.a = 1
      e.flash = 1
    }
  }, [eventSeq, event, battingIsA])

  useEffect(() => {
    const cv = canvas.current!
    const H = Math.round(height * (W / 640) * 1.6)
    cv.width = W; cv.height = H
    const ctx = cv.getContext('2d')!
    const img = ctx.createImageData(W, H)
    const px = img.data
    const Y0 = H * 0.55, ampScale = H / 60
    const haze = new Float32Array(H), vfade = new Float32Array(H), seamV = new Float32Array(H), seamX = new Float32Array(H)
    const smooth = (a: number, b: number, x: number) => { const u = Math.min(1, Math.max(0, (x - a) / (b - a))); return u * u * (3 - 2 * u) }
    for (let y = 0; y < H; y++) {
      const d = (y - Y0) / (13 * ampScale)
      haze[y] = 38 * Math.exp(-d * d)
      vfade[y] = smooth(0, H * 0.25, y) * smooth(H, H * 0.88, y)
      const e = (y - Y0) / (10 * ampScale)
      seamV[y] = Math.exp(-e * e)
    }
    const BG = [0x14, 0x1a, 0x1f]
    let t = 0, phA = 0, phB = 0, p = target.current, last = performance.now(), raf = 0
    const still = reducedMotion()
    const ycA = new Float32Array(NR), ycB = new Float32Array(NR)

    const frame = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000); last = now
      const e = energy.current
      if (!still) { t += dt; phA += dt * (1 + 1.6 * e.a); phB += dt * (1 + 1.6 * e.b) }
      p += (target.current - p) * (still ? 1 : 1 - Math.exp(-dt * 1.2))
      const dk = Math.exp(-dt * 1.4); e.a *= dk; e.b *= dk; e.flash *= Math.exp(-dt * 3)
      const bx = p * W
      const LUT_A = luts.current.a, LUT_B = luts.current.b
      for (let y = 0; y < H; y++) seamX[y] = bx + 3 * Math.sin(y * 0.17 + t * 2.1) + 2 * Math.sin(y * 0.06 - t * 1.3)
      const ampA = (1 + 0.9 * e.a) * ampScale, ampB = (1 + 0.9 * e.b) * ampScale
      for (let x = 0; x < W; x++) {
        const pinch = Math.min(1, Math.abs(x - bx) / 80) * 0.85 + 0.15
        const edge = Math.min(1, Math.min(x, W - 1 - x) / 18 + 0.25)
        for (let i = 0; i < NR; i++) {
          const a = RIB_A[i], b = RIB_B[i]
          ycA[i] = Y0 + pinch * ampA * (a[0] * Math.sin(a[1] * x - a[2] * phA + a[3]) + a[4] * Math.sin(a[5] * x + a[6] * phA * 0.6 + a[7]))
          ycB[i] = Y0 + pinch * ampB * (b[0] * Math.sin(b[1] * x + b[2] * phB + b[3]) + b[4] * Math.sin(b[5] * x - b[6] * phB * 0.6 + b[7]))
        }
        for (let y = 0; y < H; y++) {
          const wa = Math.min(1, Math.max(0, (seamX[y] - x) / 16 + 0.5))
          const vf = vfade[y] * edge
          let iA = 0, iB = 0
          if (wa > 0.01) {
            let acc = haze[y]
            for (let i = 0; i < NR; i++) { const k = (Math.abs(y - ycA[i]) * RIB_A[i][8] / ampScale) | 0; if (k < 64) acc += GLOW[k] * RIB_A[i][9] }
            iA = Math.min(255, (acc * wa * vf) | 0)
          }
          if (wa < 0.99) {
            let acc = haze[y]
            for (let i = 0; i < NR; i++) { const k = (Math.abs(y - ycB[i]) * RIB_B[i][8] / ampScale) | 0; if (k < 64) acc += GLOW[k] * RIB_B[i][9] }
            iB = Math.min(255, (acc * (1 - wa) * vf) | 0)
          }
          const ds = Math.abs(x - seamX[y])
          const wh = ds < 1.6 ? (1.6 - ds) * 0.5 * seamV[y] * (110 + 120 * e.flash) : 0
          const o = (y * W + x) * 4
          px[o] = Math.min(255, BG[0] + LUT_A[iA * 3] + LUT_B[iB * 3] + wh)
          px[o + 1] = Math.min(255, BG[1] + LUT_A[iA * 3 + 1] + LUT_B[iB * 3 + 1] + wh)
          px[o + 2] = Math.min(255, BG[2] + LUT_A[iA * 3 + 2] + LUT_B[iB * 3 + 2] + wh)
          px[o + 3] = 255
        }
      }
      ctx.putImageData(img, 0, 0)
      if (pill.current) {
        const w = cv.clientWidth, pw = pill.current.offsetWidth
        const x = Math.min(w - pw - 6, Math.max(6, p * w - pw / 2))
        pill.current.style.transform = `translate3d(${x}px,0,0)`
        if (pctA.current) pctA.current.textContent = (p * 100).toFixed(1) + '%'
        if (pctB.current) pctB.current.textContent = (100 - p * 100).toFixed(1) + '%'
      }
      raf = requestAnimationFrame(frame)
    }
    raf = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(raf)
  }, [height])

  return (
    <div className={`relative overflow-hidden ${className}`} style={{ height, ...teamVars(labelA, labelB) }}>
      <canvas ref={canvas} className="absolute inset-0 h-full w-full" aria-hidden />
      {showPill && (
        <div ref={pill} className="absolute left-0 top-2 flex items-center gap-2 border border-rule bg-charcoal/90 px-2.5 py-1 text-xs will-change-transform"
             role="status" aria-label={`Win probability ${labelA} ${(winA * 100).toFixed(1)} percent`}>
          <span className="team-a font-semibold">{labelA}</span><span ref={pctA} className="num">-</span>
          <span className="h-3 w-px bg-rule" />
          <span className="team-b font-semibold">{labelB}</span><span ref={pctB} className="num">-</span>
        </div>
      )}
    </div>
  )
}

/** 6px static seam for match rows. */
export function MiniSeam({ winA, className = '' }: { winA: number; className?: string }) {
  const a = Math.max(0.02, Math.min(0.98, winA))
  return (
    <div className={`relative h-1.5 w-full overflow-hidden bg-raised ${className}`} aria-label={`Team A win ${(a * 100).toFixed(1)}%`}>
      <div className="absolute inset-y-0 left-0 w-full origin-left bg-team-a/80 transition-transform duration-700" style={{ transform: `scaleX(${a})` }} />
      <div className="absolute inset-y-0 right-0 w-full origin-right bg-team-b/80 transition-transform duration-700" style={{ transform: `scaleX(${1 - a})` }} />
      <div className="absolute inset-0 transition-transform duration-700" style={{ transform: `translateX(${a * 100}%)` }}>
        <div className="h-full w-px bg-ink" />
      </div>
    </div>
  )
}
