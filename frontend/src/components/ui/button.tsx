import React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-1.5 rounded-[8px] text-[13px] font-semibold tracking-tight transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F4C430] disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98] cursor-pointer select-none',
  {
    variants: {
      variant: {
        default:
          'bg-[#F4C430] text-[#0B1110] font-bold hover:bg-[#F8D25B] border border-[#F4C430] shadow-sm',
        accent:
          'bg-[#F4C430] text-[#0B1110] hover:bg-[#F8D25B] font-bold border border-[#FFE17D] shadow-sm',
        secondary:
          'bg-[#182421] text-[#F5F7F6] border border-[#263632] hover:bg-[#1E2D29] hover:border-[#334842] shadow-xs',
        outline:
          'border border-[#263632] bg-transparent text-[#F5F7F6] hover:bg-[#182421] hover:border-[#334842]',
        ghost:
          'text-[#A8B5B1] hover:bg-[#182421] hover:text-[#F5F7F6]',
        destructive:
          'border border-[rgba(255,92,92,0.35)] bg-[rgba(255,92,92,0.12)] text-[#FF5C5C] hover:bg-[rgba(255,92,92,0.22)] shadow-xs',
        success:
          'border border-[rgba(25,201,151,0.35)] bg-[rgba(25,201,151,0.12)] text-[#19C997] hover:bg-[rgba(25,201,151,0.22)] shadow-xs',
      },
      size: {
        default: 'h-8 px-3.5 py-1.5',
        sm: 'h-7 px-2.5 py-1 text-[11.5px]',
        lg: 'h-9 px-4.5 py-2 text-[13.5px]',
        icon: 'h-7 w-7 p-0',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'
