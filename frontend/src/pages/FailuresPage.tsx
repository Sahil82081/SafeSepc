import {
  Beaker,
  CheckCircle2,
  Flame,
  GitPullRequest,
  RotateCcw,
  RotateCw,
  ShieldCheck,
  Zap,
} from 'lucide-react'
import { useFailures, useFixes } from '../api/queries'
import { PageHeader } from '../components/common/PageHeader'
import { VerificationNav } from '../components/common/VerificationNav'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { ErrorState } from '../components/ui/error-state'
import { Skeleton } from '../components/ui/skeleton'
import { useRunContext } from '../context/RunContext'

export function FailuresPage() {
  const { selectedRunId } = useRunContext()
  const {
    data: failures,
    isLoading: failuresLoading,
    error: failuresError,
    refetch: refetchFailures,
  } = useFailures(selectedRunId)

  const {
    data: fixes,
    isLoading: fixesLoading,
    error: fixesError,
    refetch: refetchFixes,
  } = useFixes(selectedRunId)

  const isLoading = failuresLoading || fixesLoading

  const handleRefresh = () => {
    refetchFailures()
    refetchFixes()
  }

  const currentFix = fixes?.[0] as any
  const experiments = (currentFix?.experiments_conducted || []) as Array<{
    tool: string
    input: Record<string, unknown>
    output: string
  }>
  const patchCode = currentFix?.proposed_code || currentFix?.patch_diff || currentFix?.diff || currentFix?.proposed_text || ''
  const rootCause = currentFix?.root_cause || ''
  const proposedVersion = currentFix?.proposed_version || currentFix?.candidate_version || 'candidate_patch'
  const riskAssessment = currentFix?.risk_assessment || (currentFix?.risk_score !== undefined ? `Risk Score: ${currentFix.risk_score}/100` : 'Assessed')
  const regressionPassed = Boolean(currentFix?.regression_passed)

  if (failuresError || fixesError) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Defect Diagnosis & Fixes"
          subtitle="Root-cause diagnosis and candidate fixes."
        />
        <VerificationNav />
        <ErrorState
          title="Defect Diagnosis Service Unavailable"
          message={
            ((failuresError || fixesError) as Error).message ||
            'Unable to query failure records.'
          }
          onRetry={handleRefresh}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Defect Diagnosis & Fixes"
        subtitle="Automated root-cause analysis, tool hypotheses, and candidate ECU firmware patches."
        badge={`${failures?.length ?? 0} Active Failures`}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            className="gap-1.5 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
          >
            <RotateCw className="h-3 w-3 text-[#A8B5B1]" />
            <span>Refresh Diagnosis</span>
          </Button>
        }
      />

      <VerificationNav />

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-56 w-full" />
          <Skeleton className="h-56 w-full" />
        </div>
      ) : (
        <>
          {/* Section 1: Active Failures Overview */}
          <div className="space-y-3.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Flame className="h-4 w-4 text-[#FF5C5C]" />
                <h3 className="text-[16px] font-bold tracking-tight text-[#F5F7F6]">
                  Simulation Test Failures ({failures?.length ?? 0})
                </h3>
              </div>
              <span className="text-[11.5px] text-[#71807B]">
                Actuator discrepancies detected on Virtual ECU
              </span>
            </div>

            {!failures || failures.length === 0 ? (
              <EmptyState
                icon={CheckCircle2}
                title="Zero Test Failures"
                description="All boundary, normal, and negative test cases passed successfully on the loaded Virtual ECU."
              />
            ) : (
              <div className="grid grid-cols-1 gap-3.5">
                {failures.map((f, i) => (
                  <div
                    key={i}
                    className="rounded-[9px] border border-[rgba(255,92,92,0.35)] bg-[#141E1C] overflow-hidden shadow-xs"
                  >
                    <div className="flex items-center justify-between border-b border-[rgba(255,92,92,0.35)] bg-[rgba(255,92,92,0.12)] px-4 py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-[#FF5C5C]">
                          {f.test_id}
                        </span>
                        <span className="font-mono text-[10.5px] text-[#71807B]">
                          Target: {f.req_id || 'REQ-050'}
                        </span>
                      </div>
                      <Badge variant="destructive" className="font-mono text-[9.5px]">
                        FAIL
                      </Badge>
                    </div>

                    <div className="p-4 space-y-3">
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 font-mono text-xs">
                        <div className="rounded-[7px] border border-[#263632] bg-[#182421] p-3 shadow-2xs">
                          <span className="text-[10.5px] uppercase font-bold text-[#71807B] block font-sans">
                            Stimulus Inputs:
                          </span>
                          <pre className="mt-1 text-[11px] text-[#F5F7F6]">
                            {JSON.stringify(f.inputs, null, 2)}
                          </pre>
                        </div>
                        <div className="rounded-[7px] border border-[#263632] bg-[#182421] p-3 shadow-2xs">
                          <span className="text-[10.5px] uppercase font-bold text-[#71807B] block font-sans">
                            Actuator Deviation:
                          </span>
                          <div className="mt-1.5 space-y-1">
                            <div className="flex justify-between">
                              <span className="text-[#A8B5B1]">Expected:</span>
                              <span className="font-bold text-[#19C997]">
                                {String(f.expected_value)}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-[#A8B5B1]">Actual (ECU):</span>
                              <span className="font-bold text-[#FF5C5C]">
                                {String(f.actual_value)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {f.log && (
                        <div className="rounded-[7px] bg-[#0B1110] p-3 font-mono text-[10.5px] text-[#A8B5B1] border border-[#263632]">
                          <span className="text-[#71807B] font-bold block mb-1">
                            CAN Telemetry Trace:
                          </span>
                          {f.log}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 2: Experiments Tried by Root Cause Agent */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-1.5">
                <Beaker className="h-4 w-4 text-[#F4C430]" />
                <CardTitle>Experimental Isolation &amp; Tool Diagnosis</CardTitle>
              </div>
              <CardDescription>
                Automated experiments executed by Gemini Root Cause Agent to isolate the bug
              </CardDescription>
            </CardHeader>
            <CardContent>
              {experiments.length === 0 ? (
                <EmptyState
                  icon={Beaker}
                  title="No Diagnostic Experiments Conducted"
                  description={
                    failures && failures.length > 0
                      ? 'Root cause diagnosis has not executed experimental tool calls for this run yet.'
                      : 'All simulation tests passed; no diagnostic experiments required.'
                  }
                />
              ) : (
                <div className="space-y-3.5">
                  {experiments.map((exp, idx) => (
                    <div
                      key={idx}
                      className="relative pl-6 before:absolute before:left-2 before:top-2 before:bottom-0 before:w-px before:bg-[#263632] last:before:hidden"
                    >
                      <span className="absolute left-0 top-1.5 flex h-4 w-4 items-center justify-center rounded-[4px] bg-[#182421] font-mono text-[9.5px] font-bold text-[#F4C430] border border-[rgba(244,196,48,0.30)]">
                        {idx + 1}
                      </span>
                      <div className="rounded-[7px] border border-[#263632] bg-[#182421] p-3 text-xs shadow-2xs">
                        <div className="flex items-center justify-between font-mono">
                          <span className="font-bold text-[#F4C430]">
                            Tool: {exp.tool}()
                          </span>
                          <Badge variant="outline" className="text-[9.5px]">
                            Experiment Executed
                          </Badge>
                        </div>

                        <div className="mt-1.5 font-mono text-[11px] text-[#A8B5B1]">
                          <span className="font-bold text-[#71807B]">Input:</span>{' '}
                          {JSON.stringify(exp.input)}
                        </div>

                        <div className="mt-1.5 rounded-[5px] bg-[#141E1C] p-2.5 text-xs text-[#F5F7F6] border border-[#263632]">
                          <strong className="text-[#19C997] block font-mono text-[10px] uppercase">
                            Observation:
                          </strong>
                          {exp.output}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Section 3: Proposed Fix as a Code Diff */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <div className="flex items-center gap-1.5">
                  <GitPullRequest className="h-4 w-4 text-[#19C997]" />
                  <CardTitle>Proposed ECU Patch Candidate</CardTitle>
                </div>
                <CardDescription>
                  Synthesized remediation candidate with plain code Z3 and regression proof
                </CardDescription>
              </div>
              {patchCode && (
                <Badge variant="success" className="font-mono text-xs">
                  {riskAssessment}
                </Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {!patchCode && !rootCause ? (
                <EmptyState
                  icon={GitPullRequest}
                  title="No Remediation Patch Available"
                  description={
                    failures && failures.length > 0
                      ? 'No candidate patch has been synthesized yet for the active failures.'
                      : 'Virtual ECU simulation has zero failures; no code remediation required.'
                  }
                />
              ) : (
                <>
                  {/* Root Cause Summary */}
                  {rootCause && (
                    <div className="rounded-[7px] border border-[rgba(255,176,32,0.35)] bg-[rgba(255,176,32,0.12)] p-3.5 text-xs text-[#F5F7F6] shadow-2xs">
                      <div className="flex items-center gap-1.5 font-bold mb-1 text-[#FFB020]">
                        <Zap className="h-3.5 w-3.5" />
                        <span>Root Cause Identified:</span>
                      </div>
                      <p className="leading-relaxed text-[12.5px] text-[#A8B5B1]">{rootCause}</p>
                    </div>
                  )}

                  {/* Code Diff / Proposed ECU Code Display */}
                  {patchCode && (
                    <div className="rounded-[7px] border border-[#263632] bg-[#0B1110] p-3.5 font-mono text-xs text-[#F5F7F6] overflow-x-auto shadow-inner">
                      <div className="flex items-center justify-between pb-2 border-b border-[#263632] text-[11px] text-[#71807B]">
                        <span className="text-[#19C997] font-bold">
                          Patch Target / Proposed ECU: {proposedVersion}
                        </span>
                        <span className="text-[#F4C430] font-bold">
                          {currentFix?.patch_diff ? 'Unified Diff Patch' : 'Synthesized ECU Python Logic (v2 Candidate)'}
                        </span>
                      </div>
                      <pre className="mt-2.5 leading-relaxed text-[11px] text-[#F5F7F6] whitespace-pre-wrap font-mono">
                        {patchCode}
                      </pre>
                    </div>
                  )}

                  {/* Safety Evaluation & Rollback Guarantee */}
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-[7px] border border-[#263632] bg-[#182421] p-3 text-xs shadow-2xs">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-[#19C997]" />
                      <span className="font-semibold text-[#F5F7F6]">
                        Regression Validation:
                      </span>
                      <span
                        className={
                          regressionPassed
                            ? 'text-[#19C997] font-bold'
                            : 'text-[#FFB020] font-bold'
                        }
                      >
                        {regressionPassed
                          ? 'All Regression Tests Passed on Candidate Patch'
                          : 'Regression Verification In Progress or Pending'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-[#71807B]">
                      <RotateCcw className="h-3.5 w-3.5" />
                      <span className="font-mono text-[10.5px]">
                        Automatic Rollback Enabled
                      </span>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
