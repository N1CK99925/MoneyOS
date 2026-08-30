import type { ReactNode } from 'react'
import Navbar from './Navbar'
import Footer from './Footer'
import GoalIndicator from '../ui/GoalIndicator'
import ShaderBackground from '../ui/ShaderBackground'

interface Props {
  children: ReactNode
  shaderOpacity?: number
}

export default function Layout({ children, shaderOpacity = 0.35 }: Props) {
  return (
    <div className="min-h-[100dvh] flex flex-col">
      {/* ── Shader background ── */}
      <ShaderBackground opacity={shaderOpacity} />

      {/* ── Grain overlay ── */}
      <div className="grain-overlay" aria-hidden="true" />

      <Navbar />
      <main className="flex-1 relative z-10">{children}</main>
      <Footer />
      <GoalIndicator />
    </div>
  )
}
