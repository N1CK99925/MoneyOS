import { Link, useLocation } from 'react-router-dom'
import { Lightning } from 'phosphor-react'

export default function Footer() {
  const location = useLocation()
  const isHome = location.pathname === '/'

  return (
    <footer className={`px-4 py-16 border-t ${isHome ? 'border-white/10' : 'border-border-faint'}`}>
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <Link to="/" className="flex items-center gap-3 no-underline group">
          <div className={`w-6 h-6 flex items-center justify-center transition-colors duration-500 ${isHome ? 'border border-[#C7F464]/40' : 'rounded-full bg-sage'}`}>
            <Lightning weight="fill" className={`w-3 h-3 ${isHome ? 'text-[#C7F464]' : 'text-cream'}`} />
          </div>
          <span className={`font-display text-sm font-semibold uppercase tracking-wide transition-colors duration-500 ${isHome ? 'text-white' : 'text-ink'}`}>
            MoneyOS
          </span>
        </Link>
        <div className={`flex items-center gap-6 font-mono text-xs uppercase tracking-[0.2em] transition-colors duration-500 ${isHome ? 'text-white/40' : 'text-ink-muted'}`}>
          <span>Financial OS</span>
          <span className={`${isHome ? 'text-[#C7F464]/60' : 'text-sage/60'}`}>/</span>
          <span>Buildathon 2026</span>
        </div>
      </div>
    </footer>
  )
}
