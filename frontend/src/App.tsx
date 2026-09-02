import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { GoalProvider } from '@/hooks'
import { Layout } from '@/components/layout'
import GoalIndicator from '@/components/ui/GoalIndicator'
import { Home, Catalog, Agent, Audit, Settings } from '@/pages'

function AppRoutes() {
  const location = useLocation()
  const isHome = location.pathname === '/'
  return (
    <Layout shaderOpacity={isHome ? 1.0 : 0.5}>
      <Routes location={location}>
        <Route path="/" element={<Home />} />
        <Route path="/catalog" element={<Catalog />} />
        <Route path="/agent" element={<Agent />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
      <GoalIndicator />
    </Layout>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <GoalProvider>
        <AppRoutes />
      </GoalProvider>
    </BrowserRouter>
  )
}
