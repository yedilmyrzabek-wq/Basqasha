import { useMutation } from '@tanstack/react-query'
import { ArrowLeft, ChevronDown, ChevronRight, RotateCcw } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, unwrap, type ProjectDetail, type StepKey, type StepState } from '@/api/client'
import { useInvalidateProject, useProject, useRunStep, useStepLogs } from '@/api/hooks'
import { ErrorBox, Loading, Notice, StepStatusBadge } from '@/components/common'
import { MinutesInput } from '@/components/MinutesInput'
import { ProjectActions, StopButton } from '@/components/ProjectActions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { PROJECT_STATUS, STEPS, WAIT_REASON, focusStep, stepState } from '@/lib/steps'
import { cn, fmtDate, fmtDuration, fmtUsd } from '@/lib/utils'
import { STEP_VIEWS } from '@/steps'

function ProjectHeader({ project }: { project: ProjectDetail }) {
  const invalidate = useInvalidateProject(project.id)
  const patch = useMutation({
    mutationFn: (body: { target_seconds?: number }) =>
      unwrap(api.PATCH('/api/projects/{projectId}', { params: { path: { projectId: project.id } }, body })),
    onSettled: invalidate,
  })
  const st = PROJECT_STATUS[project.status]
  const warn = project.budget_warn_usd != null && project.cost_usd >= project.budget_warn_usd
  return (
    <div className="mb-4">
      <Link to="/" className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-ink">
        <ArrowLeft className="size-4" /> Проекты
      </Link>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{project.title || 'Без названия'}</h1>
        <Badge tone={st.tone}>{st.label}</Badge>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Длительность</span>
          <MinutesInput
            seconds={project.target_seconds}
            disabled={patch.isPending}
            onCommit={(sec) => patch.mutate({ target_seconds: sec })}
          />
          {project.target_words != null && (
            <span className="text-muted-foreground">≈ {project.target_words} слов</span>
          )}
        </div>
        {project.duration != null && (
          <span className="text-sm">
            <span className="text-muted-foreground">Голос:</span> {fmtDuration(project.duration)}
          </span>
        )}
        <span className={cn('text-sm tabular-nums', warn && 'font-semibold text-brand-red')}>
          <span className="font-normal text-muted-foreground">Расход:</span> {fmtUsd(project.cost_usd)}
          {project.budget_usd != null && ` / ${fmtUsd(project.budget_usd)}`}
        </span>
        <div className="ml-auto flex gap-2">
          {project.source_url && (
            <Button asChild variant="ghost" size="sm">
              <a href={project.source_url} target="_blank" rel="noreferrer">
                Источник ↗
              </a>
            </Button>
          )}
          {project.steps?.some((s) => s.status === 'running') && <StopButton projectId={project.id} />}
          <ProjectActions project={project} />
        </div>
      </div>
      <ErrorBox error={patch.error} className="mt-2" />
    </div>
  )
}

function StepList({
  project,
  selected,
  onSelect,
}: {
  project: ProjectDetail
  selected: StepKey
  onSelect: (k: StepKey) => void
}) {
  return (
    <nav aria-label="Шаги" className="flex flex-col gap-1">
      {STEPS.map((s, i) => {
        const st = stepState(project, s.key)
        return (
          <button
            key={s.key}
            onClick={() => onSelect(s.key)}
            aria-current={selected === s.key ? 'step' : undefined}
            className={cn(
              'rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              selected === s.key ? 'border-ink bg-paper shadow-sm' : 'border-transparent hover:bg-paper/70',
              st.status === 'waiting_operator' && selected !== s.key && 'border-brand-yellow/70',
            )}
          >
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'grid size-6 shrink-0 place-items-center rounded-full text-xs font-semibold',
                  st.status === 'done' ? 'bg-brand-green text-paper' : 'bg-muted text-ink',
                )}
              >
                {i + 1}
              </span>
              <span className="flex-1 text-sm font-medium">{s.title}</span>
              <StepStatusBadge status={st.status} />
            </div>
            {st.status === 'waiting_operator' && st.wait_reason && (
              <div className="mt-1 pl-8 text-xs text-[#8a6410]">{WAIT_REASON[st.wait_reason]}</div>
            )}
            {st.status === 'failed' && st.error && (
              <div className="mt-1 line-clamp-2 pl-8 text-xs text-brand-red">{st.error}</div>
            )}
            {st.status === 'running' && st.progress != null && (
              <div className="ml-8 mt-1.5 h-1 overflow-hidden rounded bg-muted">
                <div className="h-full bg-brand-blue" style={{ width: `${Math.round(st.progress * 100)}%` }} />
              </div>
            )}
          </button>
        )
      })}
    </nav>
  )
}

function StepLogs({ projectId, state }: { projectId: string; state: StepState }) {
  const [open, setOpen] = useState(false)
  const logs = useStepLogs(projectId, state.step, open, state.status === 'running')
  return (
    <div className="border-t">
      <button
        className="flex w-full items-center gap-1 px-4 py-2 text-sm text-muted-foreground hover:text-ink"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />} Логи шага
      </button>
      {open && (
        <div className="px-4 pb-4">
          {logs.isLoading ? (
            <Loading />
          ) : logs.isError ? (
            <ErrorBox error={logs.error} />
          ) : !logs.data?.length ? (
            <p className="text-sm text-muted-foreground">Логов пока нет.</p>
          ) : (
            <pre className="max-h-72 overflow-auto rounded-md bg-ink p-3 text-xs leading-relaxed text-paper">
              {logs.data.map((l) => (
                <div
                  key={l.id}
                  className={cn(
                    l.level === 'error' && 'text-brand-red',
                    l.level === 'warning' && 'text-brand-yellow',
                    l.level === 'debug' && 'opacity-60',
                  )}
                >
                  {fmtDate(l.created_at)} [{l.level}] {l.message}
                </div>
              ))}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

function BudgetRaise({ project, step }: { project: ProjectDetail; step: StepKey }) {
  const [value, setValue] = useState(String((project.budget_usd ?? 5) + 2.5))
  const invalidate = useInvalidateProject(project.id)
  const raise = useMutation({
    mutationFn: async () => {
      await unwrap(
        api.PATCH('/api/projects/{projectId}', {
          params: { path: { projectId: project.id } },
          body: { budget_usd: Number(value) },
        }),
      )
      return unwrap(api.POST('/api/projects/{projectId}/steps/{step}/run', { params: { path: { projectId: project.id, step } } }))
    },
    onSettled: invalidate,
  })
  return (
    <Notice>
      <div className="flex flex-wrap items-center gap-2">
        <span>
          Потрачено {fmtUsd(project.cost_usd)} из {fmtUsd(project.budget_usd)}. Новый лимит, $:
        </span>
        <Input aria-label="Новый лимит, $" className="h-8 w-24" type="number" min={0} step={0.5} value={value} onChange={(e) => setValue(e.target.value)} />
        <Button size="sm" disabled={raise.isPending || !(Number(value) > 0)} onClick={() => raise.mutate()}>
          Увеличить и продолжить
        </Button>
      </div>
      <ErrorBox error={raise.error} className="mt-2" />
    </Notice>
  )
}

function StepPanel({ project, step }: { project: ProjectDetail; step: StepKey }) {
  const state = stepState(project, step)
  const meta = STEPS.find((s) => s.key === step)!
  const index = STEPS.indexOf(meta)
  const run = useRunStep(project.id)
  const View = STEP_VIEWS[step]
  return (
    <Card>
      <div className="flex flex-wrap items-start gap-3 border-b p-4">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">
              Шаг {index + 1}. {meta.title}
            </h2>
            <StepStatusBadge status={state.status} />
            {!!state.attempts && state.attempts > 1 && (
              <span className="text-xs text-muted-foreground">попытка {state.attempts}</span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">{meta.hint}</p>
        </div>
        {state.status === 'running' && <StopButton projectId={project.id} />}
        <Button
          variant="outline"
          size="sm"
          disabled={state.status === 'running' || run.isPending}
          onClick={() => run.mutate(step)}
          title="Запустить шаг заново; следующие готовые шаги станут устаревшими"
        >
          <RotateCcw /> {state.status === 'pending' ? 'Запустить' : 'Повторить'}
        </Button>
      </div>
      <div className="grid gap-3 p-4">
        <ErrorBox error={run.error} />
        {state.status === 'waiting_operator' && state.wait_reason && (
          <Notice>
            <b>Ждёт вас:</b> {WAIT_REASON[state.wait_reason]}
          </Notice>
        )}
        {state.wait_reason === 'budget_exceeded' && <BudgetRaise project={project} step={step} />}
        {state.status === 'failed' && state.error && <ErrorBox error={state.error} />}
        {state.status === 'stale' && (
          <Notice tone="blue">Входные данные изменились — результат устарел. Нажмите «Повторить», чтобы пересчитать.</Notice>
        )}
        {state.status === 'running' && (
          <Notice tone="blue">
            Выполняется{state.progress != null ? ` — ${Math.round(state.progress * 100)}%` : '…'} Страница обновляется
            автоматически.
          </Notice>
        )}
        <View project={project} state={state} />
      </div>
      <StepLogs projectId={project.id} state={state} />
    </Card>
  )
}

export default function ProjectPage() {
  const { projectId = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const project = useProject(projectId)

  if (project.isLoading) return <Loading />
  if (project.isError) return <ErrorBox error={project.error} />
  const p = project.data!
  const selected = (params.get('step') as StepKey | null) ?? focusStep(p)

  return (
    <div>
      <ProjectHeader project={p} />
      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        <aside className="lg:sticky lg:top-4 lg:self-start">
          <StepList project={p} selected={selected} onSelect={(k) => setParams({ step: k }, { replace: true })} />
        </aside>
        <StepPanel key={selected} project={p} step={selected} />
      </div>
    </div>
  )
}
