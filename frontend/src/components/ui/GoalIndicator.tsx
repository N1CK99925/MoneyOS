import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Lightning, X, CaretUp, CaretDown } from 'phosphor-react'
import { useGoal } from '../../hooks'
import { GlassButton } from './glass-button'

export default function GoalIndicator() {
  const [expanded, setExpanded] = useState(false)
  const { items, removeItem, clearItems, count } = useGoal()
  if (count === 0) return null

  return (
    <div className="fixed bottom-6 right-6 z-40">
      {/* ── Collapsed pill ── */}
      {!expanded && (
        <GlassButton onClick={() => setExpanded(true)}>
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-full bg-sage flex items-center justify-center">
              <Lightning weight="fill" className="w-3 h-3 text-cream" />
            </div>
            <span className="text-cream text-sm font-medium">{count} active</span>
            <CaretUp weight="light" className="w-3 h-3 text-cream" />
          </div>
        </GlassButton>
      )}

      {/* ── Expanded panel ── */}
      {expanded && (
        <div className="w-72 rounded-[1.5rem] bg-cream-dark border border-border-faint p-1 shadow-floating-panel transition-all duration-700 ease-spring">
          <div className="rounded-[calc(1.5rem-4px)] bg-white border border-border-faint/50 inset-highlight overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border-faint/50">
              <span className="text-xs font-medium text-ink">Goal Queue</span>
              <div className="flex items-center gap-1">
                <GlassButton
                  size="icon"
                  variant="ghost"
                  onClick={() => { clearItems(); setExpanded(false) }}
                  className="!h-6 !w-6 !rounded-full"
                  title="Clear all"
                >
                  <X weight="light" className="w-3 h-3" />
                </GlassButton>
                <GlassButton
                  size="icon"
                  variant="ghost"
                  onClick={() => setExpanded(false)}
                  className="!h-6 !w-6 !rounded-full"
                >
                  <CaretDown weight="light" className="w-3 h-3" />
                </GlassButton>
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
                  <GlassButton
                    size="icon"
                    variant="ghost"
                    onClick={() => { removeItem(goal.item.id); if (count === 1) setExpanded(false) }}
                    className="!h-5 !w-5 !rounded-full opacity-0 group-hover:opacity-100"
                  >
                    <X weight="light" className="w-2.5 h-2.5" />
                  </GlassButton>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-border-faint/50">
              <Link
                to="/agent"
                onClick={() => setExpanded(false)}
                className="no-underline"
              >
                <GlassButton className="w-full">
                  <div className="flex items-center justify-center gap-2">
                    <Lightning weight="fill" className="w-3 h-3" />
                    <span>Open Agent</span>
                  </div>
                </GlassButton>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
