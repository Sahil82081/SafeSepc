import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

export function AppLayout() {
  return (
    <div className="flex min-h-screen bg-[#0B100E] text-[#F8FAFC] transition-colors">
      {/* Left fixed rail sidebar */}
      <Sidebar />

      {/* Main working column */}
      <div className="flex flex-1 flex-col overflow-x-hidden min-w-0">
        <Header />
        <main className="flex-1 p-5 md:p-6 lg:p-7">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
