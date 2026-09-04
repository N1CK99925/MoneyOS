import { useState, useRef, useEffect, useCallback } from 'react'
import { Lightning, X, PaperPlaneRight } from 'phosphor-react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { streamAgentRun } from '../lib/api'
import type { AgentMessage, AgentMessageType } from '../types'
import { useGoal, useScrollReveal } from '../hooks'
import { GlassButton } from '../components/ui/glass-button'

const EASE: [number, number, number, number] = [0.32, 0.72, 0, 1]

export default function Agent() {
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [isStretch, setIsStretch] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<(() => void) | null>(null)
  const lastRunGoal = useRef<string>('')
  const lastGoalFromContext = useRef<string>('')
  const directInputRef = useRef(false)
  const conversationHistoryRef = useRef<{ role: string; content: string }[]>([])
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

    // History = all previously completed turns, tracked in a ref (single source of truth).
    // Do NOT try to read it out of a setMessages updater — that runs asynchronously
    // during the next render, so it would still be empty here.
    const apiHistory = conversationHistoryRef.current

    setMessages((prev) => [...prev, userMsg])

    setIsStreaming(true)
    let agentContent = ''

    abortRef.current = streamAgentRun(
      goal,
      (chunk, type) => {
        const msgType: AgentMessageType = type || 'message'

        if (msgType === 'progress') {
          // Replace the last progress message if it exists
          setMessages((prev) => {
            const last = prev[prev.length - 1]
            if (last?.role === 'assistant' && last.type === 'progress') {
              return [...prev.slice(0, -1), { ...last, content: chunk, timestamp: Date.now() }]
            }
            return [...prev, { id: crypto.randomUUID(), role: 'assistant', content: chunk, timestamp: Date.now(), type: 'progress' }]
          })
          return
        }

        // Message content — append or create
        agentContent += chunk
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === 'assistant' && last.type !== 'progress') {
            return [...prev.slice(0, -1), { ...last, content: agentContent }]
          }
          return [...prev, { id: crypto.randomUUID(), role: 'assistant', content: agentContent, timestamp: Date.now() }]
        })
      },
      () => {
        // On completion — persist this turn so the next message has full context
        conversationHistoryRef.current = [
          ...conversationHistoryRef.current,
          { role: 'user', content: goal },
          ...(agentContent ? [{ role: 'assistant' as const, content: agentContent }] : []),
        ]
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
      apiHistory,
    )
  }, [isStreaming, isStretch])

  useEffect(() => {
    if (directInputRef.current) {
      directInputRef.current = false
      lastGoalFromContext.current = goalText
      return
    }
    if (goalText && goalText !== lastGoalFromContext.current && !isStreaming && goalText !== lastRunGoal.current) {
      lastGoalFromContext.current = goalText
      runGoal(goalText)
    }
  }, [goalText, isStreaming, runGoal])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const goal = input.trim()
    if (!goal || isStreaming) return
    setInput('')
    directInputRef.current = true
    lastRunGoal.current = goal
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
            Agent
          </span>
          <h1 className="font-serif text-3xl md:text-4xl font-bold tracking-tight text-ink">
            Talk to MoneyOS
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
              <p className="text-xs text-ink-muted/60">Tell the agent what you want to buy.</p>
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
                      : msg.type === 'progress'
                        ? 'bg-transparent text-ink-muted/60 text-xs px-2 py-1 italic'
                        : 'bg-white border border-border-faint text-ink-soft rounded-bl-md'
                  }`}
                >
                  {msg.content ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  ) : (
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
                placeholder="What do you want to buy?"
                rows={1}
                className="flex-1 bg-transparent px-5 py-4 text-sm text-ink placeholder:text-ink-muted outline-none resize-none min-h-[48px] max-h-[120px]"
                style={{ height: 'auto' }}
              />
              <div className="flex items-center gap-2 pr-3 pb-3">
                <GlassButton
                  size="sm"
                  variant={isStretch ? "sage" : "ghost"}
                  type="button"
                  onClick={() => setIsStretch(!isStretch)}
                  title={isStretch ? 'Research mode ON' : 'Research mode OFF'}
                >
                  {isStretch ? 'Research ON' : 'Research OFF'}
                </GlassButton>
                {isStreaming ? (
                  <GlassButton
                    size="icon"
                    type="button"
                    onClick={handleStop}
                    className="!h-9 !w-9 !rounded-full"
                  >
                    <X weight="light" className="w-4 h-4" />
                  </GlassButton>
                ) : (
                  <GlassButton
                    size="icon"
                    type="submit"
                    disabled={!input.trim()}
                    className="!h-9 !w-9 !rounded-full"
                  >
                    <PaperPlaneRight weight="light" className="w-4 h-4" />
                  </GlassButton>
                )}
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
