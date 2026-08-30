import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { GoalProvider } from '@/hooks'
import { Layout } from '@/components/layout'
import GoalIndicator from '@/components/ui/GoalIndicator'
import { Home, Catalog, Agent, Audit } from '@/pages'

export default function App() {
  return (
    <BrowserRouter>
      <GoalProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/catalog" element={<Catalog />} />
            <Route path="/agent" element={<Agent />} />
            <Route path="/audit" element={<Audit />} />
          </Routes>
          <GoalIndicator />
        </Layout>
      </GoalProvider>
    </BrowserRouter>
  )
}
