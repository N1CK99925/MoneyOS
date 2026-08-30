import { Link } from 'react-router-dom'
import { ArrowRight, Lightning } from 'phosphor-react'
import { useScrollReveal } from '../../hooks'
import { GlassButton } from '../ui/glass-button'

export default function AgentCTA() {
  const leftRef = useScrollReveal()
  const rightRef = useScrollReveal(0.1)

  return (
    <section className="px-4 py-24 md:py-32">
      <div className="max-w-5xl mx-auto rounded-[2rem] bg-white/5 backdrop-blur-sm border border-white/10 p-2">
        <div className="rounded-[calc(2rem-8px)] bg-white/5 border border-white/5 overflow-hidden">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
            {/* ── Left: editorial text ── */}
            <div ref={leftRef} className="reveal p-8 md:p-14 flex flex-col justify-center">
              <span className="inline-flex items-center gap-2 rounded-full bg-[#C7F464]/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-[#C7F464] w-fit mb-6 border border-[#C7F464]/20">
                <Lightning weight="fill" className="w-3 h-3" />
                Agent
              </span>
              <h2 className="font-display text-3xl md:text-4xl font-bold tracking-tight text-white mb-5 leading-tight">
                Just tell it
                <br />
                what you want.
              </h2>
              <p className="text-base text-white/50 leading-relaxed mb-8">
                Say something like "find me a mechanical keyboard under 5000." The agent searches the catalog, picks the best match, and hands you a Razorpay checkout link. Every step gets signed to the audit log.
              </p>
              <Link to="/agent" className="no-underline w-fit">
                <GlassButton contentClassName="flex items-center gap-2">
                  <span>Open Agent</span>
                  <ArrowRight weight="light" className="w-3.5 h-3.5" />
                </GlassButton>
              </Link>
            </div>

            {/* ── Right: live preview ── */}
            <div ref={rightRef} className="reveal p-8 md:p-14 bg-white/5 border-t md:border-t-0 md:border-l border-white/10">
              <div className="space-y-4">
                {/* Mock user message */}
                <div className="flex justify-end">
                  <div className="rounded-2xl rounded-br-md bg-[#C7F464] text-[#0D1B0F] px-5 py-3 text-sm max-w-[85%] font-medium">
                    Find me a good keyboard under ₹5000
                  </div>
                </div>
                {/* Mock agent tool call */}
                <div className="flex gap-3">
                  <div className="w-7 h-7 rounded-full bg-[#C7F464]/10 flex items-center justify-center shrink-0 mt-1 border border-[#C7F464]/20">
                    <Lightning weight="fill" className="w-3 h-3 text-[#C7F464]" />
                  </div>
                  <div className="space-y-2">
                    <div className="rounded-2xl rounded-bl-md bg-white/10 border border-white/10 px-5 py-3 text-sm text-white/70 max-w-[90%]">
                      <span className="text-white/40 text-xs block mb-1">search_catalog</span>
                      Mechanical keyboards, budget range
                    </div>
                    <div className="rounded-2xl rounded-bl-md bg-white/10 border border-white/10 px-5 py-3 text-sm text-white/70 max-w-[90%]">
                      <span className="text-white/40 text-xs block mb-1">create_checkout_session</span>
                      <span className="text-[#C7F464] font-medium">Ready for payment</span>
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
