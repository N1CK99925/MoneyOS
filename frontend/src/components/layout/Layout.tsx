import type { ReactNode } from 'react'
import Navbar from './Navbar'
import Footer from './Footer'
import GoalIndicator from '../ui/GoalIndicator'

interface Props {
  children: ReactNode
}

export default function Layout({ children }: Props) {
  return (
    <div className="min-h-[100dvh] flex flex-col">
      {/* ── Grain overlay ── */}
      <div className="grain-overlay" aria-hidden="true" />

      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
      <GoalIndicator />
    </div>
  )
}
