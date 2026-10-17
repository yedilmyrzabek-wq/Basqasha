import { useMutation, useQuery } from '@tanstack/react-query'
import { request } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject } from '@/api/hooks'
import { CopyButton, Empty, ErrorBox, Loading } from '@/components/common'
import { Badge, type BadgeTone } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { isNotFound, type StepViewProps } from './types'

type Item = {
  category: string
  priority: number
  title: string
  details: string
  where: string
  flow_prompt: string
  done: boolean
}
type Doc = { summary: string; items: Item[] }

const CATEGORY: Record<string, string> = {
  character: 'персонаж', poses: 'позы', sounds: 'звуки', music: 'музыка', backgrounds: 'фоны',
  script: 'сценарий', packaging: 'упаковка', pipeline: 'система',
}
const PRIORITY: Record<number, { label: string; tone: BadgeTone }> = {
  1: { label: 'до следующего видео', tone: 'red' },
  2: { label: 'скоро', tone: 'yellow' },
  3: { label: 'по желанию', tone: 'neutral' },
}

export default function RecommendationsStep({ project, state }: StepViewProps) {
  const id = project.id
  const invalidate = useInvalidateProject(id)
  const recs = useQuery({
    queryKey: [...projectKey(id), 'recommendations', stepVersionKey(project, 'recommendations')],
    queryFn: () => request<Doc>(`/api/projects/${id}/recommendations`),
    retry: false,
  })
  const mark = useMutation({
    mutationFn: ({ index, done }: { index: number; done: boolean }) =>
      request<Doc>(`/api/projects/${id}/recommendations/${index}`, { method: 'PATCH', body: { done } }),
    onSettled: invalidate,
  })

  if (recs.isLoading) return <Loading />
  if (recs.isError && !isNotFound(recs.error)) return <ErrorBox error={recs.error} />
  const doc = recs.data
  if (!doc) return <Empty>{state.status === 'running' ? 'Смотрим, чего не хватило…' : 'Рекомендаций пока нет.'}</Empty>
  const left = doc.items.filter((i) => !i.done).length

  return (
    <div className="grid gap-3 text-sm">
      <p>{doc.summary}</p>
      <p className="text-xs text-muted-foreground">
        Осталось {left} из {doc.items.length}. Отмечай, что добавил — новые позы и звуки подхватятся в следующем видео.
      </p>
      <ul className="grid gap-2">
        {doc.items.map((it, i) => {
          const pr = PRIORITY[it.priority] ?? PRIORITY[3]
          return (
            <li key={i} className={cn('grid gap-1.5 rounded-md border p-3', it.done && 'opacity-60')}>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="checkbox"
                  aria-label="Сделано"
                  checked={it.done}
                  disabled={mark.isPending}
                  onChange={(e) => mark.mutate({ index: i, done: e.target.checked })}
                />
                <b className={cn(it.done && 'line-through')}>{it.title}</b>
                <Badge tone="blue">{CATEGORY[it.category] ?? it.category}</Badge>
                <Badge tone={pr.tone}>{pr.label}</Badge>
              </div>
              <p>{it.details}</p>
              <p className="text-xs">
                <span className="text-muted-foreground">Куда добавить:</span> {it.where}
              </p>
              {it.flow_prompt && (
                <div className="grid gap-1 rounded bg-muted p-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-muted-foreground">Промпт для Google Flow</span>
                    <CopyButton text={it.flow_prompt} />
                  </div>
                  <p className="font-mono text-xs">{it.flow_prompt}</p>
                </div>
              )}
            </li>
          )
        })}
      </ul>
      <ErrorBox error={mark.error} />
    </div>
  )
}
