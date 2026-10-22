import {
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  FileCode,
  Loader2,
  RotateCw,
  ShieldCheck,
  UploadCloud,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useConflicts, useRules, useRunDemo } from '../api/queries'
import { PageHeader } from '../components/common/PageHeader'
import { VerificationNav } from '../components/common/VerificationNav'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { ErrorState } from '../components/ui/error-state'
import { Skeleton } from '../components/ui/skeleton'
import { useRunContext } from '../context/RunContext'

export function VerificationPage() {
  const { selectedRunId, setSelectedRunId } = useRunContext()
  const runDemoMutation = useRunDemo()
  const {
    data: rules,
    isLoading: rulesLoading,
    error: rulesError,
    refetch: refetchRules,
  } = useRules(selectedRunId)

  const handleRunDemo = async () => {
    try {
      const res = await runDemoMutation.mutateAsync()
      setSelectedRunId(res.run_id)
    } catch (err) {
      console.error('Failed to run demo:', err)
    }
  }

  const {
    data: conflicts,
    isLoading: conflictsLoading,
    error: conflictsError,
    refetch: refetchConflicts,
  } = useConflicts(selectedRunId)

  const isLoading = rulesLoading || conflictsLoading

  // Map rules by ID for quick lookup in side-by-side comparison
  const rulesMap = new Map((rules || []).map((r) => [r.id, r]))

  const handleRefresh = () => {
    refetchRules()
    refetchConflicts()
  }

  if (rulesError || conflictsError) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Safety Verification"
          subtitle="Formal logic proofs and contradiction detection."
        />
        <VerificationNav />
        <ErrorState
          title="Formal Verification Engine Unavailable"
          message={
            ((rulesError || conflictsError) as Error).message ||
            'Unable to communicate with Z3 proof engine.'
          }
          onRetry={handleRefresh}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Safety Verification"
        subtitle="First-order logic satisfiability checking, invariant proofs, and contradiction detection."
        badge={rules ? `${rules.length} Rules Proven` : undefined}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            className="gap-1.5 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
          >
            <RotateCw className="h-3 w-3 text-[#A8B5B1]" />
            <span>Re-verify</span>
          </Button>
        }
      />

      <VerificationNav />

      {/* Invariant Status Banner */}
      <div className="rounded-[9px] border border-[#263632] bg-gradient-to-b from-[#162320] to-[#141E1C] p-4 shadow-xs transition-colors">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-[rgba(0,184,217,0.14)] p-2 text-[#00B8D9] border border-[rgba(0,184,217,0.30)] shrink-0 mt-0.5 shadow-2xs">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-[14px] font-bold text-[#F5F7F6]">
                  Automotive Safety Invariant: INV-SAFE-01
                </h3>
                {!rules || rules.length === 0 ? (
                  <Badge variant="outline" className="text-[10px]">
                    Not verified yet
                  </Badge>
                ) : conflicts && conflicts.length > 0 ? (
                  <Badge variant="destructive" className="text-[10px]">
                    Contradiction Detected ({conflicts.length})
                  </Badge>
                ) : (
                  <Badge variant="success" className="text-[10px]">
                    Invariant Proved Safe
                  </Badge>
                )}
              </div>
              <p className="mt-1 font-mono text-[11.5px] text-[#A8B5B1]">
                {!rules || rules.length === 0 ? (
                  <span>Formula: Ingestion in progress &bull; Z3 Status: Not verified yet</span>
                ) : conflicts && conflicts.length > 0 ? (
                  <span>Formula: <span className="text-[#FF5C5C]">Mutual Satisfiability Space</span> &bull; Z3 Proof: UNSAT (Contradictory Activation Proven)</span>
                ) : (
                  <span>Formula: <span className="text-[#19C997]">Not(speed &gt; 20 &#8743; door != LOCKED)</span> &bull; Z3 Proof: UNSAT (Invariant Holds)</span>
                )}
              </p>
            </div>
          </div>
          <div className="font-mono text-xs text-[#71807B] self-end sm:self-center">
            Rules Evaluated: <strong className="text-[#F5F7F6]">{rules?.length ?? 0}</strong>
          </div>
        </div>
      </div>

      {/* Skeletons while loading */}
      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-44 w-full" />
          <Skeleton className="h-44 w-full" />
        </div>
      ) : (
        <>
          {/* Section 1: Z3 Contradictions with Side-by-Side Comparison */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <AlertOctagon className="h-4 w-4 text-[#FF5C5C]" />
                <h3 className="text-[16px] font-bold tracking-tight text-[#F5F7F6]">
                  Formally Proven Contradictions ({conflicts?.length ?? 0})
                </h3>
              </div>
              <span className="text-[11.5px] text-[#71807B]">
                Mutual activation verified by Microsoft Z3
              </span>
            </div>

            {!rules || rules.length === 0 ? (
              <EmptyState
                icon={ShieldCheck}
                title="No Formal Verification Run Active"
                description="Run the verification cycle to formalize specifications into logic ASTs and prove satisfiability with the Z3 SMT prover."
                action={
                  <div className="flex items-center gap-3">
                    <Button
                      onClick={handleRunDemo}
                      disabled={runDemoMutation.isPending}
                      className="bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 font-bold px-4 py-2 hover:from-amber-300 hover:to-amber-400 shadow-sm"
                    >
                      {runDemoMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                      ) : (
                        <Zap className="h-4 w-4 mr-1.5" />
                      )}
                      <span>{runDemoMutation.isPending ? 'Executing...' : 'Run Quick Demo'}</span>
                    </Button>
                    <Link
                      to="/upload"
                      className="flex items-center gap-1.5 rounded-lg border border-[#202F2B] bg-[#141D1B] px-3.5 py-2 text-xs font-semibold text-[#F8FAFC] hover:bg-[#1A2623] transition"
                    >
                      <UploadCloud className="h-3.5 w-3.5 text-[#94A3B8]" />
                      <span>Upload Spec</span>
                    </Link>
                  </div>
                }
              />
            ) : !conflicts || conflicts.length === 0 ? (
              <EmptyState
                icon={CheckCircle2}
                title="Zero Formal Contradictions"
                description="Z3 SMT solver completed mutual satisfiability proofs across all approved rules. No conflicting activation spaces exist."
              />
            ) : (
              <div className="space-y-4">
                {conflicts.map((conf, index) => {
                  const ruleA = rulesMap.get(conf.rule_a_id)
                  const ruleB = rulesMap.get(conf.rule_b_id)

                  return (
                    <div
                      key={index}
                      className="rounded-[9px] border border-[rgba(255,92,92,0.35)] bg-[#141E1C] overflow-hidden shadow-xs"
                    >
                      {/* Contradiction Top Banner */}
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-[rgba(255,92,92,0.35)] bg-[rgba(255,92,92,0.12)] px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <AlertOctagon className="h-4 w-4 text-[#FF5C5C] shrink-0" />
                          <span className="font-mono font-bold text-xs text-[#FF5C5C]">
                            Contradiction: {conf.rule_a_id} vs {conf.rule_b_id}
                          </span>
                        </div>
                        <Badge variant="destructive" className="font-mono text-[10px]">
                          Z3 SATISFIABILITY: UNSAT
                        </Badge>
                      </div>

                      <div className="p-4 space-y-3.5">
                        {/* Conflict Explanation */}
                        <div className="text-[13px] text-[#F5F7F6]">
                          <strong className="text-[#FF5C5C]">
                            Formal Proof Diagnosis:
                          </strong>{' '}
                          {conf.reason}
                        </div>

                        {/* SIDE-BY-SIDE RULES COMPARISON */}
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                          {/* Rule A */}
                          <div className="rounded-[7px] border border-[#263632] bg-[#182421] p-3.5 shadow-2xs">
                            <div className="flex items-center justify-between border-b border-[#263632] pb-1.5">
                              <span className="font-mono text-xs font-bold text-[#F4C430]">
                                Rule A: {conf.rule_a_id}
                              </span>
                              <Badge variant="outline" className="text-[9.5px]">
                                Base Rule
                              </Badge>
                            </div>

                            <p className="mt-2 text-[12.5px] text-[#F5F7F6] min-h-[32px]">
                              {ruleA?.text || `Requirement ${conf.rule_a_id}`}
                            </p>

                            {ruleA?.condition && ruleA?.action ? (
                              <div className="mt-2.5 space-y-1 font-mono text-[11px] rounded-[5px] bg-[#141E1C] p-2.5 border border-[#263632]">
                                <div className="text-[#F5F7F6]">
                                  <span className="text-[#71807B] font-bold">IF:</span>{' '}
                                  {ruleA.condition.var}{' '}
                                  <span className="text-[#F4C430] font-bold">
                                    {ruleA.condition.op}
                                  </span>{' '}
                                  {String(ruleA.condition.value)}
                                </div>
                                <div className="text-[#F5F7F6]">
                                  <span className="text-[#71807B] font-bold">THEN:</span>{' '}
                                  {ruleA.action.var}{' '}
                                  <span className="text-[#F4C430] font-bold">
                                    {ruleA.action.op}
                                  </span>{' '}
                                  <span className="font-bold text-[#FF5C5C]">
                                    {String(ruleA.action.value)}
                                  </span>
                                </div>
                              </div>
                            ) : null}
                          </div>

                          {/* Rule B */}
                          <div className="rounded-[7px] border border-[rgba(255,92,92,0.35)] bg-[rgba(255,92,92,0.06)] p-3.5 shadow-2xs">
                            <div className="flex items-center justify-between border-b border-[rgba(255,92,92,0.35)] pb-1.5">
                              <span className="font-mono text-xs font-bold text-[#FF5C5C]">
                                Rule B: {conf.rule_b_id}
                              </span>
                              <Badge variant="destructive" className="text-[9.5px]">
                                Contradictory Action
                              </Badge>
                            </div>

                            <p className="mt-2 text-[12.5px] text-[#F5F7F6] min-h-[32px]">
                              {ruleB?.text || `Requirement ${conf.rule_b_id}`}
                            </p>

                            {ruleB?.condition && ruleB?.action ? (
                              <div className="mt-2.5 space-y-1 font-mono text-[11px] rounded-[5px] bg-[#141E1C] p-2.5 border border-[#263632]">
                                <div className="text-[#F5F7F6]">
                                  <span className="text-[#71807B] font-bold">IF:</span>{' '}
                                  {ruleB.condition.var}{' '}
                                  <span className="text-[#F4C430] font-bold">
                                    {ruleB.condition.op}
                                  </span>{' '}
                                  {String(ruleB.condition.value)}
                                </div>
                                <div className="text-[#F5F7F6]">
                                  <span className="text-[#71807B] font-bold">THEN:</span>{' '}
                                  {ruleB.action.var}{' '}
                                  <span className="text-[#F4C430] font-bold">
                                    {ruleB.action.op}
                                  </span>{' '}
                                  <span className="font-bold text-[#FF5C5C]">
                                    {String(ruleB.action.value)}
                                  </span>
                                </div>
                              </div>
                            ) : null}
                          </div>
                        </div>

                        {/* Concrete Z3 Counter-Example State */}
                        {conf.counter_example && (
                          <div className="rounded-[7px] border border-[#263632] bg-[#0B1110] p-3 font-mono text-xs text-[#F5F7F6]">
                            <div className="flex items-center gap-1.5 text-[#F4C430] font-bold pb-1.5 border-b border-[#263632]">
                              <Zap className="h-3.5 w-3.5" />
                              <span className="text-[11.5px]">Z3 Mathematical Counter-Example (Activation Overlap):</span>
                            </div>
                            <pre className="mt-2 text-[11px] text-[#F4C430] overflow-x-auto leading-relaxed">
                              {JSON.stringify(conf.counter_example, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Section 2: Formalized Rule 5 Specifications */}
          <div className="space-y-4 pt-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <FileCode className="h-4 w-4 text-[#F4C430]" />
                <h3 className="text-[16px] font-bold tracking-tight text-[#F5F7F6]">
                  Formalized Rule 5 AST Schema ({rules?.length ?? 0})
                </h3>
              </div>
              <span className="text-[11.5px] text-[#71807B]">
                Checkable first-order AST with English back-translation
              </span>
            </div>

            {!rules || rules.length === 0 ? (
              <EmptyState
                icon={FileCode}
                title="No Formalized Rules"
                description="Run the formalizer agent on your extracted requirements to generate Rule 5 AST objects."
              />
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {rules.map((rule) => (
                  <Card key={rule.id}>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-[#F4C430]">
                          {rule.id}
                        </span>
                        {rule.not_formalizable ? (
                          <Badge variant="destructive" className="text-[9.5px]">
                            Not Formalizable
                          </Badge>
                        ) : (
                          <Badge variant="success" className="text-[9.5px]">
                            Formalized AST
                          </Badge>
                        )}
                      </div>
                      <span className="font-mono text-[10.5px] text-[#71807B]">
                        AST Rule Node
                      </span>
                    </CardHeader>
                    <CardContent className="space-y-2.5">
                      <p className="text-[13px] text-[#F5F7F6]">
                        {rule.text}
                      </p>

                      {rule.back_translation && (
                        <div className="rounded-[7px] border border-[#263632] bg-[#182421] p-3 text-[12.5px] text-[#A8B5B1]">
                          <strong className="text-[#F5F7F6] block text-[11.5px] mb-0.5">
                            English Back-Translation:
                          </strong>
                          {rule.back_translation}
                        </div>
                      )}

                      {rule.condition && rule.action && (
                        <div className="flex flex-wrap items-center gap-2 font-mono text-[11.5px]">
                          <div className="rounded-[5px] border border-[#263632] bg-[#182421] px-2.5 py-1 text-[#F5F7F6]">
                            <span className="text-[#71807B]">IF:</span> {rule.condition.var}{' '}
                            <span className="text-[#F4C430] font-bold">
                              {rule.condition.op}
                            </span>{' '}
                            {String(rule.condition.value)}
                          </div>
                          <ArrowRight className="h-3 w-3 text-[#71807B]" />
                          <div className="rounded-[5px] border border-[#263632] bg-[#182421] px-2.5 py-1 text-[#F5F7F6]">
                            <span className="text-[#71807B]">THEN:</span> {rule.action.var}{' '}
                            <span className="text-[#F4C430] font-bold">
                              {rule.action.op}
                            </span>{' '}
                            {String(rule.action.value)}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
