import { useRef, type ReactNode } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'
import { reducedMotion } from '../lib/hooks'
import { chipClass } from '../lib/format'

gsap.registerPlugin(useGSAP)

export function Panel({ title, meta, actions, children, className = '', bodyClass = 'panel-body' }: {
  title?: ReactNode; meta?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; bodyClass?: string
}) {
  return (
    <section className={`panel ${className}`} data-reveal>
      {(title || actions || meta) && (
        <header className="panel-head">
          <div className="flex min-w-0 items-baseline gap-3">
            {title && <h2 className="h2 truncate">{title}</h2>}
            {meta && <span className="label truncate">{meta}</span>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  )
}

/** Stagger-reveal every [data-reveal] child on mount and whenever `key` changes. */
export function Page({ children, title, sub, actions, revealKey }: {
  children: ReactNode; title: string; sub?: ReactNode; actions?: ReactNode; revealKey?: unknown
}) {
  const root = useRef<HTMLDivElement>(null)
  useGSAP(() => {
    if (reducedMotion()) return
    gsap.from('[data-reveal]', { y: 8, opacity: 0, duration: 0.45, stagger: 0.04, ease: 'power2.out', clearProps: 'transform,opacity' })
  }, { scope: root, dependencies: [revealKey] })
  return (
    <div ref={root} className="mx-auto w-full max-w-[1440px] px-4 pb-28 pt-5 md:px-6 md:pb-10">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3" data-reveal>
        <div>
          <h1 className="h1">{title}</h1>
          {sub && <p className="mt-1 max-w-[65ch] text-dim">{sub}</p>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  )
}

export function Skeleton({ h = 16, w = '100%', className = '' }: { h?: number; w?: number | string; className?: string }) {
  return <div className={`skel ${className}`} style={{ height: h, width: w }} />
}

export function SkeletonRows({ rows = 4, h = 38 }: { rows?: number; h?: number }) {
  return <div className="grid gap-2">{Array.from({ length: rows }, (_, i) => <Skeleton key={i} h={h} />)}</div>
}

export function Empty({ title, hint, action }: { title: string; hint: string; action?: ReactNode }) {
  return (
    <div className="grid gap-3 border border-dashed border-rule p-5">
      <div className="h2">{title}</div>
      <p className="max-w-[60ch] text-dim">{hint}</p>
      {action && <div>{action}</div>}
    </div>
  )
}

export function ErrorRow({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3 border border-wicket/60 bg-wicket/5 px-3 py-2" role="alert">
      <span className="text-[13px]">{message}</span>
      {onRetry && <button className="btn btn-sm" onClick={onRetry}>Retry</button>}
    </div>
  )
}

export function Chips({ balls, max = 12, size = 'md' }: { balls: string[]; max?: number; size?: 'md' | 'lg' }) {
  const list = balls.slice(-max)
  const ref = useRef<HTMLDivElement>(null)
  const last = useRef(balls.length)
  useGSAP(() => {
    const added = balls.length > last.current
    last.current = balls.length
    if (!added || reducedMotion() || !ref.current) return
    const el = ref.current.lastElementChild
    if (el) gsap.from(el, { x: 14, opacity: 0, duration: 0.35, ease: 'power3.out' })
  }, { dependencies: [balls.length, balls.join(',')], scope: ref })
  if (!list.length) return <span className="text-dim">No deliveries yet</span>
  return (
    <div ref={ref} className="flex flex-wrap gap-1.5">
      {list.map((b, i) => (
        <span key={`${balls.length - list.length + i}`} className={`${chipClass(b)} ${size === 'lg' ? '!h-8 !min-w-9 text-sm' : ''}`}>
          {b === '.' ? '' : b}
        </span>
      ))}
    </div>
  )
}

export function Stat({ label, value, sub, className = '' }: { label: string; value: ReactNode; sub?: ReactNode; className?: string }) {
  return (
    <div className={`grid gap-1 ${className}`}>
      <span className="label">{label}</span>
      <span className={`${typeof value === 'string' && /[a-z]{2}/i.test(value) ? 'text-[15px]' : 'num text-xl'} font-medium leading-none`}>{value}</span>
      {sub && <span className="text-xs text-dim">{sub}</span>}
    </div>
  )
}

export function Modal({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  return (
    <div className="fixed inset-0 z-30 grid place-items-center overflow-y-auto bg-charcoal/80 p-4" onMouseDown={onClose}>
      <div className={`panel w-full ${wide ? 'max-w-2xl' : 'max-w-md'}`} onMouseDown={e => e.stopPropagation()} role="dialog" aria-label={title}>
        <div className="panel-head">
          <span className="h2">{title}</span>
          <button className="btn btn-sm" onClick={onClose} aria-label="Close">Close</button>
        </div>
        <div className="panel-body">{children}</div>
      </div>
    </div>
  )
}

export function Field({ label, helper, error, children, htmlFor }: { label: string; helper?: string; error?: string | null; children: ReactNode; htmlFor?: string }) {
  return (
    <div className="field">
      <label className="label" htmlFor={htmlFor}>{label}</label>
      {children}
      {error ? <span className="error-text">{error}</span> : helper ? <span className="helper">{helper}</span> : null}
    </div>
  )
}

export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; label?: string
}) {
  return (
    <div className="inline-flex border border-rule" role="radiogroup" aria-label={label}>
      {options.map(o => (
        <button key={o.value} role="radio" aria-checked={o.value === value} onClick={() => onChange(o.value)}
                className={`min-h-9 border-r border-rule px-3 text-[13px] last:border-r-0 ${o.value === value ? 'bg-raised text-teal' : 'text-dim hover:text-ink'}`}>
          {o.label}
        </button>
      ))}
    </div>
  )
}
