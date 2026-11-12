import { Navigate, Route, Routes } from 'react-router-dom'
import { Shell } from './components/Shell'
import Overview from './pages/Overview'
import LiveCentre from './pages/LiveCentre'
import Scoring from './pages/Scoring'
import Tournaments from './pages/Tournaments'
import Teams from './pages/Teams'
import Simulation from './pages/Simulation'
import Device from './pages/Device'
import Analytics from './pages/Analytics'

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/live/:id?" element={<LiveCentre />} />
        <Route path="/score/:id?" element={<Scoring />} />
        <Route path="/tournaments/:id?" element={<Tournaments />} />
        <Route path="/teams/:id?" element={<Teams />} />
        <Route path="/sim/:id?" element={<Simulation />} />
        <Route path="/device" element={<Device />} />
        <Route path="/analytics/:id?" element={<Analytics />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  )
}
