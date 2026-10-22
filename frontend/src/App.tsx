import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { RunProvider } from './context/RunContext'
import { ThemeProvider } from './context/ThemeContext'
import { AgentActivityPage } from './pages/AgentActivityPage'
import { ApprovalsPage } from './pages/ApprovalsPage'
import { DashboardPage } from './pages/DashboardPage'
import { FailuresPage } from './pages/FailuresPage'
import { ReportsPage } from './pages/ReportsPage'
import { RequirementsPage } from './pages/RequirementsPage'
import { TestResultsPage } from './pages/TestResultsPage'
import { TraceabilityPage } from './pages/TraceabilityPage'
import { UploadPage } from './pages/UploadPage'
import { VerificationPage } from './pages/VerificationPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <RunProvider>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="upload" element={<UploadPage />} />
                <Route path="requirements" element={<RequirementsPage />} />
                <Route path="verification" element={<VerificationPage />} />
                <Route path="tests" element={<TestResultsPage />} />
                <Route path="failures" element={<FailuresPage />} />
                <Route path="approvals" element={<ApprovalsPage />} />
                <Route path="activity" element={<AgentActivityPage />} />
                <Route path="traceability" element={<TraceabilityPage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </RunProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
