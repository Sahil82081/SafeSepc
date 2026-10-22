import React from 'react'
import { cn } from '../../lib/utils'

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-[6px] bg-[#1E2D29]',
        className
      )}
      {...props}
    />
  )
}
