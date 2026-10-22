import { useState, useEffect } from 'react'
import { CheckCircle2, Loader2, RotateCcw, Trash2, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useResetWorkspace } from '../../api/queries'
import { useRunContext } from '../../context/RunContext'

interface ResetButtonProps {
  variant?: 'nav' | 'sidebar' | 'compact'
  className?: string
}

export function ResetButton({ variant = 'nav', className = '' }: ResetButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showSuccessToast, setShowSuccessToast] = useState(false)
  const { clearRun } = useRunContext()
  const resetMutation = useResetWorkspace()
  const navigate = useNavigate()

  // Handle ESC key to dismiss modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  const handleReset = async () => {
    try {
      await resetMutation.mutateAsync()
      clearRun()
      setIsOpen(false)
      setShowSuccessToast(true)
      navigate('/')
      setTimeout(() => {
        setShowSuccessToast(false)
      }, 4000)
    } catch (err) {
      console.error('Failed to reset workspace:', err)
    }
  }

  return (
    <>
      {/* Trigger Button based on placement variant */}
      {variant === 'nav' ? (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          title="Reset all workspace data"
          aria-label="Reset all workspace data"
          className={`group flex items-center gap-1.5 rounded-lg border border-[#202F2B] bg-[#141D1B] px-2.5 py-1.5 text-xs font-semibold text-[#94A3B8] hover:border-rose-500/40 hover:bg-rose-500/10 hover:text-rose-400 active:scale-[0.98] transition cursor-pointer shadow-xs ${className}`}
        >
          <RotateCcw className="h-3.5 w-3.5 text-[#64748B] group-hover:text-rose-400 group-hover:-rotate-45 transition-transform duration-200" />
          <span className="hidden sm:inline">Reset</span>
        </button>
      ) : variant === 'sidebar' ? (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className={`group w-full flex items-center justify-between rounded-lg border border-[#202F2B] bg-[#121A18] px-2.5 py-2 text-xs font-medium text-[#94A3B8] hover:border-rose-500/40 hover:bg-rose-500/10 hover:text-rose-400 active:scale-[0.98] transition cursor-pointer ${className}`}
        >
          <div className="flex items-center gap-2">
            <RotateCcw className="h-3.5 w-3.5 text-[#64748B] group-hover:text-rose-400 group-hover:-rotate-45 transition-transform duration-200" />
            <span>Reset Data</span>
          </div>
          <span className="text-[10px] uppercase font-mono tracking-wider text-[#64748B] group-hover:text-rose-400/80">Clean</span>
        </button>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          title="Reset Data"
          aria-label="Reset Data"
          className={`flex h-8 w-8 items-center justify-center rounded-lg border border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:border-rose-500/40 hover:bg-rose-500/10 hover:text-rose-400 transition cursor-pointer shadow-xs ${className}`}
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Confirmation Modal Dialog */}
      {isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="reset-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/75 backdrop-blur-xs transition-opacity animate-fade-in"
            onClick={() => !resetMutation.isPending && setIsOpen(false)}
          />

          {/* Modal Card */}
          <div className="relative w-full max-w-md rounded-2xl border border-[#263632] bg-[#101715] p-6 shadow-2xl z-10 animate-scale-in">
            {/* Close Button */}
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              disabled={resetMutation.isPending}
              className="absolute right-4 top-4 rounded-lg p-1 text-[#64748B] hover:bg-[#182421] hover:text-[#F8FAFC] transition cursor-pointer disabled:opacity-50"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Header Icon & Title */}
            <div className="flex items-start gap-3.5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-400 shadow-xs">
                <Trash2 className="h-5 w-5 text-rose-400" />
              </div>
              <div className="space-y-1 pr-6">
                <h3 id="reset-modal-title" className="text-base font-bold text-[#F8FAFC]">
                  Reset Workspace Data
                </h3>
                <p className="text-xs text-[#94A3B8] leading-relaxed">
                  Clean all current verification runs, requirements, test outcomes, and approvals to start with a fresh slate.
                </p>
              </div>
            </div>

            {/* Bullet points of items being deleted */}
            <div className="mt-4 rounded-xl border border-[#202F2B] bg-[#141D1B] p-3 text-xs text-[#A8B5B1] space-y-2">
              <span className="font-semibold text-[11px] text-[#F8FAFC] block">
                The following data will be permanently cleared:
              </span>
              <ul className="space-y-1.5 pl-1 text-[11.5px]">
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0" />
                  <span>All verification runs &amp; specifications</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0" />
                  <span>Extracted requirements &amp; AST formal rules</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0" />
                  <span>Z3 satisfiability proofs &amp; conflict checks</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0" />
                  <span>Virtual ECU simulation results &amp; test cases</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0" />
                  <span>Safety gate human approval records</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0" />
                  <span>Agent reasoning logs &amp; generated reports</span>
                </li>
              </ul>
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                disabled={resetMutation.isPending}
                className="rounded-lg border border-[#202F2B] bg-[#141D1B] px-3.5 py-2 text-xs font-semibold text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC] transition cursor-pointer disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleReset}
                disabled={resetMutation.isPending}
                className="flex items-center gap-2 rounded-lg border border-rose-500/40 bg-gradient-to-r from-rose-600 to-rose-700 px-4 py-2 text-xs font-bold text-white shadow-sm hover:from-rose-500 hover:to-rose-600 active:scale-[0.98] transition cursor-pointer disabled:opacity-50"
              >
                {resetMutation.isPending ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Cleaning Data...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>Clean All Data</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Success Toast */}
      {showSuccessToast && (
        <div className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 rounded-xl border border-emerald-500/30 bg-[#0E1513]/95 px-4 py-3 shadow-xl backdrop-blur-md animate-fade-in text-xs font-medium text-[#F8FAFC]">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div>
            <span className="font-bold block text-emerald-400">Workspace Reset</span>
            <span className="text-[#94A3B8] text-[11px]">All data has been cleaned. Ready for new verification.</span>
          </div>
        </div>
      )}
    </>
  )
}
