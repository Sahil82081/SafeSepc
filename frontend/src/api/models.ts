import type { components } from './types'

export type Schema = components['schemas']

// Re-exported OpenAPI schema types
export type RunResponse = Schema['RunResponse']
export type RunUploadResponse = Schema['RunUploadResponse']
export type RunStartRequest = Schema['RunStartRequest']
export type ApprovalItemResponse = Schema['ApprovalItemResponse']
export type ApprovalActionRequest = Schema['ApprovalActionRequest']
export type DashboardStatsResponse = Schema['DashboardStatsResponse']
export type ReportResponse = Schema['ReportResponse']
export type TraceabilityGraphResponse = Schema['TraceabilityGraphResponse']
export type TraceabilityNode = Schema['TraceabilityNode']
export type TraceabilityEdge = Schema['TraceabilityEdge']

// Domain Types used across SafeSpec
export interface Requirement {
  id: string
  text: string
  source?: string | null
  asil?: 'QM' | 'A' | 'B' | 'C' | 'D' | string
  ambiguity?: 'LOW' | 'MEDIUM' | 'HIGH' | string
  ambiguity_reasons?: string[]
  suggested_refinement?: string | null
  created_at?: string | null
}

export interface RuleCondition {
  var: string
  op: '==' | '!=' | '>' | '<' | '>=' | '<=' | 'in' | 'not in' | string
  value: unknown
}

export interface RuleAction {
  var: string
  op: '==' | 'set' | string
  value: unknown
}

export interface Rule {
  id: string
  text: string
  condition: RuleCondition
  action: RuleAction
  not_formalizable?: boolean
  reason?: string
  back_translation?: string | null
}

export interface Conflict {
  id?: string
  rule_a_id: string
  rule_b_id: string
  reason: string
  counter_example?: Record<string, unknown>
  state_conflict?: boolean
}

export interface TestCase {
  id: string
  req_id: string
  name: string
  category: 'boundary' | 'normal' | 'negative' | 'fault_injection' | string
  inputs: Record<string, unknown>
  expected: Record<string, unknown>
  description?: string
}

export interface TestResult {
  test_id: string
  req_id?: string
  category?: string
  inputs: Record<string, unknown>
  expected_value: unknown
  actual_value: unknown
  passed: boolean
  status?: 'PASSED' | 'FAILED' | 'ERROR' | string
  log?: string
  execution_time_ms?: number
}

export interface FixRecord {
  id?: string
  root_cause?: string
  hypothesis?: string
  original_version?: string
  candidate_version?: string
  patch_diff?: string
  status?: string
  risk_score?: number
  created_at?: string
}

export interface AgentLogEvent {
  id?: number
  cycle_id?: string
  node?: string
  agent_name?: string
  thought?: string | null
  action?: string | null
  tool_name?: string | null
  tool_input?: unknown
  tool_output?: unknown
  status?: string | null
  timestamp?: string
}
