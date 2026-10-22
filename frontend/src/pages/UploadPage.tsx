import React, { useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Cpu,
  FileCheck,
  FileText,
  Loader2,
  PauseCircle,
  Shield,
  ShieldAlert,
  UploadCloud,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../api/client'
import { useRun, useStartRun, useUploadRun } from '../api/queries'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { ErrorState } from '../components/ui/error-state'
import { useRunContext } from '../context/RunContext'

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [ecuVersion, setEcuVersion] = useState<string>('v1')
  const [useInterrupt, setUseInterrupt] = useState<boolean>(false)
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false)
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState<boolean>(false)

  const uploadMutation = useUploadRun()
  const startMutation = useStartRun()
  const { setSelectedRunId } = useRunContext()
  const navigate = useNavigate()

  // Track run progress if started
  const { data: runData } = useRun(activeRunId || '', {
    enabled: Boolean(activeRunId),
  })

  const stages = [
    { id: 'uploaded', label: '1. Ingestion', icon: FileText },
    { id: 'extract', label: '2. Requirements Extraction', icon: FileCheck },
    { id: 'formalize', label: '3. Safety Analysis', icon: Shield },
    { id: 'z3', label: '4. Mathematical Proof', icon: CheckCircle2 },
    { id: 'simulate', label: '5. Virtual ECU Simulation', icon: Cpu },
  ]

  const getStageIndex = (stageName?: string, status?: string) => {
    if (!stageName) return 0
    if (status === 'completed' || stageName === 'completed') return stages.length
    const name = stageName.toLowerCase()
    if (name.includes('uploaded')) return 1
    if (name.includes('extract')) return 2
    if (name.includes('formalize')) return 3
    if (name.includes('z3') || name.includes('safety_gate')) return 4
    if (name.includes('simulate') || name.includes('tester') || name.includes('diagnosis')) return 5
    return 1
  }

  const currentStageIndex = getStageIndex(runData?.pipeline_stage, runData?.status)
  const isCompleted = runData?.status === 'completed'
  const isPaused = runData?.status === 'paused'
  const isFailed = runData?.status === 'failed'
  const isRunning =
    runData?.status === 'running' ||
    runData?.status === 'pending' ||
    isUploading ||
    uploadMutation.isPending ||
    startMutation.isPending

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setErrorMsg(null)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
      setErrorMsg(null)
    }
  }

  // Pre-load default sample requirement PDF
  const handleLoadSamplePdf = async () => {
    try {
      setIsUploading(true)
      const blob = await apiClient.getSamplePdfBlob()
      const sampleFile = new File([blob], 'sample_requirements.pdf', {
        type: 'application/pdf',
      })
      setFile(sampleFile)
      setErrorMsg(null)
      setIsUploading(false)
    } catch {
      setIsUploading(false)
      setErrorMsg('Failed to download sample PDF from server. Please verify backend is active.')
    }
  }


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setErrorMsg('Please select or drop an automotive specification PDF file.')
      return
    }

    try {
      setIsUploading(true)
      setErrorMsg(null)

      const uploadRes = await uploadMutation.mutateAsync(file)
      setActiveRunId(uploadRes.run_id)
      setSelectedRunId(uploadRes.run_id)

      await startMutation.mutateAsync({
        id: uploadRes.run_id,
        config: {
          ecu_version: ecuVersion,
          target_req_id: 'REQ-050',
          use_interrupt_for_human: useInterrupt,
        },
      })
      setIsUploading(false)
    } catch (err: unknown) {
      setIsUploading(false)
      setErrorMsg((err as Error).message || 'Failed to start verification pipeline.')
    }
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-[#F8FAFC]">
          New Verification
        </h1>
        <p className="text-sm text-[#94A3B8] mt-1">
          Upload an automotive requirement document to begin automated safety analysis and test execution.
        </p>
      </div>

      {/* Main Upload Card */}
      <Card className="border-[#202F2B] bg-[#121A18] rounded-2xl shadow-sm">
        <CardContent className="p-4 sm:p-6 md:p-8 space-y-5 sm:space-y-6">
          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
            {/* Drag and Drop Box */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-5 sm:p-8 text-center transition ${
                file
                  ? 'border-emerald-500/50 bg-emerald-500/5'
                  : 'border-[#202F2B] bg-[#0E1513] hover:border-amber-500/40 hover:bg-[#141D1B]'
              }`}
            >
              <div className="mb-2.5 sm:mb-3 rounded-xl bg-[#141D1B] p-2.5 sm:p-3 text-amber-400 border border-[#202F2B]">
                {file ? (
                  <FileCheck className="h-6 w-6 sm:h-7 sm:w-7 text-emerald-400" />
                ) : (
                  <UploadCloud className="h-6 w-6 sm:h-7 sm:w-7 text-amber-400" />
                )}
              </div>

              {file ? (
                <div>
                  <p className="font-semibold text-xs sm:text-sm text-[#F8FAFC]">
                    {file.name}
                  </p>
                  <p className="text-[11px] sm:text-xs text-emerald-400 font-mono mt-0.5">
                    {(file.size / 1024).toFixed(1)} KB • Document Selected
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-xs sm:text-sm font-semibold text-[#F8FAFC]">
                    Upload automotive requirement specification
                  </p>
                  <p className="text-[11px] sm:text-xs text-[#64748B]">
                    Accepts ISO 26262 requirements or automotive system specifications PDF
                  </p>
                </div>
              )}

              <div className="mt-3.5 sm:mt-4 flex flex-wrap items-center justify-center gap-2 sm:gap-2.5">
                <label className="cursor-pointer">
                  <span className="inline-flex h-9 items-center justify-center rounded-lg border border-[#202F2B] bg-[#141D1B] px-3.5 py-1.5 text-xs font-semibold text-[#F8FAFC] hover:bg-[#1A2623] active:scale-95 transition">
                    Browse Files
                  </span>
                  <input
                    type="file"
                    accept="application/pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleLoadSamplePdf}
                  className="h-9 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1A2623] text-xs active:scale-95"
                >
                  Use Sample PDF
                </Button>
              </div>
            </div>

            {errorMsg && (
              <ErrorState
                title="Verification Error"
                message={errorMsg}
                onRetry={() => setErrorMsg(null)}
              />
            )}

            {/* Collapsible Progressive Disclosure: Advanced Options */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-1.5 text-xs text-[#64748B] hover:text-[#94A3B8] transition font-medium cursor-pointer"
              >
                {showAdvanced ? (
                  <ChevronDown className="h-3.5 w-3.5" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" />
                )}
                <span>Advanced Options (ECU Firmware &amp; Gate)</span>
              </button>

              {showAdvanced && (
                <div className="mt-3 p-4 rounded-xl border border-[#202F2B] bg-[#0E1513] space-y-4 text-xs">
                  <div>
                    <label className="block text-xs font-semibold text-[#F8FAFC]">
                      Virtual ECU Logic Version:
                    </label>
                    <select
                      value={ecuVersion}
                      onChange={(e) => setEcuVersion(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-[#202F2B] bg-[#141D1B] p-2 text-xs text-[#F8FAFC]"
                    >
                      <option value="v1">v1 (Nominal baseline)</option>
                      <option value="v1_buggy_threshold">v1_buggy_threshold (Injected threshold bug)</option>
                      <option value="v1_buggy_timeout">v1_buggy_timeout (Injected timeout bug)</option>
                    </select>
                  </div>

                  <div className="flex items-start gap-2.5 pt-1">
                    <input
                      type="checkbox"
                      id="interrupt-check"
                      checked={useInterrupt}
                      onChange={(e) => setUseInterrupt(e.target.checked)}
                      className="mt-0.5 h-3.5 w-3.5 rounded border-[#202F2B] accent-amber-500"
                    />
                    <label htmlFor="interrupt-check" className="cursor-pointer text-[#94A3B8]">
                      Enable Human Engineering Gate (pause for engineer sign-off on ASIL C/D changes)
                    </label>
                  </div>
                </div>
              )}
            </div>

            {/* Primary Action Button */}
            <Button
              type="submit"
              disabled={!file || isRunning}
              className="w-full bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 font-bold py-2.5 h-10 hover:from-amber-300 hover:to-amber-400 shadow-sm transition disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  <span>Verification Running in Background...</span>
                </>
              ) : (
                <>
                  <span>Start Safety Verification →</span>
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Live Pipeline Execution Progress */}
      {activeRunId && (
        <Card className="border-[#202F2B] bg-[#121A18] rounded-2xl shadow-sm">
          <CardHeader className="pb-3 border-b border-[#202F2B]">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-bold text-[#F8FAFC]">
                Verification Progress
              </CardTitle>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  isCompleted
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : isPaused
                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                      : isFailed
                        ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                        : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 animate-pulse'
                }`}
              >
                {isCompleted
                  ? '✓ Completed'
                  : isPaused
                    ? '⏸ Awaiting Safety Sign-off'
                    : isFailed
                      ? '✗ Verification Error'
                      : 'Analyzing...'}
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <div className="space-y-2">
              {stages.map((stage, idx) => {
                const Icon = stage.icon
                const isPast = currentStageIndex > idx + 1 || isCompleted
                const isCurrent = currentStageIndex === idx + 1 && !isCompleted

                return (
                  <div
                    key={stage.id}
                    className={`flex items-center justify-between p-2.5 rounded-lg border transition ${
                      isPast
                        ? 'border-emerald-500/30 bg-emerald-500/5 text-[#F8FAFC]'
                        : isCurrent
                          ? isFailed
                            ? 'border-red-500/40 bg-red-500/10 text-red-400 font-semibold'
                            : isPaused
                              ? 'border-amber-500/40 bg-amber-500/10 text-amber-400 font-semibold'
                              : 'border-amber-500/40 bg-amber-500/10 text-amber-400 font-semibold'
                          : 'border-transparent text-[#64748B]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="h-4 w-4" />
                      <span className="text-xs">{stage.label}</span>
                    </div>
                    {isPast && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                    {isCurrent && (
                      <>
                        {isFailed ? (
                          <AlertCircle className="h-4 w-4 text-red-400" />
                        ) : isPaused ? (
                          <PauseCircle className="h-4 w-4 text-amber-400" />
                        ) : (
                          <Loader2 className="h-4 w-4 animate-spin text-amber-400" />
                        )}
                      </>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Human Engineering Gate Paused Callout */}
            {isPaused && (
              <div className="p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 space-y-2.5">
                <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs sm:text-sm">
                  <ShieldAlert className="h-4 w-4 shrink-0" />
                  <span>Human Safety Gate Active (Paused)</span>
                </div>
                <p className="text-xs text-[#CBD5E1]">
                  Verification is held at the engineering safety gate for formal sign-off on ASIL C/D requirements or Z3 detected contradictions.
                </p>
                <Button
                  type="button"
                  onClick={() => navigate('/approvals')}
                  className="bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold py-1.5 px-3.5 text-xs inline-flex items-center gap-1.5"
                >
                  <span>Open Approvals Gate →</span>
                </Button>
              </div>
            )}

            {/* Failure Callout */}
            {isFailed && (
              <div className="p-4 rounded-xl border border-red-500/40 bg-red-500/10 space-y-2.5">
                <div className="flex items-center gap-2 text-red-400 font-semibold text-xs sm:text-sm">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>Pipeline Execution Error</span>
                </div>
                <p className="text-xs text-red-200">
                  Verification pipeline encountered an error during analysis. Check server logs or restart verification.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setActiveRunId(null)
                    setErrorMsg(null)
                  }}
                  className="border-red-500/30 text-red-300 hover:bg-red-500/20 text-xs"
                >
                  <span>Reset &amp; Try Again</span>
                </Button>
              </div>
            )}

            {/* Completion Button */}
            {isCompleted && (
              <Button
                onClick={() => navigate('/verification')}
                className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold py-2 text-xs"
              >
                <span>View Verification Results →</span>
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
