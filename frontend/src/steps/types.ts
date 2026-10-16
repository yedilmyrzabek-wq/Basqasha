import type { ProjectDetail, StepState } from '@/api/client'

export interface StepViewProps {
  project: ProjectDetail
  state: StepState
}

/** Content endpoints may 404 before the step has produced anything — treat as "no data yet". */
export function isNotFound(e: unknown): boolean {
  return !!e && typeof e === 'object' && 'status' in e && (e as { status: number }).status === 404
}
