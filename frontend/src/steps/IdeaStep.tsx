import { useMutation, useQuery } from '@tanstack/react-query'
import { Check } from 'lucide-react'
import { useState } from 'react'
import { api, unwrap, type Angle } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject } from '@/api/hooks'
import { Empty, ErrorBox, Loading, Notice } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label, Select, Textarea } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { isNotFound, type StepViewProps } from './types'

const CATEGORY: Record<string, string> = {
  H: 'История',
  W: 'Как это работает',
  E: 'Экономика',
  G: 'География / природа',
  S: 'Наука',
  F: 'Еда',
  Sp: 'Спорт',
  P: 'Психология',
  M: 'Мотивация',
}
const HOOK: Record<string, string> = {
  question: 'вопрос',
  number: 'число',
  paradox: 'парадокс',
  scene: 'сцена',
  myth: 'миф',
}
const RISK = ['нет', 'низкий', 'средний', 'отклонить']

function CustomAngleForm({ projectId, onDone }: { projectId: string; onDone: () => void }) {
  const invalidate = useInvalidateProject(projectId)
  const [a, setA] = useState<Angle>({ title: '', pitch: '', why_it_works: '' })
  const submit = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/api/projects/{projectId}/angles/custom', {
          params: { path: { projectId } },
          body: {
            title: a.title.trim(),
            pitch: a.pitch.trim(),
            ...(a.why_it_works?.trim() ? { why_it_works: a.why_it_works.trim() } : {}),
            ...(a.suggested_hook_type ? { suggested_hook_type: a.suggested_hook_type } : {}),
          },
        }),
      ),
    onSuccess: onDone,
    onSettled: invalidate,
  })
  const titleOk = a.title.trim().length >= 3 && a.title.trim().length <= 60
  return (
    <Card>
      <CardHeader>
        <CardTitle>Свой вариант</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="grid gap-1.5">
          <Label htmlFor="ca-title">Рабочее название (на языке видео, 3–60 символов)</Label>
          <Input id="ca-title" maxLength={60} value={a.title} onChange={(e) => setA({ ...a, title: e.target.value })} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="ca-pitch">О чём видео (до 600 символов)</Label>
          <Textarea
            id="ca-pitch"
            rows={4}
            maxLength={600}
            value={a.pitch}
            onChange={(e) => setA({ ...a, pitch: e.target.value })}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="ca-why">Почему зайдёт (для себя)</Label>
          <Textarea
            id="ca-why"
            rows={2}
            maxLength={400}
            value={a.why_it_works ?? ''}
            onChange={(e) => setA({ ...a, why_it_works: e.target.value })}
          />
        </div>
        <div className="grid gap-1.5 sm:w-60">
          <Label htmlFor="ca-hook">Тип хука</Label>
          <Select
            id="ca-hook"
            value={a.suggested_hook_type ?? ''}
            onChange={(e) =>
              setA({ ...a, suggested_hook_type: (e.target.value || undefined) as Angle['suggested_hook_type'] })
            }
          >
            <option value="">— авто —</option>
            {Object.entries(HOOK).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </Select>
        </div>
        <ErrorBox error={submit.error} />
      </CardContent>
      <CardFooter>
        <Button disabled={!titleOk || !a.pitch.trim() || submit.isPending} onClick={() => submit.mutate()}>
          Выбрать свой вариант
        </Button>
        <Button variant="ghost" onClick={onDone}>
          Отмена
        </Button>
      </CardFooter>
    </Card>
  )
}

export default function IdeaStep({ project, state }: StepViewProps) {
  const id = project.id
  const invalidate = useInvalidateProject(id)
  const idea = useQuery({
    queryKey: [...projectKey(id), 'idea', stepVersionKey(project, 'idea')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/idea', { params: { path: { projectId: id } } })),
    retry: false,
  })
  const choose = useMutation({
    mutationFn: (angleId: string) =>
      unwrap(api.POST('/api/projects/{projectId}/angles/{angleId}/choose', { params: { path: { projectId: id, angleId } } })),
    onSettled: invalidate,
  })
  const [custom, setCustom] = useState(false)

  if (idea.isLoading) return <Loading />
  if (idea.isError && !isNotFound(idea.error)) return <ErrorBox error={idea.error} />
  const brief = idea.data?.brief
  const angles = idea.data?.angles ?? []
  if (!brief && !angles.length)
    return <Empty>{state.status === 'running' ? 'Готовим бриф и варианты…' : 'Бриф ещё не готов.'}</Empty>

  return (
    <div className="grid gap-4">
      {brief && (
        <div className="grid gap-2 rounded-md border bg-paper p-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-base font-semibold">{brief.topic}</span>
            {brief.category && <Badge tone="blue">{CATEGORY[brief.category] ?? brief.category}</Badge>}
            <Badge tone={brief.risk >= 2 ? 'red' : brief.risk === 1 ? 'yellow' : 'green'}>
              риск: {RISK[brief.risk] ?? brief.risk}
            </Badge>
          </div>
          {brief.operator_summary && <p>{brief.operator_summary}</p>}
          <p>
            <span className="text-muted-foreground">Главный вопрос:</span> {brief.core_question}
          </p>
          <p>
            <span className="text-muted-foreground">Структура:</span> {brief.structure_idea.join(' → ')}
          </p>
          {brief.key_concepts.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {brief.key_concepts.map((k) => (
                <span key={k.term} className="rounded bg-muted px-2 py-0.5 text-xs" title={k.gloss}>
                  <b>{k.term}</b> — {k.gloss}
                </span>
              ))}
            </div>
          )}
          {!!brief.sensitive_topics?.length && (
            <Notice>Чувствительные темы: {brief.sensitive_topics.join(', ')} — нужны ≥ 2 источника на каждую цифру.</Notice>
          )}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-3">
        {angles.map((row) => {
          const a = row.data
          if (!a || !row.id) return null
          return (
            <Card key={row.id} className={cn('flex flex-col', row.chosen && 'border-brand-green ring-2 ring-brand-green/40')}>
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle>{a.title}</CardTitle>
                  {a.score != null && (
                    <Badge tone="ink" title="Оценка 0–40">
                      {a.score.toFixed(1)}
                    </Badge>
                  )}
                </div>
                <div className="flex flex-wrap gap-1">
                  {row.is_custom && <Badge tone="yellow">свой</Badge>}
                  {a.suggested_hook_type && <Badge>хук: {HOOK[a.suggested_hook_type]}</Badge>}
                </div>
              </CardHeader>
              <CardContent className="flex-1 space-y-2 text-sm">
                <p>{a.pitch}</p>
                {a.why_it_works && <p className="text-muted-foreground">{a.why_it_works}</p>}
                {!!a.hook_words?.length && (
                  <div className="flex flex-wrap gap-1">
                    {a.hook_words.map((w) => (
                      <span key={w} className="rounded bg-brand-yellow/25 px-1.5 py-0.5 text-xs">
                        {w}
                      </span>
                    ))}
                  </div>
                )}
              </CardContent>
              <CardFooter>
                {row.chosen ? (
                  <span className="inline-flex items-center gap-1 text-sm font-medium text-[#2b7a44]">
                    <Check className="size-4" /> Выбран
                  </span>
                ) : (
                  <Button
                    variant={state.wait_reason === 'choose_angle' ? 'accent' : 'outline'}
                    disabled={choose.isPending || state.status === 'running'}
                    onClick={() => choose.mutate(row.id!)}
                  >
                    Выбрать
                  </Button>
                )}
              </CardFooter>
            </Card>
          )
        })}
      </div>
      <ErrorBox error={choose.error} />
      {angles.some((a) => a.chosen) && state.status === 'done' && (
        <p className="text-xs text-muted-foreground">
          Выбор другого варианта сделает факты и все следующие шаги устаревшими.
        </p>
      )}

      {custom ? (
        <CustomAngleForm projectId={id} onDone={() => setCustom(false)} />
      ) : (
        <div>
          <Button variant="outline" onClick={() => setCustom(true)}>
            Свой вариант
          </Button>
        </div>
      )}
    </div>
  )
}
