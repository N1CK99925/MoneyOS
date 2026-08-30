import { useState, useRef, useEffect, useCallback } from 'react'
import { Lightning, X, PaperPlaneRight } from 'phosphor-react'
import { motion, AnimatePresence } from 'framer-motion'
import { streamAgentRun } from '../lib/api'
import type { AgentMessage } from '../types'
import { useGoal, useScrollReveal } from '../hooks'

const EASE: [number, number, number, number] = [0.32, 0.72, 0, 1]

export default function Agent() {
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [isStretch, setIsStretch] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<(() => void) | null>(null)
  const lastRunGoal = useRef<string>('')
  const { buildGoal, clearItems } = useGoal()
  const headerRef = useScrollReveal()

  const goalText = buildGoal()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(scrollToBottom, [messages])

  const runGoal = useCallback((goal: string) => {
    if (isStreaming) return
    lastRunGoal.current = goal
    const now = Date.now()
    const userMsg: AgentMessage = { id: crypto.randomUUID(), role: 'user', content: goal, timestamp: now }
    setMessages((prev) => [...prev, userMsg])
    setIsStreaming(true)
    let agentContent = ''

    abortRef.current = streamAgentRun(
      goal,
      (chunk) => {
        agentContent += chunk
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === 'assistant') {
            return [...prev.slice(0, -1), { ...last, content: agentContent }]
          }
          return [...prev, { id: crypto.randomUUID(), role: 'assistant', content: agentContent, timestamp: Date.now() }]
        })
      },
      () => {
        setIsStreaming(false)
        abortRef.current = null
      },
      (err) => {
        setMessages((prev) => [
          ...prev,
          { id: crypto.randomUUID(), role: 'assistant', content: `Error: ${err.message}`, timestamp: Date.now() },
        ])
        setIsStreaming(false)
        abortRef.current = null
      },
      isStretch,
    )
  }, [isStreaming, isStretch])

  useEffect(() => {
    if (goalText && !isStreaming && goalText !== lastRunGoal.current) {
      runGoal(goalText)
    }
  }, [goalText]) // only watch goalText — isStreaming handled inside runGoal

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const goal = input.trim()
    if (!goal || isStreaming) return
    setInput('')
    lastRunGoal.current = ''
    runGoal(goal)
  }

  const handleStop = () => {
    abortRef.current?.()
    setIsStreaming(false)
    abortRef.current = null
    clearItems()
  }

  return (
    <div className="min-h-[100dvh] flex flex-col px-4 pt-28 pb-8 md:pt-32 md:pb-12">
      <div className="w-full max-w-3xl mx-auto flex flex-col flex-1">
        {/* ── Header ── */}
        <div ref={headerRef} className="reveal mb-8 text-center">
          <span className="inline-flex items-center gap-2 rounded-full bg-sage-pale px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-sage mb-5">
            <Lightning weight="fill" className="w-3 h-3" />
            Agent Interface
          </span>
          <h1 className="font-serif text-3xl md:text-4xl font-bold tracking-tight text-ink">
            Financial Agent
          </h1>
        </div>

        {/* ── Messages ── */}
        <div className="flex-1 overflow-y-auto space-y-5 mb-6 min-h-0">
          {messages.length === 0 && (
            <div className="text-center py-20">
              <div className="w-14 h-14 rounded-full bg-parchment border border-border-faint flex items-center justify-center mx-auto mb-5">
                <Lightning weight="light" className="w-6 h-6 text-ink-muted" />
              </div>
              <p className="text-sm text-ink-muted mb-1">No messages yet.</p>
              <p className="text-xs text-ink-muted/60">Type a goal below to get started.</p>
            </div>
          )}
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: EASE }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'gap-3'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-sage-pale border border-sage/10 flex items-center justify-center shrink-0 mt-1">
                    <Lightning weight="fill" className="w-3 h-3 text-sage" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-ink text-cream rounded-br-md'
                      : 'bg-white border border-border-faint text-ink-soft rounded-bl-md'
                  }`}
                >
                  {msg.content || (
                    <span className="inline-flex items-center gap-1.5 text-ink-muted">
                      <span className="w-1.5 h-1.5 rounded-full bg-sage animate-pulse" />
                      Thinking...
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        {/* ── Input area ── */}
        <form onSubmit={handleSubmit} className="relative">
          <div className="rounded-[1.5rem] bg-cream-dark border border-border-faint p-1.5 transition-all duration-500 ease-spring focus-within:border-sage/20 focus-within:shadow-card">
            <div className="rounded-[calc(1.5rem-6px)] bg-white border border-border-faint/50 flex items-end inset-highlight transition-all duration-500 ease-spring focus-within:border-sage/10">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit(e)
                  }
                }}
                placeholder="Ask the agent to do something..."
                rows={1}
                className="flex-1 bg-transparent px-5 py-4 text-sm text-ink placeholder:text-ink-muted outline-none resize-none min-h-[48px] max-h-[120px]"
                style={{ height: 'auto' }}
              />
              <div className="flex items-center gap-2 pr-3 pb-3">
                <button
                  type="button"
                  onClick={() => setIsStretch(!isStretch)}
                  className={`rounded-full px-3 py-1.5 text-[10px] uppercase tracking-wider font-medium border transition-all duration-500 ease-spring ${
                    isStretch
                      ? 'bg-sage-pale border-sage/20 text-sage'
                      : 'bg-parchment/50 border-border-faint text-ink-muted hover:bg-parchment'
                  }`}
                  title={isStretch ? 'Research mode ON' : 'Research mode OFF'}
                >
                  {isStretch ? 'Research ON' : 'Research OFF'}
                </button>
                {isStreaming ? (
                  <button
                    type="button"
                    onClick={handleStop}
                    className="w-9 h-9 rounded-full bg-error/10 border border-error/20 flex items-center justify-center transition-all duration-300 ease-spring hover:bg-error/20 active:scale-[0.95]"
                  >
                    <X weight="light" className="w-4 h-4 text-error" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={!input.trim()}
                    className="w-9 h-9 rounded-full bg-sage flex items-center justify-center text-cream transition-all duration-500 ease-spring hover:bg-sage-light active:scale-[0.95] disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <PaperPlaneRight weight="light" className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
