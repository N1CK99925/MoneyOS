import { Link } from 'react-router-dom'
import { ArrowRight, Lightning } from 'phosphor-react'
import { useScrollReveal } from '../../hooks'
import { GlassButton } from '../ui/glass-button'

export default function AgentCTA() {
  const leftRef = useScrollReveal()
  const rightRef = useScrollReveal(0.1)

  return (
    <section className="px-4 py-24 md:py-32 border-t border-white/5">
      <div className="max-w-5xl mx-auto border border-white/10 bg-white/[0.03] backdrop-blur-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
          {/* ── Left: editorial text ── */}
          <div ref={leftRef} className="reveal p-8 md:p-14 flex flex-col justify-center">
            <div className="flex items-center gap-3 mb-6">
              <span className="w-8 h-px bg-[#C7F464]/60" />
              <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-[#C7F464]">
                03 / Agent
              </span>
            </div>

            <h2 className="font-display text-4xl md:text-5xl font-bold tracking-tight uppercase leading-[0.95] text-white mb-7">
              Just tell it
              <br />
              what you want.
            </h2>

            <p className="text-base text-white/50 leading-relaxed mb-10 max-w-md">
              Say something like "find me a mechanical keyboard under 5000." The agent
              searches the catalog, picks the best match, and hands you a Razorpay
              checkout link. Every step gets signed to the audit log.
            </p>

            <Link to="/agent" className="no-underline w-fit">
              <GlassButton contentClassName="flex items-center gap-2">
                <span>Open Agent</span>
                <ArrowRight weight="light" className="w-3.5 h-3.5" />
              </GlassButton>
            </Link>
          </div>

          {/* ── Right: live preview ── */}
          <div ref={rightRef} className="reveal p-8 md:p-14 bg-white/[0.03] border-t md:border-t-0 md:border-l border-white/10">
            <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-white/40 mb-8">
              Live transcript
            </div>
            <div className="space-y-5">
              {/* Mock user message */}
              <div className="flex justify-end">
                <div className="bg-[#C7F464] text-[#0D1B0F] px-5 py-3 text-sm max-w-[85%] font-medium">
                  Find me a good keyboard under ₹5000
                </div>
              </div>
              {/* Mock agent tool calls */}
              <div className="flex gap-3">
                <div className="w-8 h-8 border border-[#C7F464]/30 bg-[#C7F464]/10 flex items-center justify-center shrink-0 mt-1">
                  <Lightning weight="fill" className="w-3 h-3 text-[#C7F464]" />
                </div>
                <div className="space-y-3 flex-1">
                  <div className="border border-white/10 bg-white/[0.04] px-5 py-3 text-sm text-white/70 max-w-[90%]">
                    <span className="font-mono text-white/40 text-xs block mb-1">search_catalog</span>
                    Mechanical keyboards, budget range
                  </div>
                  <div className="border border-white/10 bg-white/[0.04] px-5 py-3 text-sm text-white/70 max-w-[90%]">
                    <span className="font-mono text-white/40 text-xs block mb-1">create_checkout_session</span>
                    <span className="text-[#C7F464] font-medium">Ready for payment</span>
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
