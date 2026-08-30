import { useEffect, useState } from 'react'
import { ShieldCheck, CaretDown, CaretUp } from 'phosphor-react'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchAuditLog } from '../lib/api'
import type { AuditEntry } from '../types'
import { useScrollReveal } from '../hooks'
import { GlassButton } from '../components/ui/glass-button'

const EASE: [number, number, number, number] = [0.32, 0.72, 0, 1]

const actionColor: Record<string, string> = {
  checkout_session_created: 'bg-sage-pale text-sage border-sage/10',
  checkout_completed: 'bg-sage-pale text-sage border-sage/10',
  checkout_canceled: 'bg-parchment text-ink-muted border-border-faint',
  checkout_failed: 'bg-error-surface text-error border-error-border',
  catalog_browsed: 'bg-parchment text-ink-muted border-border-faint',
  unknown_action: 'bg-parchment text-ink-muted border-border-faint',
}

export default function Audit() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const headerRef = useScrollReveal()

  useEffect(() => {
    fetchAuditLog(100)
      .then((data) => setEntries(data.entries ?? data))
      .catch(() => setError('Failed to load audit log'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-[60dvh] px-4 py-24 md:py-32">
      <div className="max-w-3xl mx-auto">
        {/* ── Header ── */}
        <div ref={headerRef} className="reveal mb-12">
          <span className="inline-flex items-center gap-2 rounded-full bg-parchment px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-ink-muted mb-5">
            <ShieldCheck weight="light" className="w-3 h-3" />
            Audit Trail
          </span>
          <h1 className="font-serif text-4xl md:text-5xl font-bold tracking-tight text-ink mb-3">
            Audit Log
          </h1>
          <p className="text-base text-ink-muted">
            Every action, signed and timestamped. Click any entry to see the full payload and HMAC signature.
          </p>
        </div>

        {error && (
          <div className="mb-8 rounded-2xl bg-error-surface border border-error-border px-5 py-3 text-sm text-error">
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-20 rounded-2xl bg-parchment/50 animate-pulse" />
            ))}
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-14 h-14 rounded-full bg-parchment border border-border-faint flex items-center justify-center mx-auto mb-5">
              <ShieldCheck weight="light" className="w-6 h-6 text-ink-muted" />
            </div>
            <p className="text-sm text-ink-muted">No audit entries yet.</p>
            <p className="text-xs text-ink-muted/60 mt-1">Actions will appear here once the agent runs.</p>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence initial={false}>
              {entries.map((entry, i) => {
                const isOpen = expandedId === entry.id
                const colorClass = actionColor[entry.action] ?? actionColor.unknown_action

                return (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, ease: EASE, delay: i * 0.03 }}
                  >
                    <div className="rounded-[1.25rem] bg-cream-dark border border-border-faint p-1">
                      <div className="rounded-[calc(1.25rem-4px)] bg-white border border-border-faint/50 inset-highlight">
                        <GlassButton
                          variant="ghost"
                          onClick={() => setExpandedId(isOpen ? null : entry.id)}
                          className="w-full !rounded-[calc(1.25rem-4px)] justify-between"
                          contentClassName="flex items-center justify-between gap-4 w-full"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <span className={`shrink-0 inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ${colorClass}`}>
                              {entry.action.replace(/_/g, ' ')}
                            </span>
                            {entry.entity_type && (
                              <span className="font-mono text-[10px] text-ink-muted tracking-wider uppercase truncate">
                                {entry.entity_type}/{entry.entity_id}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 shrink-0">
                            <span className="font-mono text-[10px] text-ink-muted">
                              {new Date(entry.timestamp).toLocaleTimeString()}
                            </span>
                            {isOpen ? (
                              <CaretUp weight="light" className="w-4 h-4 text-ink-muted" />
                            ) : (
                              <CaretDown weight="light" className="w-4 h-4 text-ink-muted" />
                            )}
                          </div>
                        </GlassButton>

                        <AnimatePresence>
                          {isOpen && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.4, ease: EASE }}
                              className="overflow-hidden"
                            >
                              <div className="px-5 pb-5 space-y-3 border-t border-border-faint/50">
                                <div className="grid grid-cols-2 gap-3 pt-4">
                                  <div>
                                    <span className="text-[10px] uppercase tracking-wider text-ink-muted font-medium">Actor</span>
                                    <p className="text-sm text-ink mt-0.5">{entry.actor}</p>
                                  </div>
                                  <div>
                                    <span className="text-[10px] uppercase tracking-wider text-ink-muted font-medium">Result</span>
                                    <p className="text-sm text-ink mt-0.5">{entry.result || '—'}</p>
                                  </div>
                                </div>
                                {entry.signed_hash && (
                                  <div>
                                    <span className="text-[10px] uppercase tracking-wider text-ink-muted font-medium">HMAC Signature</span>
                                    <p className="font-mono text-[10px] text-ink-muted mt-0.5 break-all leading-relaxed">
                                      {entry.signed_hash}
                                    </p>
                                  </div>
                                )}
                                {entry.payload && (
                                  <div>
                                    <span className="text-[10px] uppercase tracking-wider text-ink-muted font-medium">Payload</span>
                                    <pre className="font-mono text-[10px] text-ink-muted mt-0.5 bg-parchment/30 rounded-xl p-3 overflow-x-auto whitespace-pre-wrap break-all">
                                      {typeof entry.payload === 'string'
                                        ? entry.payload
                                        : JSON.stringify(entry.payload, null, 2)}
                                    </pre>
                                  </div>
                                )}
                                {entry.error_reason && (
                                  <div>
                                    <span className="text-[10px] uppercase tracking-wider text-error font-medium">Error</span>
                                    <p className="text-sm text-error mt-0.5">{entry.error_reason}</p>
                                  </div>
                                )}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}
