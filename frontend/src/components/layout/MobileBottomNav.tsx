import {
  FileText,
  LayoutDashboard,
  Menu,
  PlusCircle,
  ShieldCheck,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { usePendingApprovals } from '../../api/queries'

interface MobileBottomNavProps {
  onOpenMenu: () => void
}

export function MobileBottomNav({ onOpenMenu }: MobileBottomNavProps) {
  const { data: pendingApprovals } = usePendingApprovals()
  const pendingCount = pendingApprovals?.length ?? 0

  return (
    <nav
      aria-label="Mobile Navigation Bar"
      className="fixed bottom-0 left-0 right-0 z-40 flex h-16 items-center justify-around border-t border-[#202F2B] bg-[#0E1513]/95 backdrop-blur-lg px-2 pb-[env(safe-area-inset-bottom,0px)] md:hidden transition-colors"
    >
      {/* 1. Dashboard */}
      <NavLink
        to="/"
        end
        className={({ isActive }) =>
          `flex flex-1 flex-col items-center justify-center py-1 text-center transition-all ${
            isActive
              ? 'text-amber-400 font-bold'
              : 'text-[#94A3B8] hover:text-[#F8FAFC]'
          }`
        }
      >
        {({ isActive }) => (
          <>
            <div className={`p-1 rounded-lg ${isActive ? 'bg-amber-500/15' : ''}`}>
              <LayoutDashboard className="h-4.5 w-4.5" />
            </div>
            <span className="text-[10px] mt-0.5 tracking-tight">Dashboard</span>
          </>
        )}
      </NavLink>

      {/* 2. Requirements */}
      <NavLink
        to="/requirements"
        className={({ isActive }) =>
          `flex flex-1 flex-col items-center justify-center py-1 text-center transition-all ${
            isActive
              ? 'text-amber-400 font-bold'
              : 'text-[#94A3B8] hover:text-[#F8FAFC]'
          }`
        }
      >
        {({ isActive }) => (
          <>
            <div className={`p-1 rounded-lg ${isActive ? 'bg-amber-500/15' : ''}`}>
              <FileText className="h-4.5 w-4.5" />
            </div>
            <span className="text-[10px] mt-0.5 tracking-tight">Specs</span>
          </>
        )}
      </NavLink>

      {/* 3. Center Highlight: + New Verification */}
      <NavLink
        to="/upload"
        className="flex flex-1 flex-col items-center justify-center -mt-3.5 group"
      >
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 shadow-md shadow-amber-500/20 group-active:scale-95 transition-transform">
          <PlusCircle className="h-6 w-6 stroke-[2.2]" />
        </div>
        <span className="text-[10px] font-bold text-amber-400 mt-1">Verify</span>
      </NavLink>

      {/* 4. Verification */}
      <NavLink
        to="/verification"
        className={({ isActive }) =>
          `flex flex-1 flex-col items-center justify-center py-1 text-center transition-all ${
            isActive
              ? 'text-amber-400 font-bold'
              : 'text-[#94A3B8] hover:text-[#F8FAFC]'
          }`
        }
      >
        {({ isActive }) => (
          <>
            <div className={`p-1 rounded-lg ${isActive ? 'bg-amber-500/15' : ''}`}>
              <ShieldCheck className="h-4.5 w-4.5" />
            </div>
            <span className="text-[10px] mt-0.5 tracking-tight">Proof</span>
          </>
        )}
      </NavLink>

      {/* 5. Menu Drawer Trigger */}
      <button
        type="button"
        onClick={onOpenMenu}
        className="relative flex flex-1 flex-col items-center justify-center py-1 text-center text-[#94A3B8] hover:text-[#F8FAFC] active:scale-95 transition cursor-pointer"
        aria-label="Open navigation menu"
      >
        <div className="p-1 relative">
          <Menu className="h-4.5 w-4.5" />
          {pendingCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2 rounded-full bg-amber-400 ring-2 ring-[#0E1513]" />
          )}
        </div>
        <span className="text-[10px] mt-0.5 tracking-tight">Menu</span>
      </button>
    </nav>
  )
}
