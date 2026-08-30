import { Link } from 'react-router-dom'
import { ArrowRight, Sparkle, ShoppingCart, ChartBar } from 'phosphor-react'
import { useScrollReveal } from '../../hooks'
import { GlassButton } from '../ui/glass-button'

const features = [
  {
    icon: Sparkle,
    title: 'Talk, it does.',
    desc: 'Say what you want in plain English. The agent handles search, comparison, checkout.',
    span: 'col-span-1 md:col-span-5 row-span-1',
  },
  {
    icon: ShoppingCart,
    title: 'Real products.',
    desc: 'Browse a curated catalog. Pay with Razorpay. Get a receipt, not a hallucination.',
    span: 'col-span-1 md:col-span-3 row-span-1',
  },
  {
    icon: ChartBar,
    title: 'Signed receipts.',
    desc: 'Every action gets a cryptographic hash. Tamper-proof. Verifiable.',
    span: 'col-span-1 md:col-span-4 row-span-1',
  },
]

export default function HeroSection() {
  const headlineRef = useScrollReveal()
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
      <div ref={headlineRef} className="reveal text-center mb-8 relative z-10">
        <span className="inline-flex items-center gap-2 rounded-full bg-[#C7F464]/15 backdrop-blur-md px-5 py-2 text-[11px] uppercase tracking-[0.25em] font-semibold text-[#C7F464] border border-[#C7F464]/25 shadow-[0_0_20px_rgba(199,244,100,0.1)]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#C7F464] animate-pulse" />
          Financial OS with agents
        </span>
      </div>

      {/* ── Massive headline ── */}
      <div className="text-center max-w-5xl mx-auto mb-20 relative z-10">
        <h1
          ref={useScrollReveal()}
          className="reveal font-display text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[0.95] text-white mb-8"
        >
          Your money,
          <br />
          <span
            className="text-[#B8E634]"
            style={{
              textShadow: '0 0 40px rgba(184,230,52,0.4), 0 0 80px rgba(184,230,52,0.15)',
            }}
          >
            directed by you.
          </span>
        </h1>
        <p
          ref={useScrollReveal()}
          className="reveal text-lg md:text-xl text-white/70 max-w-2xl mx-auto leading-relaxed"
        >
          Tell the agent what you want. It browses products, completes checkout,
          and signs every action to a tamper-proof audit log. You stay in control.
        </p>
      </div>

      {/* ── CTA buttons ── */}
      <div ref={useScrollReveal()} className="reveal flex flex-col sm:flex-row items-center gap-4 mb-24 relative z-10">
        <Link to="/agent" className="no-underline">
          <GlassButton contentClassName="flex items-center gap-2">
            <span>Open the Agent</span>
            <ArrowRight weight="light" className="w-4 h-4" />
          </GlassButton>
        </Link>
        <Link to="/catalog" className="no-underline">
          <GlassButton variant="ghost-hero">
            Browse Products
          </GlassButton>
        </Link>
      </div>

      {/* ── Asymmetrical bento feature grid ── */}
      <div
        ref={gridRef}
        className="reveal w-full max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-4 stagger-children relative z-10"
      >
        {features.map((f) => (
          <div key={f.title} className={`reveal ${f.span}`}>
            <div className="group h-full rounded-[1.5rem] bg-[#0D1B0F]/60 backdrop-blur-md border border-white/10 p-1 transition-all duration-700 ease-spring hover:border-[#C7F464]/30 hover:bg-[#0D1B0F]/80">
              <div className="h-full rounded-[calc(1.5rem-4px)] bg-white/5 border border-white/5 p-6 md:p-8 transition-all duration-700 ease-spring">
                <div className="w-10 h-10 rounded-full bg-[#C7F464]/10 flex items-center justify-center mb-5 transition-all duration-500 ease-spring group-hover:bg-[#C7F464]/20 group-hover:shadow-[0_0_20px_rgba(199,244,100,0.15)]">
                  <f.icon weight="light" className="w-5 h-5 text-[#C7F464]" />
                </div>
                <h3 className="font-display text-xl font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-white/50 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
