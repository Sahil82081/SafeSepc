import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Network,
  ShieldCheck,
  UserCheck,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { usePendingApprovals } from '../../api/queries'

export function VerificationNav() {
  const { data: pendingApprovals } = usePendingApprovals()
  const pendingCount = pendingApprovals?.length ?? 0

  const tabs = [
    { name: 'Formal Proofs', to: '/verification', icon: ShieldCheck },
    { name: 'Virtual CAN Tests', to: '/tests', icon: CheckCircle2 },
    { name: 'Traceability DAG', to: '/traceability', icon: Network },
    { name: 'Root Cause & Fixes', to: '/failures', icon: AlertTriangle },
    {
      name: 'Safety Approvals',
      to: '/approvals',
      icon: UserCheck,
      badge: pendingCount > 0 ? String(pendingCount) : undefined,
    },
    { name: 'Agent Audit Trail', to: '/activity', icon: Bot },
  ]

  return (
    <div className="flex items-center gap-1.5 overflow-x-auto pb-1 mb-6 border-b border-[#202F2B]">
      {tabs.map((tab) => {
        const Icon = tab.icon
        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === '/verification'}
            className={({ isActive }) =>
              `flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg transition whitespace-nowrap ${
                isActive
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                  : 'text-[#94A3B8] hover:bg-[#141D1B] hover:text-[#F8FAFC]'
              }`
            }
          >
            <Icon className="h-3.5 w-3.5" />
            <span>{tab.name}</span>
            {tab.badge && (
              <span className="rounded-full bg-amber-500/20 text-amber-400 text-[10px] px-1.5 py-0.2 font-mono font-bold">
                {tab.badge}
              </span>
            )}
          </NavLink>
        )
      })}
    </div>
  )
}
