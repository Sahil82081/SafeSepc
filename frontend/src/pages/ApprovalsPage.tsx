import { useState } from 'react'
import {
  Check,
  CheckCircle2,
  Clock,
  RotateCw,
  X,
} from 'lucide-react'
import {
  useApproveApproval,
  usePendingApprovals,
  useRejectApproval,
} from '../api/queries'
import { PageHeader } from '../components/common/PageHeader'
import { VerificationNav } from '../components/common/VerificationNav'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { EmptyState } from '../components/ui/empty-state'
import { ErrorState } from '../components/ui/error-state'
import { Skeleton } from '../components/ui/skeleton'

export function ApprovalsPage() {
  const {
    data: pending,
    isLoading,
    error,
    refetch,
  } = usePendingApprovals()

  const approveMutation = useApproveApproval()
  const rejectMutation = useRejectApproval()

  const [notes, setNotes] = useState<Record<string, string>>({})
  const [successBanner, setSuccessBanner] = useState<string | null>(null)

  const handleNoteChange = (id: string, text: string) => {
    setNotes((prev) => ({ ...prev, [id]: text }))
  }

  const handleApprove = async (id: string, reqId: string) => {
    try {
      await approveMutation.mutateAsync({
        id,
        action: {
          note: notes[id] || 'Approved by safety engineer sign-off gate.',
          decided_by: 'lead_safety_engineer',
        },
      })
      setSuccessBanner(`Requirement ${reqId} formalization approved. Resumed verification workflow.`)
      refetch()
    } catch (err: unknown) {
      alert(`Approval action failed: ${(err as Error).message}`)
    }
  }

  const handleReject = async (id: string, reqId: string) => {
    try {
      await rejectMutation.mutateAsync({
        id,
        action: {
          note: notes[id] || 'Rejected by safety engineer sign-off gate.',
          decided_by: 'lead_safety_engineer',
        },
      })
      setSuccessBanner(`Requirement ${reqId} formalization rejected. Blocked downstream execution.`)
      refetch()
    } catch (err: unknown) {
      alert(`Rejection action failed: ${(err as Error).message}`)
    }
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Safety Approvals Gate"
          subtitle="High-risk formalizations requiring functional safety engineer sign-off."
        />
        <VerificationNav />
        <ErrorState
          title="Sign-off Gate Queue Unavailable"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Safety Approvals Gate"
        subtitle="High-risk formalizations and safety-critical changes requiring functional safety review."
        badge={`${pending?.length ?? 0} Pending Approvals`}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="gap-1.5 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
          >
            <RotateCw className="h-3 w-3 text-[#A8B5B1]" />
            <span>Refresh</span>
          </Button>
        }
      />

      <VerificationNav />

      {successBanner && (
        <div className="flex items-center justify-between rounded-[7px] border border-[rgba(25,201,151,0.35)] bg-[rgba(25,201,151,0.12)] p-3 text-xs text-[#19C997] shadow-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-[#19C997] shrink-0" />
            <span className="font-semibold">{successBanner}</span>
          </div>
          <button
            onClick={() => setSuccessBanner(null)}
            className="text-[#19C997] hover:text-[#119771]"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-56 w-full" />
          <Skeleton className="h-56 w-full" />
        </div>
      ) : !pending || pending.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="All Engineering Approvals Clear"
          description="No active formalizations, high-risk patches, or contradictory rules are currently waiting in the safety review queue."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {pending.map((item) => (
            <div
              key={item.id}
              className="rounded-[9px] border border-[#263632] bg-[#141E1C] overflow-hidden shadow-xs"
            >
              {/* Header */}
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-[#263632] bg-[#182421] px-4 py-2.5">
                <div className="flex items-center gap-2.5">
                  <span className="rounded-[4px] bg-[rgba(244,196,48,0.14)] px-2 py-0.5 font-mono text-xs font-bold text-[#F4C430] border border-[rgba(244,196,48,0.30)]">
                    {item.req_id}
                  </span>
                  <div>
                    <h3 className="text-[13.5px] font-bold text-[#F5F7F6]">
                      {item.title}
                    </h3>
                    <span className="font-mono text-[10.5px] text-[#71807B]">
                      Kind: {item.kind} &bull; Sign-off Type: ASIL Safety Gate
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge
                    variant={
                      item.asil_level === 'D' || item.asil_level === 'C'
                        ? 'destructive'
                        : 'secondary'
                    }
                    className="font-mono text-xs"
                  >
                    ASIL {item.asil_level}
                  </Badge>
                  <Badge variant="warning" className="text-xs">
                    <Clock className="h-3 w-3" />
                    Pending Sign-off
                  </Badge>
                </div>
              </div>

              <div className="p-4 space-y-3.5 text-xs">
                {/* 1. Original Text */}
                <div>
                  <span className="text-[10.5px] font-bold uppercase tracking-wider text-[#71807B] block mb-1">
                    Original Natural Language Specification:
                  </span>
                  <div className="rounded-[7px] border border-[#263632] bg-[#182421] p-3 text-[#F5F7F6] leading-relaxed font-sans shadow-2xs">
                    {item.original_text || 'No natural language text provided.'}
                  </div>
                </div>

                {/* 2. Formalized Rule 5 AST */}
                {item.rule && (
                  <div>
                    <span className="text-[10.5px] font-bold uppercase tracking-wider text-[#71807B] block mb-1">
                      Formalized AST Specification (Rule 5 Schema):
                    </span>
                    <pre className="rounded-[7px] border border-[#263632] bg-[#0B1110] p-3 font-mono text-[11px] text-[#F4C430] overflow-x-auto">
                      {JSON.stringify(item.rule, null, 2)}
                    </pre>
                  </div>
                )}

                {/* 3. English Back-Translation */}
                {item.back_translation && (
                  <div>
                    <span className="text-[10.5px] font-bold uppercase tracking-wider text-[#71807B] block mb-1">
                      English Back-Translation (Formal Interpretation):
                    </span>
                    <div className="rounded-[7px] border border-[rgba(25,201,151,0.32)] bg-[rgba(25,201,151,0.10)] p-3 text-[#19C997] leading-relaxed shadow-2xs">
                      <strong className="text-[10.5px] uppercase font-mono block mb-0.5">
                        Synthesized Safety Semantics:
                      </strong>
                      {item.back_translation}
                    </div>
                  </div>
                )}

                {/* Decision Notes Input */}
                <div className="pt-1">
                  <label className="block text-xs font-semibold text-[#F5F7F6]">
                    Lead Safety Engineer Audit Rationale:
                  </label>
                  <input
                    type="text"
                    placeholder="Document ISO 26262 sign-off justification or rejection cause..."
                    value={notes[item.id] || ''}
                    onChange={(e) => handleNoteChange(item.id, e.target.value)}
                    className="mt-1 w-full rounded-[7px] border border-[#263632] bg-[#182421] px-3 py-1.5 text-xs text-[#F5F7F6] focus:outline-none focus:ring-1 focus:ring-[#F4C430] placeholder:text-[#71807B]"
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end gap-2 sm:gap-2.5 pt-2 border-t border-[#263632]">
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={rejectMutation.isPending || approveMutation.isPending}
                    onClick={() => handleReject(item.id, item.req_id)}
                    className="gap-1.5 w-full sm:w-auto justify-center"
                  >
                    <X className="h-3.5 w-3.5" />
                    <span>Reject &amp; Block Rule</span>
                  </Button>

                  <Button
                    variant="success"
                    size="sm"
                    disabled={approveMutation.isPending || rejectMutation.isPending}
                    onClick={() => handleApprove(item.id, item.req_id)}
                    className="gap-1.5 w-full sm:w-auto justify-center"
                  >
                    <Check className="h-3.5 w-3.5 stroke-[2.5]" />
                    <span>Approve &amp; Resume</span>
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
