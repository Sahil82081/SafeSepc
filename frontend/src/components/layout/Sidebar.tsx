import { useState } from 'react'
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileSpreadsheet,
  FileText,
  LayoutDashboard,
  Network,
  ShieldCheck,
  UploadCloud,
  UserCheck,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { usePendingApprovals } from '../../api/queries'
import { ResetButton } from '../common/ResetButton'

export function Sidebar() {
  const { data: pendingApprovals } = usePendingApprovals()
  const pendingCount = pendingApprovals?.length ?? 0
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Primary simple navigation requested by user
  const primaryNavItems = [
    { name: 'Dashboard', to: '/', icon: LayoutDashboard },
    { name: 'New Verification', to: '/upload', icon: UploadCloud },
    { name: 'Requirements', to: '/requirements', icon: FileText },
    { name: 'Verification', to: '/verification', icon: ShieldCheck },
    { name: 'Reports', to: '/reports', icon: FileSpreadsheet },
  ]

  // Advanced technical modules tucked neatly in secondary area
  const advancedNavItems = [
    { name: 'Test Cases & Simulation', to: '/tests', icon: CheckCircle2 },
    { name: 'Traceability Graph', to: '/traceability', icon: Network },
    { name: 'Defect Diagnosis', to: '/failures', icon: AlertTriangle },
    {
      name: 'Safety Approvals',
      to: '/approvals',
      icon: UserCheck,
      badge: pendingCount > 0 ? String(pendingCount) : undefined,
    },
    { name: 'Agent Audit Trail', to: '/activity', icon: Bot },
  ]

  return (
    <aside className="sticky top-0 flex h-screen w-60 flex-col border-r border-[#202F2B] bg-[#0E1513] p-3 transition-colors">
      {/* Brand Header */}
      <div className="mb-4 flex items-center gap-2.5 px-2.5 py-2.5 border-b border-[#202F2B]">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/25 shadow-xs">
          <ShieldCheck className="h-4.5 w-4.5 text-amber-400" />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-[14px] tracking-tight text-[#F8FAFC]">
            SafeSpec
          </span>
          <span className="text-[11px] text-[#94A3B8] font-normal tracking-tight">
            Safety Verification
          </span>
        </div>
      </div>

      {/* Primary 5-item Nav List */}
      <nav className="flex-1 space-y-1 overflow-y-auto pr-0.5">
        <div className="space-y-1">
          {primaryNavItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `group relative flex items-center justify-between rounded-lg px-3 py-2.5 text-[13px] font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-amber-500/12 text-amber-400 font-semibold border border-amber-500/25 shadow-xs'
                      : 'text-[#94A3B8] hover:bg-[#141D1B] hover:text-[#F8FAFC] border border-transparent'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r-sm bg-amber-400" />
                    )}
                    <div className="flex items-center gap-2.5">
                      <Icon
                        className={`h-4 w-4 transition-colors ${
                          isActive
                            ? 'text-amber-400'
                            : 'text-[#64748B] group-hover:text-[#F8FAFC]'
                        }`}
                      />
                      <span>{item.name}</span>
                    </div>
                  </>
                )}
              </NavLink>
            )
          })}
        </div>

        {/* Secondary Progressive Disclosure: Advanced Details */}
        <div className="pt-4 mt-3 border-t border-[#202F2B]/70">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between px-2 py-1.5 text-[11px] font-semibold text-[#64748B] hover:text-[#94A3B8] transition cursor-pointer"
          >
            <span className="uppercase tracking-wider">Advanced Details</span>
            {showAdvanced ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>

          {showAdvanced && (
            <div className="space-y-1 mt-1 pl-1">
              {advancedNavItems.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `group flex items-center justify-between rounded-lg px-2.5 py-1.5 text-[12px] font-normal transition-all ${
                        isActive
                          ? 'bg-[#182320] text-amber-400 font-medium'
                          : 'text-[#64748B] hover:bg-[#141D1B] hover:text-[#F8FAFC]'
                      }`
                    }
                  >
                    <div className="flex items-center gap-2">
                      <Icon className="h-3.5 w-3.5" />
                      <span>{item.name}</span>
                    </div>
                    {item.badge && (
                      <span className="rounded-full bg-amber-500/20 px-1.5 py-0.2 font-mono text-[9px] font-bold text-amber-400">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                )
              })}
            </div>
          )}
        </div>
      </nav>

      {/* Sidebar Footer: Reset Workspace & Trust Badge */}
      <div className="mt-auto pt-3 space-y-2">
        <ResetButton variant="sidebar" />
        <div className="rounded-lg border border-[#202F2B] bg-[#121A18] p-2 text-center">
          <span className="text-[10.5px] font-medium text-[#94A3B8]">
            ISO 26262 ASIL D Verified
          </span>
        </div>
      </div>
    </aside>
  )
}
