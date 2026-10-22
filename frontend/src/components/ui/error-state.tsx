import { AlertTriangle, RotateCw } from 'lucide-react'
import { cn } from '../../lib/utils'
import { Button } from './button'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({
  title = 'System Error Encountered',
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-[9px] border border-[rgba(255,92,92,0.35)] bg-[rgba(255,92,92,0.08)] p-8 text-center text-[#FF5C5C] shadow-xs',
        className
      )}
    >
      <div className="rounded-lg bg-[rgba(255,92,92,0.18)] p-2.5 text-[#FF5C5C] border border-[rgba(255,92,92,0.3)]">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <h4 className="mt-2 text-[15px] font-bold tracking-tight text-[#FF5C5C]">{title}</h4>
      <p className="mt-1 max-w-md text-[12.5px] font-medium text-[#FF5C5C]/90 leading-relaxed font-mono">
        {message}
      </p>
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          className="mt-3.5 border-[rgba(255,92,92,0.35)] bg-[#141E1C] text-[#FF5C5C] hover:bg-[rgba(255,92,92,0.15)]"
        >
          <RotateCw className="h-3 w-3" />
          <span>Retry Operation</span>
        </Button>
      )}
    </div>
  )
}
