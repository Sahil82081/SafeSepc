import {
  AlertCircle,
  ArrowRight,
  Beaker,
  CheckCircle2,
  FileText,
  PlusCircle,
  Shield,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import {
  useConflicts,
  useDashboardStats,
  usePendingApprovals,
  useRequirements,
  useResults,
  useRuns,
  useTests,
} from '../api/queries'
import { useRunContext } from '../context/RunContext'

export function DashboardPage() {
  const { selectedRunId, setSelectedRunId } = useRunContext()
  const navigate = useNavigate()

  const { data: runs } = useRuns()
  const { data: stats } = useDashboardStats(selectedRunId)
  const { data: requirements } = useRequirements(selectedRunId)
  const { data: tests } = useTests(selectedRunId)
  const { data: results } = useResults(selectedRunId)
  const { data: conflicts } = useConflicts(selectedRunId)
  const { data: pendingApprovals } = usePendingApprovals()

  const hasActiveRuns = Boolean(runs && runs.length > 0)

  // Real data metrics
  const reqsCount = hasActiveRuns ? (requirements?.length ?? stats?.total_requirements ?? 0) : 0
  const passedCount = hasActiveRuns ? (results ? results.filter((r) => r.passed).length : (stats?.tests_passed ?? 0)) : 0
  const failedCount = hasActiveRuns ? (results ? results.filter((r) => !r.passed).length : (stats?.tests_failed ?? 0)) : 0
  const totalTestsCount = hasActiveRuns ? (tests?.length ?? (passedCount + failedCount)) : 0
  const conflictsCount = hasActiveRuns ? (conflicts?.length ?? 0) : 0
  const pendingApprovalsCount = hasActiveRuns ? (pendingApprovals?.length ?? 0) : 0
  const ambiguousReqs = (requirements || []).filter(
    (r) => r.ambiguity === 'HIGH' || r.ambiguity === 'MEDIUM'
  )

  const isVerified = hasActiveRuns && totalTestsCount > 0 && failedCount === 0 && conflictsCount === 0
  const hasIssues = hasActiveRuns && (failedCount > 0 || conflictsCount > 0 || ambiguousReqs.length > 0 || pendingApprovalsCount > 0)

  // Active requirement text for the current verification
  const currentReqText =
    hasActiveRuns && requirements && requirements.length > 0
      ? requirements[0].text
      : hasActiveRuns
        ? 'Specification loaded. Processing requirements verification.'
        : 'No active specification. Click "+ New Verification" or run the ISO 26262 demo to begin.'

  const currentReqAsil =
    hasActiveRuns && requirements && requirements.length > 0 ? requirements[0].asil : 'STANDBY'

  return (
    <div className="space-y-6 sm:space-y-8 max-w-5xl mx-auto pb-8 sm:pb-12">
      {/* 1. PRODUCT INTRO & PRIMARY ACTION */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 pt-1 sm:pt-2">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#F8FAFC]">
            SafeSpec Verification
          </h1>
          <p className="text-xs sm:text-sm text-[#94A3B8] mt-0.5 sm:mt-1">
            Verify automotive requirements before they reach the vehicle.
          </p>
        </div>

        <Link
          to="/upload"
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 px-4 py-2 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-bold text-slate-950 hover:from-amber-300 hover:to-amber-400 active:scale-[0.98] transition shadow-sm w-full sm:w-fit"
        >
          <PlusCircle className="h-4 w-4" />
          <span>+ New Verification</span>
        </Link>
      </div>

      {/* CURRENT VERIFICATION CARD */}
      <div className="rounded-2xl border border-[#202F2B] bg-[#121A18] p-4 sm:p-6 shadow-sm">
        <div className="flex items-center justify-between gap-2 mb-2 sm:mb-2.5">
          <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-[#64748B]">
            Current Verification
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10.5px] sm:text-[11px] font-semibold text-emerald-400">
            {currentReqAsil} Safety Target
          </span>
        </div>
        <p className="text-sm sm:text-base md:text-lg font-medium text-[#F8FAFC] leading-relaxed">
          "{currentReqText}"
        </p>
      </div>

      {/* 2. SIMPLE 4-STEP VERIFICATION FLOW (Visual Centerpiece) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[#64748B]">
            Verification Progress
          </h2>
          <span className="text-xs text-[#94A3B8]">
            Automated 4-Step Safety Flow
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {/* Step 1: Requirements */}
          <Link
            to="/requirements"
            className="group flex flex-col justify-between rounded-xl border border-[#202F2B] bg-[#121A18] p-4 hover:border-amber-500/40 hover:bg-[#15201D] transition shadow-xs"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-xs font-bold text-amber-400">01</span>
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/25">
                  <FileText className="h-4 w-4" />
                </div>
              </div>
              <h3 className="font-bold text-sm text-[#F8FAFC] group-hover:text-amber-400 transition">
                Requirements
              </h3>
              <p className="text-xs text-[#94A3B8] mt-1">
                Understand the automotive requirement
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#202F2B]/60 flex items-center justify-between">
              <span className="text-[11px] font-medium text-[#64748B]">
                {reqsCount > 0 ? `${reqsCount} Analyzed` : 'Ready'}
              </span>
              <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Complete</span>
              </span>
            </div>
          </Link>

          {/* Step 2: Safety Analysis */}
          <Link
            to="/verification"
            className="group flex flex-col justify-between rounded-xl border border-[#202F2B] bg-[#121A18] p-4 hover:border-cyan-500/40 hover:bg-[#15201D] transition shadow-xs"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-xs font-bold text-cyan-400">02</span>
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/25">
                  <Shield className="h-4 w-4" />
                </div>
              </div>
              <h3 className="font-bold text-sm text-[#F8FAFC] group-hover:text-cyan-400 transition">
                Safety Analysis
              </h3>
              <p className="text-xs text-[#94A3B8] mt-1">
                Find ambiguity and safety risks
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#202F2B]/60 flex items-center justify-between">
              <span className="text-[11px] font-medium text-[#64748B]">
                {conflictsCount > 0 ? `${conflictsCount} Issue(s)` : 'Proved Safe'}
              </span>
              <span className={`flex items-center gap-1 text-[11px] font-semibold ${
                conflictsCount > 0 ? 'text-amber-400' : 'text-emerald-400'
              }`}>
                {conflictsCount > 0 ? <AlertCircle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                <span>{conflictsCount > 0 ? 'Review' : 'Passed'}</span>
              </span>
            </div>
          </Link>

          {/* Step 3: Test & Simulation */}
          <Link
            to="/tests"
            className="group flex flex-col justify-between rounded-xl border border-[#202F2B] bg-[#121A18] p-4 hover:border-indigo-500/40 hover:bg-[#15201D] transition shadow-xs"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-xs font-bold text-indigo-400">03</span>
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/25">
                  <Beaker className="h-4 w-4" />
                </div>
              </div>
              <h3 className="font-bold text-sm text-[#F8FAFC] group-hover:text-indigo-400 transition">
                Test &amp; Simulation
              </h3>
              <p className="text-xs text-[#94A3B8] mt-1">
                Generate and run verification tests
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#202F2B]/60 flex items-center justify-between">
              <span className="text-[11px] font-medium text-[#64748B]">
                {totalTestsCount > 0 ? `${totalTestsCount} Tests` : 'Pending'}
              </span>
              <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Simulated</span>
              </span>
            </div>
          </Link>

          {/* Step 4: Result */}
          <Link
            to="/verification"
            className="group flex flex-col justify-between rounded-xl border border-[#202F2B] bg-[#121A18] p-4 hover:border-emerald-500/40 hover:bg-[#15201D] transition shadow-xs"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-xs font-bold text-emerald-400">04</span>
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
              </div>
              <h3 className="font-bold text-sm text-[#F8FAFC] group-hover:text-emerald-400 transition">
                Result
              </h3>
              <p className="text-xs text-[#94A3B8] mt-1">
                Verify whether the requirement passes
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#202F2B]/60 flex items-center justify-between">
              <span className="text-[11px] font-medium text-[#64748B]">
                {passedCount} / {totalTestsCount} Passed
              </span>
              <span className={`flex items-center gap-1 text-[11px] font-semibold ${
                !hasActiveRuns ? 'text-[#94A3B8]' : isVerified ? 'text-emerald-400' : hasIssues ? 'text-amber-400' : 'text-emerald-400'
              }`}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{!hasActiveRuns ? 'Standby' : isVerified ? 'Verified' : hasIssues ? 'Issues' : 'Verified'}</span>
              </span>
            </div>
          </Link>
        </div>
      </div>

      {/* 3. PROMINENT VERIFICATION RESULT (The Most Important Element) */}
      <div className={`rounded-2xl border p-4 sm:p-6 md:p-8 shadow-md transition-colors ${
        !hasActiveRuns
          ? 'border-[#202F2B] bg-gradient-to-b from-[#141D1B] via-[#121A18] to-[#0E1513]'
          : 'border-emerald-500/30 bg-gradient-to-b from-emerald-500/10 via-[#121A18] to-[#0E1513]'
      }`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 sm:gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className={`text-[11px] sm:text-xs font-bold uppercase tracking-wider ${!hasActiveRuns ? 'text-[#94A3B8]' : 'text-emerald-400'}`}>
                Verification Result
              </span>
            </div>

            <div className="flex items-start sm:items-center gap-3">
              <div className={`flex h-9 w-9 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-full border ${
                !hasActiveRuns
                  ? 'bg-[#182421] text-[#94A3B8] border-[#263632]'
                  : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
              }`}>
                <CheckCircle2 className={`h-5 w-5 sm:h-6 sm:w-6 ${!hasActiveRuns ? 'text-[#94A3B8]' : 'text-emerald-400'}`} />
              </div>
              <div>
                <h2 className="text-xl sm:text-2xl md:text-3xl font-extrabold tracking-tight text-[#F8FAFC]">
                  {!hasActiveRuns
                    ? 'READY TO VERIFY'
                    : isVerified || !hasIssues
                    ? '✓ VERIFIED'
                    : 'ACTION NEEDED'}
                </h2>
                <p className="text-xs sm:text-sm text-[#94A3B8] mt-0.5">
                  {!hasActiveRuns
                    ? 'No verification run active. Upload an automotive specification or click "+ New Verification".'
                    : isVerified || !hasIssues
                    ? 'All generated safety tests passed.'
                    : 'Some safety constraints or test cases require review.'}
                </p>
              </div>
            </div>
          </div>

          <Link
            to={hasActiveRuns ? '/verification' : '/upload'}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/15 px-4 py-2 text-xs font-bold text-emerald-300 hover:bg-emerald-500/25 transition w-full sm:w-fit"
          >
            <span>{hasActiveRuns ? 'View Full Verification' : 'Start Verification'}</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {/* 4 Clear Supporting Facts */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8 pt-6 border-t border-[#202F2B]">
          <div className="space-y-1">
            <span className="text-xs text-[#64748B] block">Requirements Analyzed</span>
            <span className="text-xl sm:text-2xl font-bold font-mono text-[#F8FAFC]">
              {reqsCount}
            </span>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-[#64748B] block">Tests Executed</span>
            <span className="text-xl sm:text-2xl font-bold font-mono text-[#F8FAFC]">
              {totalTestsCount}
            </span>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-[#64748B] block">Tests Passed</span>
            <span className="text-xl sm:text-2xl font-bold font-mono text-emerald-400">
              {passedCount}
            </span>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-[#64748B] block">Critical Issues</span>
            <span className={`text-xl sm:text-2xl font-bold font-mono ${
              failedCount + conflictsCount > 0 ? 'text-amber-400' : 'text-[#F8FAFC]'
            }`}>
              {failedCount + conflictsCount}
            </span>
          </div>
        </div>
      </div>

      {/* 4. ATTENTION / NEXT ACTION CARD */}
      <div className="rounded-2xl border border-[#202F2B] bg-[#121A18] p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className={`mt-0.5 rounded-lg p-2 border ${
              ambiguousReqs.length > 0 || conflictsCount > 0 || failedCount > 0
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/25'
                : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
            }`}>
              {ambiguousReqs.length > 0 || conflictsCount > 0 || failedCount > 0 ? (
                <AlertCircle className="h-5 w-5 text-amber-400" />
              ) : (
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              )}
            </div>

            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-[#64748B] block">
                {hasIssues ? 'Attention Needed' : 'All Clear'}
              </span>
              <p className="text-sm font-semibold text-[#F8FAFC] mt-0.5">
                {ambiguousReqs.length > 0
                  ? `${ambiguousReqs.length} requirement clause needs clarification.`
                  : conflictsCount > 0
                    ? `${conflictsCount} formal contradiction detected.`
                    : failedCount > 0
                      ? `${failedCount} virtual CAN test failed.`
                      : pendingApprovalsCount > 0
                        ? `${pendingApprovalsCount} safety sign-off(s) pending review.`
                        : 'No critical safety issues detected.'}
              </p>
              <p className="text-xs text-[#94A3B8] mt-0.5">
                {hasIssues
                  ? 'Review the findings to ensure ASIL compliance and test fidelity.'
                  : 'All requirements satisfy formal safety rules and simulated vehicle execution.'}
              </p>
            </div>
          </div>

          {hasIssues ? (
            <Link
              to={ambiguousReqs.length > 0 ? '/requirements' : pendingApprovalsCount > 0 ? '/approvals' : '/verification'}
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/15 border border-amber-500/30 px-3.5 py-1.5 text-xs font-bold text-amber-300 hover:bg-amber-500/25 transition w-fit shrink-0"
            >
              <span>Review Issue</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          ) : (
            <Link
              to="/requirements"
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#202F2B] bg-[#141D1B] px-3.5 py-1.5 text-xs font-semibold text-[#F8FAFC] hover:bg-[#1A2623] transition w-fit shrink-0"
            >
              <span>View Requirements</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      </div>

      {/* 5. RECENT VERIFICATIONS */}
      {runs && runs.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#64748B]">
              Recent Verifications
            </h2>
          </div>

          <div className="overflow-hidden rounded-xl border border-[#202F2B] bg-[#121A18] shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#202F2B] bg-[#141D1B] text-[#94A3B8] font-semibold text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Specification</th>
                    <th className="py-3 px-4">Safety Result</th>
                    <th className="py-3 px-4">Tests</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#202F2B]">
                  {runs.slice(0, 5).map((r, idx) => {
                    const isCompleted = r.status === 'completed'
                    const passCount = r.tests_passed || 0
                    const failCount = r.tests_failed || 0
                    const total = passCount + failCount

                    return (
                      <tr key={r.run_id} className="hover:bg-[#16221F] transition">
                        <td className="py-3 px-4 font-medium text-[#F8FAFC]">
                          {`Specification #${idx + 1}`}
                          <span className="block text-[11px] text-[#64748B] font-mono mt-0.5">
                            {r.created_at ? new Date(r.created_at).toLocaleDateString() : 'Today'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {isCompleted ? (
                            failCount === 0 ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-semibold text-emerald-400">
                                <CheckCircle2 className="h-3 w-3" />
                                <span>Verified</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[11px] font-semibold text-amber-400">
                                <AlertCircle className="h-3 w-3" />
                                <span>Review Needed</span>
                              </span>
                            )
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 text-[11px] font-semibold text-cyan-400">
                              <span>In Progress</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-[#94A3B8]">
                          {total > 0 ? `${passCount} / ${total} Passed` : 'Pending'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedRunId(r.run_id)
                              navigate('/verification')
                            }}
                            className="text-xs font-semibold text-amber-400 hover:text-amber-300 transition cursor-pointer"
                          >
                            View →
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
