import React from 'react'

interface PageHeaderProps {
  title: string
  subtitle: string
  badge?: string
  actions?: React.ReactNode
}

export function PageHeader({
  title,
  subtitle,
  badge,
  actions,
}: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-3 pb-4 border-b border-[#202F2B] sm:flex-row sm:items-end sm:justify-between">
      <div className="space-y-1">
        <div className="flex items-center gap-2.5">
          <h2 className="text-[22px] font-bold tracking-tight text-[#F8FAFC] leading-tight">
            {title}
          </h2>
          {badge && (
            <span className="rounded-md border border-[#202F2B] bg-[#141D1B] px-2.5 py-0.5 font-mono text-[11px] font-semibold text-[#94A3B8] shadow-xs">
              {badge}
            </span>
          )}
        </div>
        <p className="text-[13px] font-normal text-[#94A3B8] max-w-3xl leading-relaxed">
          {subtitle}
        </p>
      </div>
      {actions && <div className="flex items-center gap-2 pt-1 sm:pt-0">{actions}</div>}
    </div>
  )
}
