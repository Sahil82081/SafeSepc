import cytoscape from 'cytoscape'
import {
  AlertOctagon,
  ChevronDown,
  ChevronRight,
  Info,
  Loader2,
  Maximize2,
  Network,
  RotateCw,
  UploadCloud,
  X,
  Zap,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useRunDemo, useTraceability } from '../api/queries'
import { PageHeader } from '../components/common/PageHeader'
import { VerificationNav } from '../components/common/VerificationNav'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { ErrorState } from '../components/ui/error-state'
import { Skeleton } from '../components/ui/skeleton'
import { useRunContext } from '../context/RunContext'
import { useTheme } from '../context/ThemeContext'
import type { TraceabilityNode } from '../api/models'

export function TraceabilityPage() {
  const { selectedRunId, setSelectedRunId } = useRunContext()
  const {
    data: traceData,
    isLoading,
    error,
    refetch,
  } = useTraceability(selectedRunId)

  const runDemoMutation = useRunDemo()
  const { theme } = useTheme()
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [selectedNode, setSelectedNode] = useState<TraceabilityNode | null>(null)
  const [showRawJson, setShowRawJson] = useState(false)

  const isDark = theme === 'dark'

  const handleRunDemo = async () => {
    try {
      const res = await runDemoMutation.mutateAsync()
      setSelectedRunId(res.run_id)
    } catch (err) {
      console.error('Failed to run demo:', err)
    }
  }

  useEffect(() => {
    if (!containerRef.current || !traceData || traceData.nodes.length === 0) return

    const elements: cytoscape.ElementDefinition[] = []

    // 1. Convert nodes with clean engineering palette
    traceData.nodes.forEach((n) => {
      let bg = '#00B8D9'
      if (n.type === 'requirement') bg = '#F59E0B'
      else if (n.type === 'rule') bg = '#818CF8'
      else if (n.type === 'conflict') bg = '#EF4444'
      else if (n.type === 'test') bg = '#00B8D9'
      else if (n.type === 'result') {
        bg = n.status === 'PASS' ? '#10B981' : '#EF4444'
      }

      elements.push({
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
          status: n.status,
          metadata: n.metadata,
          bgColor: bg,
        },
      })
    })

    // 2. Convert edges
    traceData.edges.forEach((e, idx) => {
      elements.push({
        data: {
          id: `e-${idx}-${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          label: e.label || e.type || 'links',
        },
      })
    })

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(bgColor)',
            label: 'data(label)',
            color: isDark ? '#F8FAFC' : '#0F172A',
            'font-family': 'Inter, system-ui, sans-serif',
            'font-size': '11px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-margin-y': 7,
            width: 34,
            height: 34,
            'border-width': 2.5,
            'border-color': isDark ? '#141D1B' : '#FFFFFF',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': isDark ? '#2D413C' : '#CBD5E1',
            'target-arrow-color': isDark ? '#64748B' : '#94A3B8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '9.5px',
            'font-family': 'JetBrains Mono, monospace',
            color: isDark ? '#94A3B8' : '#64748B',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
          },
        },
        {
          selector: ':selected',
          style: {
            'border-width': 4,
            'border-color': '#F59E0B',
            'overlay-opacity': 0.15,
            'overlay-color': '#F59E0B',
          },
        },
      ],
      layout: {
        name: 'breadthfirst',
        directed: true,
        padding: 40,
        spacingFactor: 1.6,
      },
    })

    cy.on('tap', 'node', (evt) => {
      const data = evt.target.data()
      setSelectedNode({
        id: data.id,
        label: data.label,
        type: data.type,
        status: data.status,
        metadata: data.metadata,
      })
    })

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null)
      }
    })

    cyRef.current = cy

    return () => {
      cy.destroy()
    }
  }, [traceData, isDark])

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.3)
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.7)
  const handleFit = () => cyRef.current?.fit()

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Traceability DAG"
          subtitle="Requirement-to-code traceability network"
        />
        <ErrorState
          title="Failed to load traceability graph"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const nodesCount = traceData?.nodes?.length ?? 0
  const edgesCount = traceData?.edges?.length ?? 0

  return (
    <div className="space-y-5">
      <PageHeader
        title="Traceability Graph"
        subtitle="Interactive dependency graph linking requirements to formal rules, Z3 proofs, and virtual CAN test outcomes."
        badge={nodesCount > 0 ? `${nodesCount} Nodes / ${edgesCount} Edges` : undefined}
        actions={
          nodesCount > 0 && (
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="icon"
                onClick={handleZoomIn}
                title="Zoom In"
                className="h-8 w-8 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={handleZoomOut}
                title="Zoom Out"
                className="h-8 w-8 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleFit}
                className="gap-1.5 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
              >
                <Maximize2 className="h-3.5 w-3.5 text-amber-400" />
                <span>Fit Graph</span>
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => refetch()}
                title="Reload Graph"
                className="h-8 w-8 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
              >
                <RotateCw className="h-4 w-4" />
              </Button>
            </div>
          )
        }
      />

      <VerificationNav />

      {/* Clean Legend Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#202F2B] bg-[#121A18] px-4 py-2.5 text-xs shadow-xs">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
            <span className="font-medium text-[#F8FAFC]">Requirement</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-indigo-400" />
            <span className="font-medium text-[#94A3B8]">Rule AST</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-400" />
            <span className="font-medium text-cyan-400">CAN Test</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
            <span className="font-medium text-emerald-400">Pass Result</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
            <span className="font-medium text-red-400">Fail / Conflict</span>
          </div>
        </div>

        <span className="text-[11px] text-[#64748B] hidden md:inline">
          Click any node to inspect details in the inspector
        </span>
      </div>

      {/* Main Canvas & Inspector Layout */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-4">
        {/* Cytoscape Canvas Container */}
        <div className="relative h-[620px] overflow-hidden rounded-xl border border-[#202F2B] bg-canvas-grid shadow-inner lg:col-span-3">
          {isLoading ? (
            <div className="flex h-full items-center justify-center p-8">
              <Skeleton className="h-full w-full bg-[#141D1B]" />
            </div>
          ) : !traceData || traceData.nodes.length === 0 ? (
            <div className="flex h-full items-center justify-center p-8">
              <div className="max-w-md text-center p-6 rounded-2xl border border-[#202F2B] bg-[#121A18]/90 backdrop-blur-md shadow-lg">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/25 mb-4 shadow-sm">
                  <Network className="h-6 w-6" />
                </div>
                <h3 className="text-base font-bold text-[#F8FAFC]">
                  Traceability Graph Empty
                </h3>
                <p className="mt-1.5 text-xs text-[#94A3B8] leading-relaxed">
                  Run the verification workflow to link extracted requirements with formal rules, Z3 contradiction proofs, and simulated CAN test outcomes.
                </p>
                <div className="mt-5 flex items-center justify-center gap-3">
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
              </div>
            </div>
          ) : (
            <div ref={containerRef} className="h-full w-full" />
          )}
        </div>

        {/* Node Inspector Panel */}
        <Card className="flex flex-col border-[#202F2B] bg-[#121A18] rounded-xl shadow-sm">
          <CardHeader className="border-b border-[#202F2B] py-3 px-4">
            <CardTitle className="text-xs font-bold uppercase tracking-wider flex items-center justify-between text-[#F8FAFC]">
              <span className="flex items-center gap-2">
                <Info className="h-4 w-4 text-amber-400" />
                <span>Node Inspector</span>
              </span>
              {selectedNode && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSelectedNode(null)}
                  className="h-6 w-6 text-[#64748B] hover:text-[#F8FAFC] hover:bg-[#182320]"
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              )}
            </CardTitle>
          </CardHeader>

          <CardContent className="p-4 flex-1 overflow-y-auto">
            {selectedNode ? (
              <div className="space-y-4 text-xs">
                {/* Node ID & Classification Header */}
                <div className="rounded-lg border border-[#202F2B] bg-[#16221F] p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="capitalize text-[11px] border-[#2D413C] bg-[#121A18] text-[#F8FAFC]">
                      {selectedNode.type}
                    </Badge>
                    {selectedNode.status && (
                      <Badge
                        variant={
                          selectedNode.status === 'PASS'
                            ? 'success'
                            : selectedNode.status === 'FAIL' || selectedNode.status === 'CRITICAL'
                              ? 'destructive'
                              : 'secondary'
                        }
                        className="text-[10.5px]"
                      >
                        {selectedNode.status}
                      </Badge>
                    )}
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#64748B] block font-sans">
                      Node Identifier
                    </span>
                    <span className="font-mono font-bold text-amber-400 text-sm tracking-wide">
                      {selectedNode.id}
                    </span>
                  </div>
                </div>

                {/* Human-Readable Structured Details */}
                {selectedNode.type === 'requirement' && (
                  <div className="space-y-3">
                    {selectedNode.metadata?.asil != null && (
                      <div>
                        <span className="text-[10px] uppercase font-bold text-[#64748B] block mb-1">
                          Safety Integrity Level
                        </span>
                        <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-xs font-bold text-emerald-400">
                          ASIL {String(selectedNode.metadata.asil)}
                        </span>
                      </div>
                    )}
                    {selectedNode.metadata?.text != null && (
                      <div>
                        <span className="text-[10px] uppercase font-bold text-[#64748B] block mb-1">
                          Specification Clause
                        </span>
                        <p className="rounded-lg border border-[#202F2B] bg-[#141D1B] p-3 text-xs text-[#F8FAFC] leading-relaxed">
                          "{String(selectedNode.metadata.text)}"
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {selectedNode.type === 'rule' && (
                  <div className="space-y-3">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-[#64748B] block mb-1">
                        Logical Condition (IF)
                      </span>
                      <div className="rounded-lg border border-[#202F2B] bg-[#141D1B] p-2.5 font-mono text-xs text-amber-400">
                        {String(selectedNode.metadata?.condition || 'Always')}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-[#64748B] block mb-1">
                        Enforced Action (THEN)
                      </span>
                      <div className="rounded-lg border border-[#202F2B] bg-[#141D1B] p-2.5 font-mono text-xs text-cyan-400">
                        {String(selectedNode.metadata?.action || 'Asserted')}
                      </div>
                    </div>
                  </div>
                )}

                {selectedNode.type === 'conflict' && (
                  <div className="space-y-2">
                    <span className="text-[10px] uppercase font-bold text-red-400 flex items-center gap-1.5">
                      <AlertOctagon className="h-3.5 w-3.5" />
                      Z3 Contradiction Counterexample
                    </span>
                    <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 font-mono text-xs text-red-300 leading-relaxed">
                      {String(selectedNode.metadata?.counter_example || 'Mutually unsatisfiable condition space proved by Z3 SMT solver.')}
                    </div>
                  </div>
                )}

                {selectedNode.type === 'test' && (
                  <div className="space-y-2">
                    <span className="text-[10px] uppercase font-bold text-[#64748B] block">
                      Virtual CAN Stimulus
                    </span>
                    <div className="rounded-lg border border-[#202F2B] bg-[#141D1B] p-2.5 font-mono text-xs text-[#94A3B8]">
                      Expected Outcome: <span className="text-[#F8FAFC] font-semibold">{String(selectedNode.metadata?.expected ?? 'N/A')}</span>
                    </div>
                  </div>
                )}

                {selectedNode.type === 'result' && (
                  <div className="space-y-2">
                    <span className="text-[10px] uppercase font-bold text-[#64748B] block">
                      ECU Verification Result
                    </span>
                    <div className="rounded-lg border border-[#202F2B] bg-[#141D1B] p-2.5 font-mono text-xs">
                      Simulation Value: <span className="text-emerald-400 font-bold">{String(selectedNode.metadata?.actual ?? 'Recorded')}</span>
                    </div>
                  </div>
                )}

                {/* Collapsible Technical Metadata */}
                {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
                  <div className="pt-2 border-t border-[#202F2B]">
                    <button
                      type="button"
                      onClick={() => setShowRawJson(!showRawJson)}
                      className="flex items-center gap-1 text-[11px] text-[#64748B] hover:text-[#94A3B8] transition font-sans cursor-pointer"
                    >
                      {showRawJson ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                      <span>{showRawJson ? 'Hide Raw Metadata' : 'View Raw Metadata'}</span>
                    </button>
                    {showRawJson && (
                      <pre className="mt-2 rounded-lg border border-[#202F2B] bg-[#0B100E] p-2.5 text-[10px] font-mono text-[#94A3B8] overflow-x-auto leading-relaxed">
                        {JSON.stringify(selectedNode.metadata, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center text-center p-4">
                <Network className="h-8 w-8 text-[#283B36] mb-3" />
                <h4 className="text-xs font-bold text-[#F8FAFC]">
                  No Node Selected
                </h4>
                <p className="mt-1 text-[11.5px] text-[#64748B] leading-relaxed">
                  Click any node on the graph to inspect its formal AST rule, test inputs, or verification proof.
                </p>
                {nodesCount > 0 && (
                  <div className="mt-4 w-full rounded-lg border border-[#202F2B] bg-[#141D1B] p-2.5 font-mono text-[10.5px] text-[#94A3B8] text-left space-y-1">
                    <div className="flex justify-between">
                      <span>Total Nodes:</span>
                      <span className="font-bold text-[#F8FAFC]">{nodesCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Total Edges:</span>
                      <span className="font-bold text-[#F8FAFC]">{edgesCount}</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
