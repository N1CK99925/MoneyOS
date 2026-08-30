import { Lightning } from 'phosphor-react'

export default function Footer() {
  return (
    <footer className="px-4 py-16 border-t border-border-faint">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-sage flex items-center justify-center">
            <Lightning weight="fill" className="w-3 h-3 text-cream" />
          </div>
          <span className="font-serif text-sm font-semibold text-ink">MoneyOS</span>
        </div>
        <p className="text-xs text-ink-muted font-mono tracking-wider">
          Financial OS • Buildathon 2026
        </p>
      </div>
    </footer>
  )
}
