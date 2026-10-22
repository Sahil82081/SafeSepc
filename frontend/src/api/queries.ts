import { useEffect, useState } from 'react'
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query'
import { apiClient } from './client'
import type {
  AgentLogEvent,
  ApprovalActionRequest,
  ApprovalItemResponse,
  Conflict,
  DashboardStatsResponse,
  FixRecord,
  ReportResponse,
  Requirement,
  Rule,
  RunResponse,
  RunStartRequest,
  RunUploadResponse,
  TestCase,
  TestResult,
  TraceabilityGraphResponse,
} from './models'

// Query Keys
export const queryKeys = {
  runs: ['runs'] as const,
  run: (id: string) => ['runs', id] as const,
  requirements: (id: string) => ['runs', id, 'requirements'] as const,
  rules: (id: string) => ['runs', id, 'rules'] as const,
  conflicts: (id: string) => ['runs', id, 'conflicts'] as const,
  tests: (id: string) => ['runs', id, 'tests'] as const,
  results: (id: string) => ['runs', id, 'results'] as const,
  failures: (id: string) => ['runs', id, 'failures'] as const,
  fixes: (id: string) => ['runs', id, 'fixes'] as const,
  traceability: (id: string) => ['runs', id, 'traceability'] as const,
  approvals: ['approvals', 'pending'] as const,
  report: (id: string) => ['runs', id, 'report'] as const,
  dashboardStats: (runId?: string) => ['dashboard', 'stats', runId || 'all'] as const,
}

// 1. Verification Runs Queries
export function useRuns(
  options?: Partial<UseQueryOptions<RunResponse[], Error>>
) {
  return useQuery({
    queryKey: queryKeys.runs,
    queryFn: () => apiClient.getRuns(),
    refetchInterval: 5000,
    ...options,
  })
}

export function useRun(
  id: string,
  options?: Partial<UseQueryOptions<RunResponse, Error>>
) {
  return useQuery({
    queryKey: queryKeys.run(id),
    queryFn: () => apiClient.getRun(id),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' ? 2000 : false
    },
    ...options,
  })
}

// 2. Domain Data Queries
export function useRequirements(
  id: string,
  options?: Partial<UseQueryOptions<Requirement[], Error>>
) {
  return useQuery({
    queryKey: queryKeys.requirements(id),
    queryFn: () => apiClient.getRequirements(id),
    enabled: Boolean(id),
    ...options,
  })
}

export function useRules(
  id: string,
  options?: Partial<UseQueryOptions<Rule[], Error>>
) {
  return useQuery({
    queryKey: queryKeys.rules(id),
    queryFn: () => apiClient.getRules(id),
    enabled: Boolean(id),
    ...options,
  })
}

export function useConflicts(
  id: string,
  options?: Partial<UseQueryOptions<Conflict[], Error>>
) {
  return useQuery({
    queryKey: queryKeys.conflicts(id),
    queryFn: () => apiClient.getConflicts(id),
    enabled: Boolean(id),
    ...options,
  })
}

export function useTests(
  id: string,
  options?: Partial<UseQueryOptions<TestCase[], Error>>
) {
  return useQuery({
    queryKey: queryKeys.tests(id),
    queryFn: () => apiClient.getTests(id),
    enabled: Boolean(id),
    ...options,
  })
}

export function useResults(
  id: string,
  options?: Partial<UseQueryOptions<TestResult[], Error>>
) {
  return useQuery({
    queryKey: queryKeys.results(id),
    queryFn: () => apiClient.getResults(id),
    enabled: Boolean(id),
    ...options,
  })
}

export function useFailures(
  id: string,
  options?: Partial<UseQueryOptions<TestResult[], Error>>
) {
  return useQuery({
    queryKey: queryKeys.failures(id),
    queryFn: () => apiClient.getFailures(id),
    enabled: Boolean(id),
    ...options,
  })
}

export function useFixes(
  id: string,
  options?: Partial<UseQueryOptions<FixRecord[], Error>>
) {
  return useQuery({
    queryKey: queryKeys.fixes(id),
    queryFn: () => apiClient.getFixes(id),
    enabled: Boolean(id),
    ...options,
  })
}

// 3. Traceability Graph Query
export function useTraceability(
  id: string,
  options?: Partial<UseQueryOptions<TraceabilityGraphResponse, Error>>
) {
  return useQuery({
    queryKey: queryKeys.traceability(id),
    queryFn: () => apiClient.getTraceability(id),
    enabled: Boolean(id),
    ...options,
  })
}

// 4. Human Approval Queries & Mutations
export function usePendingApprovals(
  options?: Partial<UseQueryOptions<ApprovalItemResponse[], Error>>
) {
  return useQuery({
    queryKey: queryKeys.approvals,
    queryFn: () => apiClient.getPendingApprovals(),
    refetchInterval: 3000,
    ...options,
  })
}

export function useApproveApproval() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string
      action?: ApprovalActionRequest
    }) => apiClient.approveApproval(id, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.approvals })
      queryClient.invalidateQueries({ queryKey: queryKeys.runs })
    },
  })
}

export function useRejectApproval() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string
      action?: ApprovalActionRequest
    }) => apiClient.rejectApproval(id, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.approvals })
      queryClient.invalidateQueries({ queryKey: queryKeys.runs })
    },
  })
}

// 5. Reports & Dashboard Queries
export function useReport(
  id: string,
  options?: Partial<UseQueryOptions<ReportResponse, Error>>
) {
  return useQuery({
    queryKey: queryKeys.report(id),
    queryFn: () => apiClient.getReport(id),
    enabled: Boolean(id),
    ...options,
  })
}

export function useDashboardStats(
  runId?: string,
  options?: Partial<UseQueryOptions<DashboardStatsResponse, Error>>
) {
  return useQuery({
    queryKey: queryKeys.dashboardStats(runId),
    queryFn: () => apiClient.getDashboardStats(runId),
    refetchInterval: 5000,
    ...options,
  })
}

export function useResetWorkspace() {
  const queryClient = useQueryClient()
  return useMutation<{ status: string; message: string }, Error, void>({
    mutationFn: () => apiClient.resetWorkspace(),
    onSuccess: () => {
      queryClient.clear()
      queryClient.invalidateQueries()
    },
  })
}

// 6. Run Mutations
export function useRunDemo() {
  const queryClient = useQueryClient()
  return useMutation<
    { run_id: string; status: string; message: string },
    Error,
    void
  >({
    mutationFn: () => apiClient.runDemo(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.runs })
      queryClient.invalidateQueries({ queryKey: queryKeys.run(data.run_id) })
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] })
    },
  })
}

export function useUploadRun() {
  const queryClient = useQueryClient()
  return useMutation<RunUploadResponse, Error, File>({
    mutationFn: (file: File) => apiClient.uploadRun(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.runs })
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] })
    },
  })
}

export function useStartRun() {
  const queryClient = useQueryClient()
  return useMutation<
    { run_id: string; status: string; message: string },
    Error,
    { id: string; config?: Partial<RunStartRequest> }
  >({
    mutationFn: ({ id, config }) => apiClient.startRun(id, config),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.run(variables.id) })
      queryClient.invalidateQueries({ queryKey: queryKeys.runs })
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] })
    },
  })
}

// 7. Real-Time SSE Agent Events Hook with Historical Fallback
export function useAgentEvents(runId: string) {
  const [events, setEvents] = useState<AgentLogEvent[]>([])
  const [isConnected, setIsConnected] = useState<boolean>(false)
  const [isCompleted, setIsCompleted] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // 1. Initial load of all historical agent logs from REST endpoint
  useEffect(() => {
    if (!runId) return

    let cancelled = false
    apiClient
      .getRunLogs(runId)
      .then((history) => {
        if (!cancelled && history && history.length > 0) {
          setEvents(history)
        }
      })
      .catch((err) => {
        console.warn('Failed to load initial history logs:', err)
      })

    return () => {
      cancelled = true
    }
  }, [runId])

  // 2. Real-time SSE stream for live agent reasoning
  useEffect(() => {
    if (!runId) return

    setIsCompleted(false)
    setError(null)

    const url = apiClient.getEventsStreamUrl(runId)
    const eventSource = new EventSource(url)

    eventSource.onopen = () => {
      setIsConnected(true)
      setError(null)
    }

    const appendEvent = (data: AgentLogEvent) => {
      setEvents((prev) => {
        if (data.id && prev.some((e) => e.id === data.id)) {
          return prev
        }
        return [...prev, data]
      })
    }

    // W3C SSE listener for custom "agent_action" event name
    const handleAction = (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data)
        appendEvent(payload as AgentLogEvent)
      } catch (err) {
        console.error('Failed to parse agent_action SSE event:', err)
      }
    }

    const handleCompleted = () => {
      setIsCompleted(true)
      eventSource.close()
      setIsConnected(false)
    }

    eventSource.addEventListener('agent_action', handleAction)
    eventSource.addEventListener('run_completed', handleCompleted)

    // Fallback generic onmessage listener
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.event === 'complete' || data.event === 'run_completed') {
          handleCompleted()
          return
        }
        appendEvent(data as AgentLogEvent)
      } catch (err) {
        console.error('Failed to parse generic SSE payload:', err)
      }
    }

    eventSource.onerror = () => {
      setIsConnected(false)
    }

    return () => {
      eventSource.removeEventListener('agent_action', handleAction)
      eventSource.removeEventListener('run_completed', handleCompleted)
      eventSource.close()
      setIsConnected(false)
    }
  }, [runId])

  return { events, isConnected, isCompleted, error }
}
