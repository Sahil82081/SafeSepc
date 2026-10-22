import React from 'react'
import { cn } from '../../lib/utils'

export function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-[9px] border border-[#263632] bg-gradient-to-b from-[#162320] to-[#141E1C] text-[#F5F7F6] shadow-[0_4px_20px_-2px_rgba(0,0,0,0.45)] hover:border-[#334842] transition-all duration-200',
        className
      )}
      {...props}
    />
  )
}

export function CardHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex flex-col space-y-1 p-4 sm:p-5 pb-3', className)}
      {...props}
    />
  )
}

export function CardTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn(
        'text-[16px] font-bold tracking-tight text-[#F5F7F6]',
        className
      )}
      {...props}
    />
  )
}

export function CardDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn('text-[12.5px] font-medium text-[#A8B5B1] leading-relaxed', className)}
      {...props}
    />
  )
}

export function CardContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-4 sm:p-5 pt-3', className)} {...props} />
}

export function CardFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex items-center p-4 sm:p-5 pt-0', className)}
      {...props}
    />
  )
}
