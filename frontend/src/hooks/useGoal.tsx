import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import type { CatalogItem } from '@/types'

interface GoalItem {
  item: CatalogItem
  addedAt: number
}

interface GoalContextType {
  items: GoalItem[]
  addItem: (item: CatalogItem) => void
  removeItem: (id: string) => void
  clearItems: () => void
  buildGoal: () => string
  count: number
}

const GoalContext = createContext<GoalContextType | null>(null)

const STORAGE_KEY = 'moneyos-goal-items'

function loadItems(): GoalItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function GoalProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<GoalItem[]>(loadItems)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }, [items])

  const addItem = useCallback((item: CatalogItem) => {
    setItems((prev) => {
      if (prev.some((g) => g.item.id === item.id)) return prev
      return [...prev, { item, addedAt: Date.now() }]
    })
  }, [])

  const removeItem = useCallback((id: string) => {
    setItems((prev) => prev.filter((g) => g.item.id !== id))
  }, [])

  const clearItems = useCallback(() => {
    setItems([])
  }, [])

  const buildGoal = useCallback(() => {
    if (items.length === 0) return ''
    if (items.length === 1) return `Buy ${items[0].item.name}`
    const names = items.map((g) => g.item.name)
    const last = names.pop()
    return `Buy ${names.join(', ')} and ${last}`
  }, [items])

  return (
    <GoalContext.Provider
      value={{ items, addItem, removeItem, clearItems, buildGoal, count: items.length }}
    >
      {children}
    </GoalContext.Provider>
  )
}

export function useGoal() {
  const ctx = useContext(GoalContext)
  if (!ctx) throw new Error('useGoal must be used within GoalProvider')
  return ctx
}
