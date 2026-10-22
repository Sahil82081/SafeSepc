import React, { useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Loader2,
  RotateCw,
  Search,
  UploadCloud,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useRequirements, useRunDemo } from '../api/queries'
import { PageHeader } from '../components/common/PageHeader'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { ErrorState } from '../components/ui/error-state'
import { Skeleton } from '../components/ui/skeleton'
import { useRunContext } from '../context/RunContext'

export function RequirementsPage() {
  const { selectedRunId, setSelectedRunId } = useRunContext()
  const runDemoMutation = useRunDemo()
  const {
    data: requirements,
    isLoading,
    error,
    refetch,
  } = useRequirements(selectedRunId)

  const handleRunDemo = async () => {
    try {
      const res = await runDemoMutation.mutateAsync()
      setSelectedRunId(res.run_id)
    } catch (err) {
      console.error('Failed to run demo:', err)
    }
  }

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAsil, setSelectedAsil] = useState('ALL')
  const [selectedAmbiguity, setSelectedAmbiguity] = useState('ALL')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  const filteredRequirements = (requirements || []).filter((req) => {
    const matchesSearch =
      req.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      req.text.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesAsil = selectedAsil === 'ALL' || req.asil === selectedAsil

    const matchesAmbiguity =
      selectedAmbiguity === 'ALL' ||
      (req.ambiguity && req.ambiguity.toUpperCase() === selectedAmbiguity)

    return matchesSearch && matchesAsil && matchesAmbiguity
  })

  const getAmbiguityBadge = (level?: string) => {
    const lvl = (level || 'LOW').toUpperCase()
    if (lvl === 'HIGH') {
      return (
        <Badge variant="destructive" className="font-mono text-[10px] gap-1">
          <AlertTriangle className="h-3 w-3" />
          HIGH
        </Badge>
      )
    }
    if (lvl === 'MEDIUM') {
      return (
        <Badge variant="warning" className="font-mono text-[10px] gap-1">
          <AlertTriangle className="h-3 w-3" />
          MEDIUM
        </Badge>
      )
    }
    return (
      <Badge variant="success" className="font-mono text-[10px] gap-1">
        <CheckCircle2 className="h-3 w-3" />
        LOW
      </Badge>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Requirements"
          subtitle="Automotive specification clauses and safety levels."
        />
        <ErrorState
          title="Requirements Parsing Unavailable"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Requirements"
        subtitle="Automotive specification clauses, ASIL safety levels, and quality ambiguity analysis."
        badge={`${requirements?.length ?? 0} Clauses`}
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

      {/* Filter and Search Bar */}
      <div className="rounded-[9px] border border-[#263632] bg-gradient-to-b from-[#162320] to-[#141E1C] p-3 sm:p-3.5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between shadow-xs">
        {/* Search Box */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#71807B]" />
          <input
            type="text"
            placeholder="Filter by ID (e.g. REQ-023) or specification text..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-[7px] border border-[#263632] bg-[#182421] pl-8.5 pr-3 py-1.5 text-xs text-[#F5F7F6] placeholder:text-[#71807B] focus:outline-none focus:ring-1 focus:ring-[#F4C430]"
          />
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 text-xs">
          {/* ASIL Filter */}
          <div className="flex items-center gap-1 flex-wrap">
            <span className="font-bold text-[#71807B] text-[11px] mr-0.5">ASIL:</span>
            {['ALL', 'QM', 'A', 'B', 'C', 'D'].map((lvl) => (
              <button
                key={lvl}
                onClick={() => setSelectedAsil(lvl)}
                className={`rounded-[5px] px-2 py-0.5 font-mono text-[10.5px] font-bold transition cursor-pointer ${
                  selectedAsil === lvl
                    ? 'bg-[#F4C430] text-[#0B1110] shadow-xs'
                    : 'bg-[#182421] text-[#A8B5B1] hover:bg-[#1E2D29] hover:text-[#F5F7F6] border border-[#263632]'
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>

          {/* Ambiguity Filter */}
          <div className="flex items-center gap-1 border-t pt-2 sm:border-t-0 sm:pt-0 sm:border-l sm:pl-3 border-[#263632] flex-wrap">
            <span className="font-bold text-[#71807B] text-[11px] mr-0.5">Ambiguity:</span>
            {['ALL', 'LOW', 'MEDIUM', 'HIGH'].map((amb) => (
              <button
                key={amb}
                onClick={() => setSelectedAmbiguity(amb)}
                className={`rounded-[5px] px-2 py-0.5 font-mono text-[10.5px] font-bold transition cursor-pointer ${
                  selectedAmbiguity === amb
                    ? 'bg-[#F4C430] text-[#0B1110] shadow-xs'
                    : 'bg-[#182421] text-[#A8B5B1] hover:bg-[#1E2D29] hover:text-[#F5F7F6] border border-[#263632]'
                }`}
              >
                {amb}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <Card>
          <CardContent className="p-5 space-y-3">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </CardContent>
        </Card>
      ) : !requirements || requirements.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No Requirements Ingested"
          description="Extract automotive specification clauses, ASIL ratings, and formal AST rules by running a verification cycle."
          action={
            <div className="flex flex-wrap items-center gap-3">
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
      ) : filteredRequirements.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No Requirements Match Query"
          description="Adjust the search term or reset ASIL / Ambiguity filters to display parsed specification clauses."
          action={
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery('')
                setSelectedAsil('ALL')
                setSelectedAmbiguity('ALL')
              }}
            >
              Reset Filters
            </Button>
          }
        />
      ) : (
        <>
          {/* Mobile Card List (md:hidden) */}
          <div className="space-y-3 md:hidden">
            {filteredRequirements.map((req) => {
              const isExpanded = expandedId === req.id
              const hasQualityFinding =
                Boolean(req.ambiguity_reasons && req.ambiguity_reasons.length > 0) ||
                Boolean(req.suggested_refinement)

              return (
                <div
                  key={req.id}
                  onClick={() => toggleExpand(req.id)}
                  className={`rounded-xl border transition p-3.5 space-y-2 cursor-pointer ${
                    isExpanded
                      ? 'border-amber-500/40 bg-[#16221F]'
                      : 'border-[#263632] bg-[#141E1C] hover:border-[#2E423D]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-amber-400 text-xs sm:text-sm">
                      {req.id}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`rounded-[4px] px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                          req.asil === 'D' || req.asil === 'C'
                            ? 'border border-[rgba(255,92,92,0.35)] bg-[rgba(255,92,92,0.12)] text-[#FF5C5C]'
                            : req.asil === 'B' || req.asil === 'A'
                              ? 'border border-[rgba(255,176,32,0.35)] bg-[rgba(255,176,32,0.12)] text-[#FFB020]'
                              : 'border border-[#263632] bg-[#182421] text-[#A8B5B1]'
                        }`}
                      >
                        ASIL {req.asil || 'QM'}
                      </span>
                      {getAmbiguityBadge(req.ambiguity)}
                    </div>
                  </div>

                  <p className="text-xs text-[#F5F7F6] leading-relaxed">
                    "{req.text}"
                  </p>

                  {hasQualityFinding && (
                    <div className="text-[11px] text-[#FFB020] bg-amber-500/10 border border-amber-500/20 rounded-md p-2">
                      <span className="font-semibold block text-[10.5px] uppercase">Quality Finding:</span>
                      <span>{req.ambiguity_reasons?.[0] || req.suggested_refinement}</span>
                    </div>
                  )}

                  {/* Mobile Expanded Drawer */}
                  {isExpanded && (
                    <div className="pt-2 border-t border-[#263632] space-y-2 text-xs">
                      {req.suggested_refinement && (
                        <div className="rounded-md border border-[rgba(25,201,151,0.32)] bg-[rgba(25,201,151,0.12)] p-2 text-[#19C997] text-[11px]">
                          <strong className="block font-mono uppercase text-[10px]">Engineering Suggestion:</strong>
                          <p>{req.suggested_refinement}</p>
                        </div>
                      )}
                      <div className="font-mono text-[10px] text-[#71807B]">
                        Source: Ingested PDF • Classification: ASIL {req.asil || 'QM'}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Desktop Table (hidden md:block) */}
          <div className="hidden md:block overflow-hidden rounded-[9px] border border-[#263632] bg-[#141E1C] shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#263632] bg-[#182421] text-[#A8B5B1] font-bold text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3.5 w-28 font-mono">REQ ID</th>
                    <th className="py-2.5 px-3 w-20">ASIL</th>
                    <th className="py-2.5 px-3.5">Specification Clause Text</th>
                    <th className="py-2.5 px-3 w-28">Ambiguity</th>
                    <th className="py-2.5 px-3.5">Quality Finding &amp; Refinement</th>
                    <th className="py-2.5 px-3 text-right w-16">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#263632]/80">
                  {filteredRequirements.map((req) => {
                    const isExpanded = expandedId === req.id
                    const hasQualityFinding =
                      Boolean(req.ambiguity_reasons && req.ambiguity_reasons.length > 0) ||
                      Boolean(req.suggested_refinement)

                    return (
                      <React.Fragment key={req.id}>
                        <tr
                          className={`transition hover:bg-[#182421] cursor-pointer ${
                            isExpanded ? 'bg-[rgba(244,196,48,0.08)]' : ''
                          }`}
                          onClick={() => toggleExpand(req.id)}
                        >
                          <td className="py-2.5 px-3.5 font-mono font-bold text-[#F4C430]">
                            {req.id}
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`rounded-[4px] px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                                req.asil === 'D' || req.asil === 'C'
                                  ? 'border border-[rgba(255,92,92,0.35)] bg-[rgba(255,92,92,0.12)] text-[#FF5C5C]'
                                  : req.asil === 'B' || req.asil === 'A'
                                    ? 'border border-[rgba(255,176,32,0.35)] bg-[rgba(255,176,32,0.12)] text-[#FFB020]'
                                    : 'border border-[#263632] bg-[#182421] text-[#A8B5B1]'
                              }`}
                            >
                              {req.asil || 'QM'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3.5 text-[#F5F7F6] leading-relaxed max-w-md">
                            {req.text}
                          </td>
                          <td className="py-2.5 px-3">
                            {getAmbiguityBadge(req.ambiguity)}
                          </td>
                          <td className="py-2.5 px-3.5 text-[#A8B5B1]">
                            {hasQualityFinding ? (
                              <div className="flex items-center gap-1.5 text-[#FFB020] text-[11.5px]">
                                <span className="truncate max-w-[280px]">
                                  {req.ambiguity_reasons?.[0] || req.suggested_refinement || 'Ambiguous phrasing detected'}
                                </span>
                              </div>
                            ) : (
                              <span className="text-[#71807B] text-[11px] font-mono">
                                Deterministic Clause
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <button
                              type="button"
                              className="rounded p-1 text-[#71807B] hover:text-[#F5F7F6]"
                            >
                              {isExpanded ? (
                                <ChevronUp className="h-3.5 w-3.5 text-[#F4C430]" />
                              ) : (
                                <ChevronDown className="h-3.5 w-3.5" />
                              )}
                            </button>
                          </td>
                        </tr>

                        {/* Expandable Technical Detail Drawer */}
                        {isExpanded && (
                          <tr className="bg-[#0B1110]">
                            <td colSpan={6} className="p-3.5 pl-10">
                              <div className="rounded-[7px] border border-[#263632] bg-[#182421] p-3.5 space-y-2.5 shadow-2xs">
                                <div className="flex items-center justify-between border-b border-[#263632] pb-2">
                                  <span className="font-mono text-xs font-bold text-[#F4C430]">
                                    {req.id} — ISO 26262 Part 8 Section 6 Inspection Finding
                                  </span>
                                  <span className="font-mono text-[10.5px] text-[#71807B]">
                                    Traceability Hash: {req.id}-FU-SA
                                  </span>
                                </div>

                                {req.ambiguity_reasons && req.ambiguity_reasons.length > 0 && (
                                  <div>
                                    <span className="text-[11.5px] font-semibold text-[#F5F7F6]">
                                      Quality Problem:
                                    </span>
                                    <ul className="mt-0.5 text-xs text-[#FF5C5C] list-disc list-inside space-y-0.5">
                                      {req.ambiguity_reasons.map((r, i) => (
                                        <li key={i}>{r}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {req.suggested_refinement && (
                                  <div className="rounded-[5px] border border-[rgba(25,201,151,0.32)] bg-[rgba(25,201,151,0.12)] p-2.5 text-xs text-[#19C997]">
                                    <strong className="block text-[11px] uppercase tracking-wider font-mono">
                                      Engineering Suggestion:
                                    </strong>
                                    <p className="mt-0.5">{req.suggested_refinement}</p>
                                  </div>
                                )}

                                <div className="flex items-center gap-3 font-mono text-[10.5px] text-[#71807B] pt-0.5">
                                  <span>Source: Ingested PDF Specification</span>
                                  <span>&bull;</span>
                                  <span>Classification: ASIL {req.asil || 'QM'}</span>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
