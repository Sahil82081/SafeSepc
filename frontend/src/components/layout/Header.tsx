import {
  ChevronDown,
  Menu,
  Moon,
  PlusCircle,
  Sun,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useRuns } from '../../api/queries'
import { useRunContext } from '../../context/RunContext'
import { useTheme } from '../../context/ThemeContext'
import { ResetButton } from '../common/ResetButton'

interface HeaderProps {
  onToggleMobileMenu?: () => void
}

export function Header({ onToggleMobileMenu }: HeaderProps) {
  const { theme, toggleTheme } = useTheme()
  const { selectedRunId, setSelectedRunId } = useRunContext()
  const { data: runs } = useRuns()

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-[#202F2B] bg-[#0E1513]/95 backdrop-blur-md px-3 sm:px-6 transition-colors">
      {/* Left: Mobile Menu Toggle & Brand Title */}
      <div className="flex items-center gap-2 sm:gap-3">
        {onToggleMobileMenu && (
          <button
            type="button"
            onClick={onToggleMobileMenu}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC] transition md:hidden cursor-pointer"
            aria-label="Toggle navigation drawer"
          >
            <Menu className="h-4.5 w-4.5" />
          </button>
        )}

        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="font-bold text-[14px] tracking-tight text-[#F8FAFC]">
                SafeSpec
              </span>
              <span className="text-[12px] text-[#94A3B8] font-normal hidden sm:inline">
                • Automotive Safety Verification
              </span>
            </div>
            <span className="text-[11px] text-[#64748B] font-normal hidden lg:inline">
              From automotive requirements to verified safety tests.
            </span>
          </div>
        </Link>
      </div>

      {/* Right: Essential Actions */}
      <div className="flex items-center gap-1.5 sm:gap-3">
        {/* Specification Selector (Only displayed if multiple specifications exist) */}
        {runs && runs.length > 1 && (
          <div className="relative flex items-center">
            <select
              id="spec-select"
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="appearance-none rounded-lg border border-[#202F2B] bg-[#141D1B] py-1.5 pl-2.5 pr-7 sm:pl-3 sm:pr-8 text-xs font-medium text-[#F8FAFC] focus:outline-none cursor-pointer max-w-[110px] sm:max-w-xs truncate"
            >
              {runs.map((r, i) => (
                <option key={r.run_id} value={r.run_id} className="bg-[#121A18] text-[#F8FAFC]">
                  {`Spec #${i + 1} (${r.status})`}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 sm:right-2.5 h-3.5 w-3.5 text-[#64748B]" />
          </div>
        )}

        {/* Reset Workspace Data Button in Navigation */}
        <ResetButton variant="nav" />

        {/* Primary Button: + New Verification */}
        <Link
          to="/upload"
          className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-amber-400 to-amber-500 px-2.5 sm:px-3.5 py-1.5 text-xs font-bold text-slate-950 hover:from-amber-300 hover:to-amber-400 active:scale-[0.98] transition shadow-sm cursor-pointer whitespace-nowrap"
        >
          <PlusCircle className="h-3.5 w-3.5 shrink-0" />
          <span className="hidden sm:inline">+ New Verification</span>
          <span className="sm:hidden">+ New</span>
        </Link>

        {/* Theme Toggle Button */}
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC] transition cursor-pointer shadow-xs shrink-0"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4 text-amber-400" />
          ) : (
            <Moon className="h-4 w-4 text-indigo-600" />
          )}
        </button>
      </div>
    </header>
  )
}
