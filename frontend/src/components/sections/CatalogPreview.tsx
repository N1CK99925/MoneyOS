import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'phosphor-react'
import { useScrollReveal } from '../../hooks'
import { fetchCatalog } from '../../lib/api'
import type { CatalogItem } from '../../types'

export default function CatalogPreview() {
  const headerRef = useScrollReveal()
  const gridRef = useScrollReveal(0.05)
  const [items, setItems] = useState<CatalogItem[]>([])

  useEffect(() => {
    fetchCatalog()
      .then(setItems)
      .catch(() => setItems([]))
  }, [])

  return (
    <section className="px-4 py-24 md:py-32 border-t border-white/5">
      <div className="max-w-5xl mx-auto">
        {/* ── Section header ── */}
        <div ref={headerRef} className="reveal mb-14">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-8">
            <div>
              <div className="flex items-center gap-3 mb-6">
                <span className="w-8 h-px bg-[#C7F464]/60" />
                <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-[#C7F464]">
                  02 / Marketplace
                </span>
              </div>
              <h2 className="font-display text-4xl md:text-6xl font-bold tracking-tight uppercase leading-[0.95] text-white">
                What you
                <br />
                can buy
              </h2>
              <p className="mt-6 text-base md:text-lg text-white/50 max-w-lg leading-relaxed">
                Browse the catalog yourself, or tell the agent what you need —
                it finds, compares, and buys for you.
              </p>
            </div>

            <Link
              to="/catalog"
              className="group inline-flex items-center gap-3 rounded-none border border-white/20 px-6 py-3.5 text-sm font-mono uppercase tracking-[0.15em] text-white/80 no-underline transition-all duration-500 ease-spring hover:bg-[#C7F464] hover:text-[#0D1B0F] hover:border-[#C7F464] shrink-0 w-fit"
            >
              <span>View all</span>
              <ArrowRight weight="light" className="w-4 h-4 transition-transform duration-500 ease-spring group-hover:translate-x-1" />
            </Link>
          </div>
        </div>

        {/* ── Bento grid ── */}
        <div
          ref={gridRef}
          className="reveal grid grid-cols-1 md:grid-cols-12 gap-4"
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
                className={`group no-underline ${span}`}
              >
                <div className="h-full flex flex-col justify-between border border-white/10 bg-white/[0.03] backdrop-blur-sm p-7 transition-all duration-700 ease-spring hover:border-[#C7F464]/40 hover:bg-white/[0.06] min-h-[180px]">
                  <div>
                    <div className="flex items-start justify-between gap-4">
                      <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40 group-hover:text-[#C7F464]/80 transition-colors duration-500">
                        {item.id}
                      </span>
                      <span className="font-mono text-[10px] text-white/25">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                    </div>
                    <h3 className="font-display text-2xl md:text-3xl font-semibold uppercase text-white mt-5 mb-3 leading-tight">
                      {item.name}
                    </h3>
                    <p className="text-sm text-white/40 leading-relaxed line-clamp-2">
                      {item.description ?? ''}
                    </p>
                  </div>

                  <div className="flex items-center justify-between mt-8 pt-5 border-t border-white/10">
                    <span className="font-mono text-lg font-medium text-[#C7F464]">
                      ₹{Math.round(item.price_paise / 100)}
                    </span>
                    <span className="w-9 h-9 border border-white/15 flex items-center justify-center transition-all duration-500 ease-spring group-hover:bg-[#C7F464] group-hover:border-[#C7F464] group-hover:text-[#0D1B0F] text-white/60">
                      <ArrowRight weight="light" className="w-4 h-4" />
                    </span>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      </div>
    </section>
  )
}
