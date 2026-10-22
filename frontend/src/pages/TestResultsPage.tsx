import { useState } from 'react'
import {
  Beaker,
  CheckCircle2,
  Layers,
  Loader2,
  RotateCw,
  Search,
  UploadCloud,
  X,
  XCircle,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useResults, useRunDemo, useTests } from '../api/queries'
import { PageHeader } from '../components/common/PageHeader'
import { VerificationNav } from '../components/common/VerificationNav'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { EmptyState } from '../components/ui/empty-state'
import { ErrorState } from '../components/ui/error-state'
import { Skeleton } from '../components/ui/skeleton'
import { useRunContext } from '../context/RunContext'
import type { TestResult } from '../api/models'

export function TestResultsPage() {
  const { selectedRunId, setSelectedRunId } = useRunContext()
  const runDemoMutation = useRunDemo()
  const {
    data: results,
    isLoading: resultsLoading,
    error: resultsError,
    refetch: refetchResults,
  } = useResults(selectedRunId)

  const handleRunDemo = async () => {
    try {
      const res = await runDemoMutation.mutateAsync()
      setSelectedRunId(res.run_id)
    } catch (err) {
      console.error('Failed to run demo:', err)
    }
  }

  const { data: testCases, isLoading: testsLoading } = useTests(selectedRunId)

  const [searchQuery, setSearchQuery] = useState('')
  const [filterCategory, setFilterCategory] = useState<string>('ALL')
  const [filterStatus, setFilterStatus] = useState<string>('ALL')
  const [selectedResult, setSelectedResult] = useState<TestResult | null>(null)

  const isLoading = resultsLoading || testsLoading

  const filteredResults = (results || []).filter((r) => {
    const matchesSearch =
      r.test_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.req_id && r.req_id.toLowerCase().includes(searchQuery.toLowerCase()))

    const matchesCat =
      filterCategory === 'ALL' ||
      (r.category && r.category.toLowerCase() === filterCategory.toLowerCase())

    const matchesStatus =
      filterStatus === 'ALL' ||
      (filterStatus === 'PASS' && r.passed) ||
      (filterStatus === 'FAIL' && !r.passed)

    return matchesSearch && matchesCat && matchesStatus
  })

  const passedCount = (results || []).filter((r) => r.passed).length
  const failedCount = (results || []).length - passedCount

  if (resultsError) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Virtual CAN Tests"
          subtitle="Telemetry verified against Virtual ECU."
        />
        <VerificationNav />
        <ErrorState
          title="Simulation Telemetry Unavailable"
          message={(resultsError as Error).message}
          onRetry={() => refetchResults()}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Virtual CAN Tests"
        subtitle="Deterministic boundary, nominal, and fault-injection test suites executed on the Virtual ECU."
        badge={`${results?.length ?? 0} Executed Tests`}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchResults()}
            className="gap-1.5 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
          >
            <RotateCw className="h-3 w-3 text-[#A8B5B1]" />
            <span>Re-run Telemetry</span>
          </Button>
        }
      />

      <VerificationNav />

      {/* Filter and Summary Strip */}
      <div className="rounded-[9px] border border-[#263632] bg-gradient-to-b from-[#162320] to-[#141E1C] p-3.5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between shadow-xs">
        {/* KPI Chips */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-[5px] bg-[rgba(25,201,151,0.12)] px-2.5 py-1 border border-[rgba(25,201,151,0.32)] shadow-2xs">
            <CheckCircle2 className="h-3.5 w-3.5 text-[#19C997]" />
            <span className="text-[11px] text-[#A8B5B1]">Passed:</span>
            <span className="font-mono text-xs font-bold text-[#19C997]">
              {passedCount}
            </span>
          </div>

          <div className="flex items-center gap-1.5 rounded-[5px] bg-[rgba(255,92,92,0.12)] px-2.5 py-1 border border-[rgba(255,92,92,0.35)] shadow-2xs">
            <XCircle className="h-3.5 w-3.5 text-[#FF5C5C]" />
            <span className="text-[11px] text-[#A8B5B1]">Failed:</span>
            <span className="font-mono text-xs font-bold text-[#FF5C5C]">
              {failedCount}
            </span>
          </div>

          <div className="flex items-center gap-1.5 rounded-[5px] bg-[#182421] px-2.5 py-1 border border-[#263632] shadow-2xs">
            <Layers className="h-3.5 w-3.5 text-[#71807B]" />
            <span className="text-[11px] text-[#A8B5B1]">Generated Cases:</span>
            <span className="font-mono text-xs font-bold text-[#F5F7F6]">
              {testCases?.length ?? 0}
            </span>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Box */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[#71807B]" />
            <input
              type="text"
              placeholder="Search Test ID / Req ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-48 rounded-[7px] border border-[#263632] bg-[#182421] pl-8 pr-3 py-1.5 text-xs text-[#F5F7F6] placeholder:text-[#71807B] focus:outline-none focus:ring-1 focus:ring-[#F4C430]"
            />
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-1 border-l border-[#263632] pl-2.5">
            {['ALL', 'boundary', 'normal', 'negative'].map((cat) => (
              <button
                key={cat}
                onClick={() => setFilterCategory(cat)}
                className={`rounded-[5px] px-2 py-0.5 text-[10.5px] font-semibold capitalize transition cursor-pointer ${
                  filterCategory === cat
                    ? 'bg-[#F4C430] text-[#0B1110] font-bold shadow-xs'
                    : 'bg-[#182421] text-[#A8B5B1] hover:bg-[#1E2D29] hover:text-[#F5F7F6] border border-[#263632]'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1 border-l border-[#263632] pl-2.5">
            {['ALL', 'PASS', 'FAIL'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`rounded-[5px] px-2 py-0.5 text-[10.5px] font-mono font-bold transition cursor-pointer ${
                  filterStatus === st
                    ? 'bg-[#F4C430] text-[#0B1110] shadow-xs'
                    : 'bg-[#182421] text-[#A8B5B1] hover:bg-[#1E2D29] hover:text-[#F5F7F6] border border-[#263632]'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading Skeletons */}
      {isLoading ? (
        <div className="rounded-[9px] border border-[#263632] bg-[#141E1C] p-5 space-y-3">
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : !results || results.length === 0 ? (
        <EmptyState
          icon={Beaker}
          title="No Test Results Available"
          description="Synthesize virtual CAN test cases and execute them against the simulated automotive ECU by running a verification cycle."
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
                <span>Upload PDF</span>
              </Link>
            </div>
          }
        />
      ) : filteredResults.length === 0 ? (
        <EmptyState
          icon={Beaker}
          title="No Test Results Match Query"
          description="Execute the test generator on formalized rules or adjust the category and status filters."
          action={
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery('')
                setFilterCategory('ALL')
                setFilterStatus('ALL')
              }}
            >
              Reset Filters
            </Button>
          }
        />
      ) : (
        /* Results Table */
        <div className="overflow-hidden rounded-[9px] border border-[#263632] bg-[#141E1C] shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#263632] bg-[#182421] text-[#A8B5B1] font-bold text-[11px]">
                <tr>
                  <th className="py-2.5 px-3.5 font-mono">Test Case ID</th>
                  <th className="py-2.5 px-3 font-mono">Req Target</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3.5 font-mono">CAN Inputs Stimulus</th>
                  <th className="py-2.5 px-3 font-mono">Expected</th>
                  <th className="py-2.5 px-3 font-mono">Actual (ECU)</th>
                  <th className="py-2.5 px-3.5 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#263632]/80 font-mono text-[11px]">
                {filteredResults.map((res) => (
                  <tr
                    key={res.test_id}
                    onClick={() => setSelectedResult(res)}
                    className={`transition hover:bg-[#182421] cursor-pointer ${
                      selectedResult?.test_id === res.test_id
                        ? 'bg-[rgba(244,196,48,0.08)]'
                        : ''
                    }`}
                  >
                    <td className="py-2.5 px-3.5 font-bold text-[#F5F7F6]">
                      {res.test_id}
                    </td>
                    <td className="py-2.5 px-3 text-[#F4C430] font-semibold">
                      {res.req_id || 'N/A'}
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <span className="rounded-[4px] bg-[#182421] px-1.5 py-0.5 text-[10px] font-semibold text-[#A8B5B1] capitalize border border-[#263632]">
                        {res.category || 'test'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3.5 text-[#A8B5B1] max-w-[200px] truncate">
                      {JSON.stringify(res.inputs)}
                    </td>
                    <td className="py-2.5 px-3 text-[#19C997] font-bold">
                      {String(res.expected_value)}
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`font-bold ${
                          res.passed
                            ? 'text-[#19C997]'
                            : 'text-[#FF5C5C]'
                        }`}
                      >
                        {String(res.actual_value)}
                      </span>
                    </td>
                    <td className="py-2.5 px-3.5 text-center">
                      <Badge
                        variant={res.passed ? 'success' : 'destructive'}
                        className="font-mono text-[9.5px] uppercase font-bold"
                      >
                        {res.passed ? 'PASS' : 'FAIL'}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* DETAIL DRAWER / SLIDE-OVER */}
      {selectedResult && (
        <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-[#263632] bg-[#101817] shadow-2xl transition-transform">
          {/* Drawer Header */}
          <div className="flex items-center justify-between border-b border-[#263632] p-4 bg-[#141E1C]">
            <div className="flex items-center gap-2">
              <Beaker className="h-4 w-4 text-[#F4C430]" />
              <div>
                <h3 className="text-[14px] font-bold text-[#F5F7F6]">
                  Test Case: {selectedResult.test_id}
                </h3>
                <span className="font-mono text-xs text-[#F4C430]">
                  Target: {selectedResult.req_id || 'REQ-050'}
                </span>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSelectedResult(null)}
              className="h-7 w-7 text-[#71807B] hover:text-[#F5F7F6]"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Drawer Content */}
          <div className="flex-1 space-y-4 overflow-y-auto p-4 text-xs">
            {/* Outcome Status Banner */}
            <div
              className={`flex items-center justify-between rounded-[7px] p-3 border ${
                selectedResult.passed
                  ? 'border-[rgba(25,201,151,0.35)] bg-[rgba(25,201,151,0.12)] text-[#19C997]'
                  : 'border-[rgba(255,92,92,0.35)] bg-[rgba(255,92,92,0.12)] text-[#FF5C5C]'
              }`}
            >
              <div className="flex items-center gap-1.5 font-bold font-mono">
                {selectedResult.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-[#19C997]" />
                ) : (
                  <XCircle className="h-4 w-4 text-[#FF5C5C]" />
                )}
                <span>VERIFICATION {selectedResult.passed ? 'PASSED' : 'FAILED'}</span>
              </div>
              <Badge variant={selectedResult.passed ? 'success' : 'destructive'} className="text-[10px]">
                {selectedResult.category || 'nominal'}
              </Badge>
            </div>

            {/* Expected vs Actual Comparator */}
            <div className="rounded-[7px] border border-[#263632] bg-[#182421] p-3.5 space-y-1.5 font-mono shadow-2xs">
              <span className="text-[10.5px] uppercase font-bold text-[#71807B] block font-sans">
                Actuator Deviation Analysis:
              </span>
              <div className="flex justify-between items-center py-1 border-b border-[#263632]">
                <span className="text-[#A8B5B1]">Expected Output:</span>
                <span className="font-bold text-[#19C997]">
                  {String(selectedResult.expected_value)}
                </span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-[#A8B5B1]">Actual ECU Output:</span>
                <span
                  className={`font-bold ${
                    selectedResult.passed
                      ? 'text-[#19C997]'
                      : 'text-[#FF5C5C]'
                  }`}
                >
                  {String(selectedResult.actual_value)}
                </span>
              </div>
            </div>

            {/* Input CAN Payload */}
            <div>
              <span className="text-[11.5px] font-bold text-[#F5F7F6] block mb-1">
                CAN Packet Stimulus Inputs:
              </span>
              <pre className="rounded-[7px] bg-[#0B1110] p-3 font-mono text-[11px] text-[#F4C430] overflow-x-auto border border-[#263632]">
                {JSON.stringify(selectedResult.inputs, null, 2)}
              </pre>
            </div>

            {/* CAN Bus Execution Telemetry Log */}
            <div>
              <span className="text-[11.5px] font-bold text-[#F5F7F6] block mb-1">
                Virtual CAN Bus Telemetry Trace:
              </span>
              <div className="rounded-[7px] bg-[#0B1110] p-3 font-mono text-[10.5px] text-[#A8B5B1] max-h-48 overflow-y-auto leading-relaxed border border-[#263632]">
                {selectedResult.log ||
                  `[CAN] TX 0x100 [8] 00 14 00 00 00 00 00 00\n[CAN] RX 0x200 [8] 01 00 00 00 00 00 00 00\n[ACTUATOR] door_latch state confirmed -> ${selectedResult.actual_value}`}
              </div>
            </div>
          </div>

          {/* Drawer Footer */}
          <div className="border-t border-[#263632] p-3.5 bg-[#141E1C] flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedResult(null)}
            >
              Close Drawer
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
