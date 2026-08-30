import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Lightning } from 'phosphor-react'
import { useGoal } from '../../hooks'

const navLinks = [
  { to: '/', label: 'Home' },
  { to: '/catalog', label: 'Catalog' },
  { to: '/audit', label: 'Audit' },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const { count } = useGoal()
  const location = useLocation()

  return (
    <>
      {/* ── Floating glass pill nav ── */}
      <nav className="fixed top-6 left-1/2 -translate-x-1/2 z-40 w-[calc(100%-2rem)] max-w-[640px]">
        <div className="relative flex items-center justify-between rounded-full bg-cream/80 backdrop-blur-xl border border-border-faint px-5 py-3 shadow-nav transition-all duration-700 ease-spring">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group" onClick={() => setOpen(false)}>
            <img
              src="/logo.png"
              alt="MoneyOS"
              className="w-7 h-7 object-contain transition-transform duration-700 ease-spring group-hover:scale-110"
            />

            <span className="font-serif text-lg font-semibold tracking-tight text-ink">
              MoneyOS
            </span>
          </Link>
          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`relative px-4 py-2 rounded-full text-sm font-medium transition-all duration-500 ease-spring ${location.pathname === link.to
                  ? 'text-ink'
                  : 'text-ink-muted hover:text-ink'
                  }`}
              >
                {link.label}
                {location.pathname === link.to && (
                  <span className="absolute inset-0 rounded-full bg-parchment/60 -z-10" />
                )}
              </Link>
            ))}
          </div>

          {/* CTA + hamburger */}
          <div className="flex items-center gap-2">
            <Link
              to="/agent"
              className={`hidden md:inline-flex items-center gap-2 rounded-full bg-ink text-cream px-5 py-2.5 text-sm font-medium transition-all duration-700 ease-spring hover:bg-ink-soft active:scale-[0.97] ${count > 0 ? 'ring-2 ring-sage/30' : ''
                }`}
            >
              <span>Launch Agent</span>
              {count > 0 && (
                <span className="w-2 h-2 rounded-full bg-sage animate-pulse" />
              )}
            </Link>

            {/* Hamburger */}
            <button
              onClick={() => setOpen(!open)}
              className="md:hidden relative w-10 h-10 rounded-full bg-parchment/50 flex items-center justify-center transition-all duration-500 ease-spring hover:bg-parchment"
              aria-label="Toggle menu"
            >
              <div className="relative w-5 h-4">
                <span
                  className={`absolute left-0 w-full h-[1.5px] bg-ink rounded-full transition-all duration-500 ease-spring ${open ? 'top-1/2 -translate-y-1/2 rotate-45' : 'top-0'
                    }`}
                />
                <span
                  className={`absolute left-0 top-1/2 -translate-y-1/2 w-full h-[1.5px] bg-ink rounded-full transition-all duration-500 ease-spring ${open ? 'opacity-0 scale-x-0' : 'opacity-100 scale-x-100'
                    }`}
                />
                <span
                  className={`absolute left-0 w-full h-[1.5px] bg-ink rounded-full transition-all duration-500 ease-spring ${open ? 'top-1/2 -translate-y-1/2 -rotate-45' : 'bottom-0'
                    }`}
                />
              </div>
            </button>
          </div>
        </div>
      </nav>

      {/* ── Mobile overlay ── */}
      <div
        className={`fixed inset-0 z-30 bg-ink/10 backdrop-blur-sm transition-opacity duration-500 ease-spring md:hidden ${open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
        onClick={() => setOpen(false)}
      />

      {/* ── Mobile menu ── */}
      <div
        className={`fixed inset-x-0 top-0 z-35 pt-28 pb-8 px-6 bg-cream/95 backdrop-blur-3xl border-b border-border-faint shadow-dropdown transition-all duration-700 ease-spring md:hidden ${open
          ? 'translate-y-0 opacity-100 pointer-events-auto'
          : '-translate-y-full opacity-0 pointer-events-none'
          }`}
      >
        <div className="flex flex-col gap-1 stagger-children">
          {navLinks.map((link, i) => (
            <Link
              key={link.to}
              to={link.to}
              onClick={() => setOpen(false)}
              className={`reveal flex items-center gap-3 px-4 py-4 rounded-2xl text-lg font-medium transition-all duration-500 ease-spring ${location.pathname === link.to
                ? 'bg-parchment/60 text-ink'
                : 'text-ink-muted hover:bg-parchment/30 hover:text-ink'
                }`}
              style={{ transitionDelay: `${i * 80}ms` }}
            >
              {link.label}
            </Link>
          ))}
          <Link
            to="/agent"
            onClick={() => setOpen(false)}
            className="reveal flex items-center justify-center gap-2 mt-4 rounded-full bg-ink text-cream px-6 py-4 text-base font-medium transition-all duration-700 ease-spring active:scale-[0.97]"
            style={{ transitionDelay: '240ms' }}
          >
            <Lightning weight="fill" className="w-4 h-4" />
            <span>Launch Agent</span>
          </Link>
        </div>
      </div>
    </>
  )
}
