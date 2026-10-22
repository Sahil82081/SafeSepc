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

export const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, '') ||
  'http://localhost:8000'

class ApiError extends Error {
  status: number
  detail?: unknown

  constructor(message: string, status: number, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`
  const headers = new Headers(options.headers || {})

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errorDetail: unknown = null
    try {
      errorDetail = await response.json()
    } catch {
      errorDetail = await response.text()
    }
    const message =
      (typeof errorDetail === 'object' &&
        errorDetail !== null &&
        'detail' in errorDetail &&
        typeof (errorDetail as { detail: unknown }).detail === 'string' &&
        (errorDetail as { detail: string }).detail) ||
      `Request failed with status ${response.status}: ${response.statusText}`
    throw new ApiError(message, response.status, errorDetail)
  }

  // Handle empty or 204 responses
  if (response.status === 204) {
    return {} as T
  }

  return response.json() as Promise<T>
}

export const apiClient = {
  // 1. Verification Runs
  async runDemo(): Promise<{ run_id: string; status: string; message: string }> {
    return request<{ run_id: string; status: string; message: string }>('/runs/demo', {
      method: 'POST',
    })
  },

  async uploadRun(file: File): Promise<RunUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    return request<RunUploadResponse>('/runs/upload', {
      method: 'POST',
      body: formData,
    })
  },

  async startRun(
    id: string,
    config?: Partial<RunStartRequest>
  ): Promise<{ run_id: string; status: string; message: string }> {
    return request<{ run_id: string; status: string; message: string }>(
      `/runs/${id}/start`,
      {
        method: 'POST',
        body: JSON.stringify(config || {}),
      }
    )
  },

  async getRuns(): Promise<RunResponse[]> {
    return request<RunResponse[]>('/runs')
  },

  async getRun(id: string): Promise<RunResponse> {
    return request<RunResponse>(`/runs/${id}`)
  },

  // 2. Domain Data
  async getRequirements(id: string): Promise<Requirement[]> {
    return request<Requirement[]>(`/runs/${id}/requirements`)
  },

  async getRules(id: string): Promise<Rule[]> {
    return request<Rule[]>(`/runs/${id}/rules`)
  },

  async getConflicts(id: string): Promise<Conflict[]> {
    return request<Conflict[]>(`/runs/${id}/conflicts`)
  },

  async getTests(id: string): Promise<TestCase[]> {
    return request<TestCase[]>(`/runs/${id}/tests`)
  },

  async getResults(id: string): Promise<TestResult[]> {
    return request<TestResult[]>(`/runs/${id}/results`)
  },

  async getFailures(id: string): Promise<TestResult[]> {
    return request<TestResult[]>(`/runs/${id}/failures`)
  },

  async getFixes(id: string): Promise<FixRecord[]> {
    return request<FixRecord[]>(`/runs/${id}/fixes`)
  },

  // 3. Traceability
  async getTraceability(id: string): Promise<TraceabilityGraphResponse> {
    return request<TraceabilityGraphResponse>(`/runs/${id}/traceability`)
  },

  // 4. Human Approval Gate
  async getPendingApprovals(): Promise<ApprovalItemResponse[]> {
    return request<ApprovalItemResponse[]>('/approvals/pending')
  },

  async approveApproval(
    id: string,
    action?: ApprovalActionRequest
  ): Promise<{ id: string; status: string; message: string }> {
    return request<{ id: string; status: string; message: string }>(
      `/approvals/${id}/approve`,
      {
        method: 'POST',
        body: JSON.stringify(action || {}),
      }
    )
  },

  async rejectApproval(
    id: string,
    action?: ApprovalActionRequest
  ): Promise<{ id: string; status: string; message: string }> {
    return request<{ id: string; status: string; message: string }>(
      `/approvals/${id}/reject`,
      {
        method: 'POST',
        body: JSON.stringify(action || {}),
      }
    )
  },

  // 5. Reports & Dashboard
  async getReport(id: string): Promise<ReportResponse> {
    return request<ReportResponse>(`/runs/${id}/report`)
  },

  async getDashboardStats(runId?: string): Promise<DashboardStatsResponse> {
    const url = runId ? `/dashboard/stats?run_id=${encodeURIComponent(runId)}` : '/dashboard/stats'
    return request<DashboardStatsResponse>(url)
  },

  async resetWorkspace(): Promise<{ status: string; message: string }> {
    return request<{ status: string; message: string }>('/runs/reset', {
      method: 'POST',
    })
  },

  // 6. Real-Time Events URL Helper & Historical Audit Logs
  getEventsStreamUrl(id: string): string {
    return `${API_BASE_URL}/runs/${id}/events`
  },

  async getRunLogs(id: string): Promise<AgentLogEvent[]> {
    return request<AgentLogEvent[]>(`/runs/${id}/logs`)
  },

  // 7. Sample Specification Helper
  getSamplePdfUrl(): string {
    return `${API_BASE_URL}/documents/sample.pdf`
  },

  async getSamplePdfBlob(): Promise<Blob> {
    const res = await fetch(`${API_BASE_URL}/documents/sample.pdf`)
    if (!res.ok) throw new Error('Failed to download sample PDF')
    return res.blob()
  },
}
