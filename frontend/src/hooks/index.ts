import { useState, useEffect, useRef, useCallback } from 'react'

export function useScrollReveal(threshold = 0.1) {
  const ref = useRef<HTMLDivElement>(null)

  const callback = useCallback(([entry]: IntersectionObserverEntry[]) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible')
    }
  }, [])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(callback, {
      threshold,
      rootMargin: '0px 0px -40px 0px',
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [callback, threshold])

  return ref
}

export function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    const mql = window.matchMedia(query)
    setMatches(mql.matches)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [query])

  return matches
}

export { GoalProvider, useGoal } from './useGoal'
