import {
  Bot,
  CheckCircle2,
  Download,
  Filter,
  Wrench,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useAgentEvents } from '../api/queries'
import { PageHeader } from '../components/common/PageHeader'
import { VerificationNav } from '../components/common/VerificationNav'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { ErrorState } from '../components/ui/error-state'
import { useRunContext } from '../context/RunContext'

export function AgentActivityPage() {
  const { selectedRunId } = useRunContext()
  const { events, isConnected, isCompleted, error } = useAgentEvents(selectedRunId)

  const [agentFilter, setAgentFilter] = useState<string>('ALL')
  const [autoScroll, setAutoScroll] = useState<boolean>(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [events, autoScroll])

  const filteredEvents = events.filter((ev) => {
    if (agentFilter === 'ALL') return true
    const name = (ev.agent_name || ev.node || '').toLowerCase()
    return name.includes(agentFilter.toLowerCase())
  })

  const handleExportLog = () => {
    const jsonStr = JSON.stringify(events, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `SafeSpec_Agent_Audit_${selectedRunId || 'stream'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Agent Audit Trail"
        subtitle="Live streaming of Gemini reasoning, tool actions, and execution telemetry."
        badge={`${events.length} Events`}
        actions={
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {isConnected && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Live Stream
              </span>
            )}
            {isCompleted && (
              <span className="flex items-center gap-1.5 text-xs text-[#94A3B8] font-mono">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                Finished
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportLog}
              disabled={events.length === 0}
              className="gap-1.5 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Export<span className="hidden sm:inline"> Audit JSON</span></span>
            </Button>
          </div>
        }
      />

      <VerificationNav />

      {error && (
        <ErrorState
          title="SSE Connection Notification"
          message={error}
        />
      )}

      {/* Filter and Auto-Scroll Toolbar */}
      <Card>
        <CardContent className="p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Agent Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-bold text-[#71807B] mr-1 flex items-center gap-1 text-[11px]">
              <Filter className="h-3 w-3" /> Agent Node:
            </span>
            {['ALL', 'Supervisor', 'Extractor', 'Formalizer', 'Z3', 'Tester', 'Diagnosis'].map(
              (node) => (
                <button
                  key={node}
                  onClick={() => setAgentFilter(node)}
                  className={`rounded-[5px] px-2.5 py-1 text-[11px] font-mono font-semibold transition cursor-pointer ${
                    agentFilter === node
                      ? 'bg-[#F4C430] text-[#0B1110] font-bold shadow-xs'
                      : 'bg-[#182421] text-[#A8B5B1] hover:bg-[#1E2D29] hover:text-[#F5F7F6] border border-[#263632]'
                  }`}
                >
                  {node}
                </button>
              )
            )}
          </div>

          {/* Autoscroll checkbox */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="autoscroll-check"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-[#263632] bg-[#182421] text-[#F4C430] focus:ring-[#F4C430] accent-[#F4C430]"
            />
            <label
              htmlFor="autoscroll-check"
              className="text-[#A8B5B1] cursor-pointer font-medium text-[11px]"
            >
              Auto-scroll to latest
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Real-time Timeline Terminal */}
      <div className="rounded-[9px] border border-[#263632] bg-[#0B1110] p-4 sm:p-5 font-mono shadow-lg">
        {/* Terminal Header */}
        <div className="flex items-center justify-between border-b border-[#263632] pb-3 text-xs text-[#71807B]">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#FF5C5C]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#F4C430]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#19C997]" />
            </div>
            <span className="text-[11px] text-[#A8B5B1]">
              safespec-event-stream://{selectedRunId || 'default'}
            </span>
          </div>
          <span className="text-[11px] text-[#F4C430] font-bold">
            {events.length} Actions Recorded in Audit Log
          </span>
        </div>

        {/* Timeline Events Scroll Area */}
        <div className="mt-4 max-h-[650px] min-h-[350px] space-y-4 overflow-y-auto pr-2 text-xs">
          {events.length === 0 ? (
            <EmptyState
              icon={Bot}
              title="Awaiting Agent Execution Stream"
              description="Start a verification run on the Upload page or select an active run to watch real-time thoughts, tool calls, and results."
              className="border-[#263632] bg-transparent text-[#71807B] my-12"
            />
          ) : (
            filteredEvents.map((ev, index) => (
              <div
                key={index}
                className="relative pl-7 before:absolute before:left-2.5 before:top-3 before:bottom-0 before:w-0.5 before:bg-[#263632] last:before:hidden"
              >
                {/* Node Dot Icon */}
                <div className="absolute left-0 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-[rgba(244,196,48,0.14)] text-[#F4C430] border border-[rgba(244,196,48,0.30)] shadow-2xs">
                  <Bot className="h-3 w-3" />
                </div>

                <div className="rounded-[8px] border border-[#263632] bg-[#141E1C] p-4 transition hover:border-[#334842] shadow-xs">
                  {/* Event Meta Line */}
                  <div className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-2">
                      <span className="rounded-[4px] bg-[rgba(244,196,48,0.14)] border border-[rgba(244,196,48,0.30)] px-2 py-0.5 font-bold text-[#F4C430]">
                        {ev.agent_name || ev.node || 'Supervisor'}
                      </span>
                      <span className="text-[#263632]">&bull;</span>
                      <span className="font-sans text-[#A8B5B1]">
                        Action: <strong className="text-[#F5F7F6]">{ev.action || 'step'}</strong>
                      </span>
                    </div>
                    {ev.timestamp && (
                      <span className="text-[10px] text-[#71807B]">
                        {ev.timestamp}
                      </span>
                    )}
                  </div>

                  {/* 1. Agent Thought Bubble */}
                  {ev.thought && (
                    <div className="mt-2.5 rounded-[7px] border border-[#263632] bg-[#182421] p-3 font-sans text-xs leading-relaxed text-[#F5F7F6]">
                      <span className="font-mono text-[10px] uppercase font-bold text-[#71807B] block mb-1">
                        Agent Reasoning / Thought:
                      </span>
                      {ev.thought}
                    </div>
                  )}

                  {/* 2. Tool Invocation */}
                  {ev.tool_name && (
                    <div className="mt-3 rounded-[7px] border border-[rgba(0,184,217,0.30)] bg-[rgba(0,184,217,0.08)] p-3 text-[11px]">
                      <div className="flex items-center gap-2 font-bold text-[#00B8D9]">
                        <Wrench className="h-3.5 w-3.5" />
                        <span>Tool Call: {ev.tool_name}()</span>
                      </div>
                      {ev.tool_input != null && (
                        <pre className="mt-1.5 overflow-x-auto text-[10.5px] text-[#00B8D9]/90 bg-[#0B1110] p-2.5 rounded-[5px] border border-[rgba(0,184,217,0.25)]">
                          {JSON.stringify(ev.tool_input, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}

                  {/* 3. Tool Result */}
                  {ev.tool_output != null && (
                    <div className="mt-2.5 rounded-[7px] border border-[rgba(25,201,151,0.30)] bg-[rgba(25,201,151,0.08)] p-3 text-[11px]">
                      <div className="flex items-center gap-2 font-bold text-[#19C997]">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Tool Return Result:</span>
                      </div>
                      <pre className="mt-1.5 overflow-x-auto text-[10.5px] text-[#19C997]/90 bg-[#0B1110] p-2.5 rounded-[5px] border border-[rgba(25,201,151,0.25)] max-h-48">
                        {typeof ev.tool_output === 'string'
                          ? ev.tool_output
                          : JSON.stringify(ev.tool_output, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  )
}
