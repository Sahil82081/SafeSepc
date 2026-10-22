import React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-[5px] px-2 py-0.5 text-[11.5px] font-semibold tracking-tight transition-colors focus:outline-none',
  {
    variants: {
      variant: {
        default:
          'bg-[#F4C430] text-[#0B1110] font-bold border border-[#F4C430]',
        secondary:
          'bg-[#182421] text-[#A8B5B1] border border-[#263632]',
        destructive:
          'border border-[rgba(255,92,92,0.35)] bg-[rgba(255,92,92,0.12)] text-[#FF5C5C]',
        success:
          'border border-[rgba(25,201,151,0.35)] bg-[rgba(25,201,151,0.12)] text-[#19C997]',
        warning:
          'border border-[rgba(255,176,32,0.35)] bg-[rgba(255,176,32,0.12)] text-[#FFB020]',
        info:
          'border border-[rgba(0,184,217,0.35)] bg-[rgba(0,184,217,0.12)] text-[#00B8D9]',
        cyan:
          'border border-[rgba(0,184,217,0.35)] bg-[rgba(0,184,217,0.12)] text-[#00B8D9]',
        outline:
          'border border-[#263632] bg-transparent text-[#F5F7F6]',
        accent:
          'border border-[rgba(244,196,48,0.35)] bg-[rgba(244,196,48,0.12)] text-[#F4C430]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}
