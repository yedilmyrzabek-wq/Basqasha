import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap, type ProjectDetail, type StepKey } from './client'
import { shouldPoll, stepState } from '@/lib/steps'

/** Every per-project query lives under ['p', id] so one invalidate refreshes the page. */
export const projectKey = (id: string) => ['p', id] as const

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => unwrap(api.GET('/api/projects')),
    refetchInterval: 10_000,
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: [...projectKey(id), 'detail'],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}', { params: { path: { projectId: id } } })),
    refetchInterval: (q) => (shouldPoll(q.state.data as ProjectDetail | undefined) ? 2000 : false),
  })
}

/**
 * Content queries are keyed by the step's status + updated_at, so they refetch
 * automatically when the polled project shows the step changed.
 */
export function stepVersionKey(project: ProjectDetail | undefined, step: StepKey) {
  const s = stepState(project, step)
  return `${s.status}:${s.updated_at ?? ''}`
}

export function useInvalidateProject(id: string) {
  const qc = useQueryClient()
  return () => {
    void qc.invalidateQueries({ queryKey: projectKey(id) })
    void qc.invalidateQueries({ queryKey: ['projects'] })
  }
}

export function useRunStep(id: string) {
  const invalidate = useInvalidateProject(id)
  return useMutation({
    mutationFn: (step: StepKey) =>
      unwrap(api.POST('/api/projects/{projectId}/steps/{step}/run', { params: { path: { projectId: id, step } } })),
    onSettled: invalidate,
  })
}

export function useStepLogs(id: string, step: StepKey, enabled: boolean, live: boolean) {
  return useQuery({
    queryKey: [...projectKey(id), 'logs', step],
    queryFn: () =>
      unwrap(api.GET('/api/projects/{projectId}/steps/{step}/logs', { params: { path: { projectId: id, step } } })),
    enabled,
    refetchInterval: live ? 2000 : false,
  })
}

export function useSettings() {
  return useQuery({ queryKey: ['settings'], queryFn: () => unwrap(api.GET('/api/settings')) })
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => unwrap(api.GET('/api/health')),
    refetchInterval: 30_000,
    retry: false,
  })
}
