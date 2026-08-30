import { Link } from 'react-router-dom'
import { ArrowRight, Sparkle, ShoppingCart, ChartBar } from 'phosphor-react'
import { useScrollReveal } from '../../hooks'

const features = [
  {
    icon: Sparkle,
    title: 'AI Agents',
    desc: 'Natural language commands that execute real financial actions.',
    span: 'col-span-1 md:col-span-5 row-span-1',
  },
  {
    icon: ShoppingCart,
    title: 'Commerce',
    desc: 'Product catalog with Razorpay-powered checkout.',
    span: 'col-span-1 md:col-span-3 row-span-1',
  },
  {
    icon: ChartBar,
    title: 'Audit Trail',
    desc: 'Cryptographic proof of every agent action.',
    span: 'col-span-1 md:col-span-4 row-span-1',
  },
]

export default function HeroSection() {
  const headlineRef = useScrollReveal()
  const gridRef = useScrollReveal(0.05)

  return (
    <section className="relative min-h-[100dvh] flex flex-col items-center justify-center px-4 py-32 md:py-40 overflow-hidden">
      {/* ── Eyebrow ── */}
      <div ref={headlineRef} className="reveal text-center mb-8">
        <span className="inline-flex items-center gap-2 rounded-full bg-sage-pale px-4 py-1.5 text-[11px] uppercase tracking-[0.2em] font-medium text-sage border border-sage/10">
          <span className="w-1.5 h-1.5 rounded-full bg-sage animate-pulse" />
          AI-Powered Financial OS
        </span>
      </div>

      {/* ── Massive headline ── */}
      <div className="text-center max-w-5xl mx-auto mb-20">
        <h1
          ref={useScrollReveal()}
          className="reveal font-serif text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[0.95] text-ink mb-8"
        >
          Your money,
          <br />
          <span className="text-sage">directed by AI.</span>
        </h1>
        <p
          ref={useScrollReveal()}
          className="reveal text-lg md:text-xl text-ink-muted max-w-2xl mx-auto leading-relaxed"
        >
          Natural language commands that browse products, complete purchases,
          and maintain a cryptographically signed audit trail — all under your control.
        </p>
      </div>

      {/* ── CTA buttons ── */}
      <div ref={useScrollReveal()} className="reveal flex flex-col sm:flex-row items-center gap-4 mb-24">
        <Link
          to="/agent"
          className="group inline-flex items-center gap-0 rounded-full bg-ink text-cream pl-7 pr-2 py-2 text-base font-medium transition-all duration-700 ease-spring hover:bg-ink-soft active:scale-[0.97]"
        >
          <span>Start with the Agent</span>
          <span className="w-9 h-9 rounded-full bg-cream/10 flex items-center justify-center ml-3 transition-all duration-500 ease-spring group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:bg-cream/20">
            <ArrowRight weight="light" className="w-4 h-4" />
          </span>
        </Link>
        <Link
          to="/catalog"
          className="inline-flex items-center gap-2 rounded-full border border-border-warm px-7 py-3 text-base font-medium text-ink-soft transition-all duration-500 ease-spring hover:bg-parchment/40 hover:border-border-warm/60 active:scale-[0.97]"
        >
          Browse Catalog
        </Link>
      </div>

      {/* ── Asymmetrical bento feature grid ── */}
      <div
        ref={gridRef}
        className="reveal w-full max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-4 stagger-children"
      >
        {features.map((f) => (
          <div key={f.title} className={`reveal ${f.span}`}>
            <div className="group h-full rounded-[1.5rem] bg-cream-dark border border-border-faint p-1 transition-all duration-700 ease-spring hover:border-border-warm/60">
              <div className="h-full rounded-[calc(1.5rem-4px)] bg-white border border-border-faint/50 p-6 md:p-8 inset-highlight transition-all duration-700 ease-spring">
                <div className="w-10 h-10 rounded-full bg-sage-pale flex items-center justify-center mb-5 transition-all duration-500 ease-spring group-hover:bg-sage/10">
                  <f.icon weight="light" className="w-5 h-5 text-sage" />
                </div>
                <h3 className="font-serif text-xl font-semibold text-ink mb-2">{f.title}</h3>
                <p className="text-sm text-ink-muted leading-relaxed">{f.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
