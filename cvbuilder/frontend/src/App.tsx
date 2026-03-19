import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AppLayout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Profile } from './pages/Profile'
import { Sections } from './pages/Sections'
import { Publications } from './pages/Publications'
import { Templates } from './pages/Templates'
import { Export } from './pages/Export'
import { CVInstances } from './pages/CVInstances'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { Users } from './pages/Users'

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/profile" element={<Profile />} />
                      <Route path="/sections" element={<Sections />} />
                      <Route path="/publications" element={<Publications />} />
                      <Route path="/cvs" element={<CVInstances />} />
                      <Route path="/export" element={<Export />} />
                      <Route path="/templates" element={<Templates />} />
                      <Route path="/users" element={<Users />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
