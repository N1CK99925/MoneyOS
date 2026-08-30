import { Link } from 'react-router-dom'
import { ArrowRight, Lightning } from 'phosphor-react'
import { useScrollReveal } from '../../hooks'

export default function AgentCTA() {
  const leftRef = useScrollReveal()
  const rightRef = useScrollReveal(0.1)

  return (
    <section className="px-4 py-24 md:py-32">
      <div className="max-w-5xl mx-auto rounded-[2rem] bg-cream-dark border border-border-faint p-2">
        <div className="rounded-[calc(2rem-8px)] bg-white border border-border-faint/50 inset-highlight overflow-hidden">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
            {/* ── Left: editorial text ── */}
            <div ref={leftRef} className="reveal p-8 md:p-14 flex flex-col justify-center">
              <span className="inline-flex items-center gap-2 rounded-full bg-sage-pale px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-sage w-fit mb-6">
                <Lightning weight="fill" className="w-3 h-3" />
                Agent Interface
              </span>
              <h2 className="font-serif text-3xl md:text-4xl font-bold tracking-tight text-ink mb-5 leading-tight">
                Talk to your
                <br />
                financial OS.
              </h2>
              <p className="text-base text-ink-muted leading-relaxed mb-8">
                Ask in plain English. The agent browses the catalog, compares options,
                completes checkout via Razorpay, and signs every action to a tamper-proof audit log.
              </p>
              <Link
                to="/agent"
                className="group inline-flex items-center gap-0 rounded-full bg-ink text-cream pl-7 pr-2 py-2 text-sm font-medium w-fit transition-all duration-700 ease-spring hover:bg-ink-soft active:scale-[0.97]"
              >
                <span>Open Agent</span>
                <span className="w-8 h-8 rounded-full bg-cream/10 flex items-center justify-center ml-3 transition-all duration-500 ease-spring group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:bg-cream/20">
                  <ArrowRight weight="light" className="w-3.5 h-3.5" />
                </span>
              </Link>
            </div>

            {/* ── Right: live preview ── */}
            <div ref={rightRef} className="reveal p-8 md:p-14 bg-parchment/30 border-t md:border-t-0 md:border-l border-border-faint/50">
              <div className="space-y-4">
                {/* Mock user message */}
                <div className="flex justify-end">
                  <div className="rounded-2xl rounded-br-md bg-ink text-cream px-5 py-3 text-sm max-w-[85%]">
                    Find me a good keyboard under ₹5000
                  </div>
                </div>
                {/* Mock agent tool call */}
                <div className="flex gap-3">
                  <div className="w-7 h-7 rounded-full bg-sage-pale flex items-center justify-center shrink-0 mt-1">
                    <Lightning weight="fill" className="w-3 h-3 text-sage" />
                  </div>
                  <div className="space-y-2">
                    <div className="rounded-2xl rounded-bl-md bg-white border border-border-faint px-5 py-3 text-sm text-ink-soft max-w-[90%]">
                      <span className="text-ink-muted text-xs block mb-1">search_catalog</span>
                      Mechanical keyboards, budget range
                    </div>
                    <div className="rounded-2xl rounded-bl-md bg-white border border-border-faint px-5 py-3 text-sm text-ink-soft max-w-[90%]">
                      <span className="text-ink-muted text-xs block mb-1">create_checkout_session</span>
                      <span className="text-sage font-medium">Ready for payment</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
