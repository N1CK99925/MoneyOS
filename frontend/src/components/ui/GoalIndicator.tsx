import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Lightning, X, CaretUp, CaretDown } from 'phosphor-react'
import { useGoal } from '../../hooks'

export default function GoalIndicator() {
  const [expanded, setExpanded] = useState(false)
  const { items, removeItem, clearItems, count } = useGoal()
  if (count === 0) return null

  return (
    <div className="fixed bottom-6 right-6 z-40">
      {/* ── Collapsed pill ── */}
      {!expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="group flex items-center gap-3 rounded-full bg-ink/90 backdrop-blur-xl border border-white/10 pl-5 pr-2 py-2.5 shadow-floating-pill transition-all duration-700 ease-spring hover:shadow-floating-pill-hover hover:scale-[1.02] active:scale-[0.98]"
        >
          <div className="w-6 h-6 rounded-full bg-sage flex items-center justify-center">
            <Lightning weight="fill" className="w-3 h-3 text-cream" />
          </div>
          <span className="text-cream text-sm font-medium">{count} active</span>
          <span className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center transition-transform duration-300 ease-spring group-hover:translate-y-[-1px]">
            <CaretUp weight="light" className="w-3 h-3 text-cream" />
          </span>
        </button>
      )}

      {/* ── Expanded panel ── */}
      {expanded && (
        <div className="w-72 rounded-[1.5rem] bg-cream-dark border border-border-faint p-1 shadow-floating-panel transition-all duration-700 ease-spring">
          <div className="rounded-[calc(1.5rem-4px)] bg-white border border-border-faint/50 inset-highlight overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border-faint/50">
              <span className="text-xs font-medium text-ink">Goal Queue</span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => { clearItems(); setExpanded(false) }}
                  className="w-6 h-6 rounded-full bg-parchment/50 flex items-center justify-center text-ink-muted transition-all duration-300 ease-spring hover:bg-error-surface hover:text-error"
                  title="Clear all"
                >
                  <X weight="light" className="w-3 h-3" />
                </button>
                <button
                  onClick={() => setExpanded(false)}
                  className="w-6 h-6 rounded-full bg-parchment/50 flex items-center justify-center text-ink-muted transition-all duration-300 ease-spring hover:bg-parchment"
                >
                  <CaretDown weight="light" className="w-3 h-3" />
                </button>
              </div>
            </div>

            {/* Goal list */}
            <div className="max-h-48 overflow-y-auto">
              {items.map((goal) => (
                <div
                  key={goal.item.id}
                  className="flex items-center gap-3 px-5 py-3 border-b border-border-faint/30 last:border-0 group"
                >
                  <div className="w-5 h-5 rounded-full bg-sage-pale flex items-center justify-center shrink-0">
                    <Lightning weight="fill" className="w-2.5 h-2.5 text-sage" />
                  </div>
                  <span className="text-sm text-ink-soft truncate flex-1">{goal.item.name}</span>
                  <button
                    onClick={() => { removeItem(goal.item.id); if (count === 1) setExpanded(false) }}
                    className="w-5 h-5 rounded-full bg-parchment/50 flex items-center justify-center opacity-0 group-hover:opacity-100 text-ink-muted transition-all duration-300 ease-spring hover:bg-error-surface hover:text-error"
                  >
                    <X weight="light" className="w-2.5 h-2.5" />
                  </button>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-border-faint/50">
              <Link
                to="/agent"
                onClick={() => setExpanded(false)}
                className="flex items-center justify-center gap-2 w-full rounded-full bg-ink text-cream py-2.5 text-xs font-medium transition-all duration-500 ease-spring hover:bg-ink-soft active:scale-[0.98]"
              >
                <Lightning weight="fill" className="w-3 h-3" />
                <span>Open Agent</span>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
