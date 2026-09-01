import { Link } from 'react-router-dom'
import { ArrowRight, MagnifyingGlass, ShieldCheck, LockKey, ChartBar } from 'phosphor-react'
import { useScrollReveal } from '../../hooks'
import { GlassButton } from '../ui/glass-button'

const steps = [
  {
    n: '01',
    icon: MagnifyingGlass,
    title: 'Search',
    desc: 'Say what you want in plain English. The agent queries the real catalog.',
  },
  {
    n: '02',
    icon: ShieldCheck,
    title: 'Compare & choose',
    desc: 'It weighs the options against your goal, then picks the best match.',
  },
  {
    n: '03',
    icon: LockKey,
    title: 'Pay',
    desc: 'A live Razorpay checkout — real payment, not a hallucination.',
  },
  {
    n: '04',
    icon: ChartBar,
    title: 'Signed audit',
    desc: 'Every action gets a cryptographic hash. Tamper-proof. Verifiable.',
  },
]

const stats = [
  { value: '4-step', label: 'pipeline, fully automated' },
  { value: '100%', label: 'real products & payments' },
  { value: 'SHA-256', label: 'signed actions, verifiable' },
]

const how = ['goal', 'search', 'compare', 'checkout', 'signed']

export default function HeroSection() {
  const eyebrowRef = useScrollReveal()
  const titleRef = useScrollReveal()
  const leadRef = useScrollReveal()
  const ctaRef = useScrollReveal()
  const howRef = useScrollReveal()
  const statsRef = useScrollReveal()
  const gridRef = useScrollReveal(0.05)

  return (
    <section className="relative min-h-[100dvh] flex flex-col items-center justify-center px-4 py-32 md:py-40 overflow-hidden">
      {/* ── Dark vignette behind text — pushes bright glow to edges ── */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 80% 60% at 50% 45%, rgba(13,27,15,0.75) 0%, rgba(13,27,15,0.35) 45%, transparent 75%)',
        }}
        aria-hidden="true"
      />

      {/* ── Bottom fade into next section ── */}
      <div
        className="absolute bottom-0 left-0 right-0 h-40 pointer-events-none"
        style={{
          background: 'linear-gradient(to bottom, transparent 0%, rgba(13,27,15,0.8) 100%)',
        }}
        aria-hidden="true"
      />

      {/* ── Eyebrow ── */}
      <div ref={eyebrowRef} className="reveal text-center mb-8 relative z-10">
        <span className="inline-flex items-center gap-2 rounded-full bg-[#C7F464]/10 backdrop-blur-md px-5 py-2 text-[11px] uppercase tracking-[0.3em] font-mono text-[#C7F464] border border-[#C7F464]/25">
          <span className="w-1.5 h-1.5 rounded-full bg-[#C7F464] animate-pulse" />
          Financial OS · agents
        </span>
      </div>

      {/* ── Headline ── */}
      <div ref={titleRef} className="reveal text-center max-w-5xl mx-auto mb-8 relative z-10">
        <h1 className="font-display text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[0.95] uppercase text-white">
          Your money,
          <br />
          <span className="hero-accent">directed by you.</span>
        </h1>
      </div>

      {/* ── Lead ── */}
      <div ref={leadRef} className="reveal text-center relative z-10 mb-10">
        <p className="text-lg md:text-xl text-white/70 max-w-2xl mx-auto leading-relaxed">
          Tell the agent what you want. It browses the real catalog, compares options,
          completes checkout, and signs every action to a tamper-proof audit trail.
          You stay in control.
        </p>
      </div>

      {/* ── CTA ── */}
      <div ref={ctaRef} className="reveal flex flex-col sm:flex-row items-center gap-4 mb-14 relative z-10">
        <Link to="/agent" className="no-underline">
          <GlassButton contentClassName="flex items-center gap-2">
            <span>Open the Agent</span>
            <ArrowRight weight="light" className="w-4 h-4" />
          </GlassButton>
        </Link>
        <Link to="/catalog" className="no-underline">
          <GlassButton variant="ghost-hero">Browse Products</GlassButton>
        </Link>
      </div>

      {/* ── Pipeline strip ── */}
      <div ref={howRef} className="reveal w-full max-w-5xl mx-auto mb-6 relative z-10">
        <div className="flex items-center justify-center gap-2 flex-wrap font-mono text-[11px] uppercase tracking-[0.2em] text-white/40">
          <span className="text-[#C7F464]">/how</span>
          {how.map((step, i) => (
            <span key={step} className="flex items-center gap-2">
              {i > 0 && <span className="text-[#C7F464]/70">→</span>}
              <span>{step}</span>
            </span>
          ))}
        </div>
      </div>

      {/* ── Stat strip ── */}
      <div ref={statsRef} className="reveal w-full max-w-5xl mx-auto mb-14 relative z-10">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10">
          {stats.map((s) => (
            <div key={s.value} className="bg-[#0D1B0F]/70 backdrop-blur-md px-6 py-5 text-center">
              <div className="font-mono text-2xl md:text-3xl font-semibold text-[#C7F464]">{s.value}</div>
              <div className="mt-1 text-[11px] uppercase tracking-[0.18em] text-white/50">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Pipeline bento ── */}
      <div
        ref={gridRef}
        className="reveal w-full max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-4 stagger-children relative z-10"
      >
        {steps.map((f, i) => {
          const span =
            i === 0 ? 'md:col-span-5' :
            i === 1 ? 'md:col-span-7' :
            i === 2 ? 'md:col-span-7' :
            'md:col-span-5'
          return (
            <div key={f.title} className={span}>
              <div className="group h-full rounded-2xl bg-[#0D1B0F]/60 backdrop-blur-md border border-white/10 p-5 transition-all duration-700 ease-spring hover:border-[#C7F464]/30 hover:bg-[#0D1B0F]/80">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 shrink-0 rounded-full bg-[#C7F464]/10 flex items-center justify-center transition-all duration-500 ease-spring group-hover:bg-[#C7F464]/20">
                      <f.icon weight="light" className="w-5 h-5 text-[#C7F464]" />
                    </div>
                    <h3 className="font-display text-xl font-semibold uppercase text-white">{f.title}</h3>
                  </div>
                  <span className="font-mono text-[11px] text-white/30 group-hover:text-[#C7F464]/70 transition-colors duration-500">{f.n}</span>
                </div>
                <p className="mt-4 text-sm text-white/50 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
