import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Lightning, List, X } from 'phosphor-react'
import { useGoal } from '../../hooks'
import { GlassButton } from '../ui/glass-button'

const navLinks = [
  { to: '/', label: 'Home' },
  { to: '/catalog', label: 'Catalog' },
  { to: '/audit', label: 'Audit' },
  { to: '/settings', label: 'Settings' },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const { count } = useGoal()
  const location = useLocation()

  return (
    <>
      {/* ── Floating glass pill nav ── */}
      <nav className="fixed top-6 left-1/2 -translate-x-1/2 z-40 w-[calc(100%-2rem)] max-w-[720px]">
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
                className={`relative px-3 py-2 rounded-full text-sm font-medium transition-all duration-500 ease-spring ${location.pathname === link.to
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
              className={`hidden md:inline-flex no-underline ${count > 0 ? 'ring-2 ring-sage/30 rounded-full' : ''}`}
            >
              <GlassButton size="sm" contentClassName="flex items-center gap-2">
                <span>Launch Agent</span>
                {count > 0 && (
                  <span className="w-2 h-2 rounded-full bg-sage animate-pulse" />
                )}
              </GlassButton>
            </Link>

            {/* Hamburger */}
            <GlassButton
              size="icon"
              variant="ghost"
              onClick={() => setOpen(!open)}
              className="md:hidden"
              aria-label="Toggle menu"
            >
              {open ? (
                <X weight="light" className="w-5 h-5 text-ink" />
              ) : (
                <List weight="light" className="w-5 h-5 text-ink" />
              )}
            </GlassButton>
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
        className={`fixed inset-x-0 top-0 z-50 pt-28 pb-8 px-6 bg-cream/95 backdrop-blur-3xl border-b border-border-faint shadow-dropdown transition-all duration-700 ease-spring md:hidden ${open
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
            className="reveal no-underline mt-4"
            style={{ transitionDelay: '240ms' }}
          >
            <GlassButton contentClassName="flex items-center gap-2 w-full justify-center">
              <Lightning weight="fill" className="w-4 h-4" />
              <span>Launch Agent</span>
            </GlassButton>
          </Link>
        </div>
      </div>
    </>
  )
}
