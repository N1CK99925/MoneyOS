import { Link } from 'react-router-dom'
import { ArrowRight } from 'phosphor-react'
import { useScrollReveal } from '../../hooks'
import type { CatalogItem } from '../../types'

interface Props {
  items?: CatalogItem[]
}

export default function CatalogPreview({ items = [] }: Props) {
  const headlineRef = useScrollReveal()
  const gridRef = useScrollReveal(0.05)

  return (
    <section className="px-4 py-24 md:py-32">
      <div className="max-w-5xl mx-auto">
        {/* ── Section header ── */}
        <div ref={headlineRef} className="reveal mb-16">
          <span className="inline-flex items-center gap-2 rounded-full bg-parchment px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-ink-muted mb-5">
            Marketplace
          </span>
          <h2 className="font-serif text-3xl md:text-5xl font-bold tracking-tight text-ink mb-4">
            Curated catalog
          </h2>
          <p className="text-base text-ink-muted max-w-lg">
            AI agents can search, compare, and purchase from this catalog — all through natural language.
          </p>
        </div>

        {/* ── Bento grid ── */}
        <div
          ref={gridRef}
          className="reveal grid grid-cols-1 md:grid-cols-12 gap-4 stagger-children"
        >
          {items.slice(0, 4).map((item, i) => {
            const span =
              i === 0 ? 'md:col-span-7 md:row-span-2' :
              i === 1 ? 'md:col-span-5' :
              i === 2 ? 'md:col-span-5' :
              'md:col-span-7'

            return (
              <Link
                key={item.id}
                to="/catalog"
                className={`reveal group ${span}`}
              >
                <div className="h-full rounded-[1.5rem] bg-cream-dark border border-border-faint p-1 transition-all duration-700 ease-spring hover:border-border-warm/60">
                  <div className="h-full rounded-[calc(1.5rem-4px)] bg-white border border-border-faint/50 p-6 inset-highlight flex flex-col justify-between min-h-[180px] transition-all duration-700 ease-spring group-hover:shadow-card-hover">
                    <div>
                      <span className="font-mono text-[10px] text-ink-muted tracking-wider uppercase">{item.id}</span>
                      <h3 className="font-serif text-xl font-semibold text-ink mt-2 mb-3">{item.name}</h3>
                      <p className="text-sm text-ink-muted leading-relaxed line-clamp-2">{item.description ?? ''}</p>
                    </div>
                    <div className="flex items-center justify-between mt-5">
                      <span className="font-mono text-base font-medium text-ink">
                        ₹{Math.round(item.price_paise / 100)}
                      </span>
                      <span className="w-8 h-8 rounded-full bg-parchment flex items-center justify-center transition-all duration-500 ease-spring group-hover:bg-sage group-hover:text-cream">
                        <ArrowRight weight="light" className="w-4 h-4" />
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>

        {/* ── View all link ── */}
        <div className="mt-10 text-center">
          <Link
            to="/catalog"
            className="group inline-flex items-center gap-0 rounded-full border border-border-warm px-6 py-3 text-sm font-medium text-ink-soft transition-all duration-500 ease-spring hover:bg-parchment/40 active:scale-[0.97]"
          >
            <span>View full catalog</span>
            <span className="w-7 h-7 rounded-full bg-parchment/60 flex items-center justify-center ml-3 transition-all duration-500 ease-spring group-hover:bg-sage group-hover:text-cream">
              <ArrowRight weight="light" className="w-3.5 h-3.5" />
            </span>
          </Link>
        </div>
      </div>
    </section>
  )
}
