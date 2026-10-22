import React from 'react'
import { Inbox } from 'lucide-react'
import { cn } from '../../lib/utils'

interface EmptyStateProps {
  icon?: typeof Inbox
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-2xl border border-dashed border-[#202F2B] p-10 text-center bg-[#121A18]/80 backdrop-blur-xs shadow-xs',
        className
      )}
    >
      <div className="rounded-xl bg-amber-500/10 p-3.5 text-amber-400 border border-amber-500/25 shadow-xs">
        <Icon className="h-5 w-5" />
      </div>
      <h4 className="mt-3.5 text-[15px] font-bold tracking-tight text-[#F8FAFC]">
        {title}
      </h4>
      {description && (
        <p className="mt-1.5 max-w-md text-[12.5px] font-normal text-[#94A3B8] leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
