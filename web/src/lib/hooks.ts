import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'

export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!!path)
  const seq = useRef(0)
  const load = useCallback(async (quiet = false) => {
    if (!path) return
    const n = ++seq.current
    if (!quiet) setLoading(true)
    try {
      const d = await api.get<T>(path)
      if (n === seq.current) { setData(d); setError(null) }
    } catch (e) {
      if (n === seq.current) setError((e as Error).message)
    } finally {
      if (n === seq.current) setLoading(false)
    }
  }, [path])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load() }, [load, ...deps])
  return { data, error, loading, reload: load, setData }
}

/** Re-run fn (debounced) whenever `signal` changes. */
export function useRefreshOn(signal: unknown, fn: () => void, wait = 600) {
  const first = useRef(true)
  useEffect(() => {
    if (first.current) { first.current = false; return }
    const t = setTimeout(fn, wait)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signal])
}

export const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
