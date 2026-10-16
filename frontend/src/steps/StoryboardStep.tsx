import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from '@/api/client'
import { projectKey, stepVersionKey } from '@/api/hooks'
import { Empty, ErrorBox, Loading } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { isNotFound, type StepViewProps } from './types'

export default function StoryboardStep({ project, state }: StepViewProps) {
  const id = project.id
  const sb = useQuery({
    queryKey: [...projectKey(id), 'storyboard', stepVersionKey(project, 'storyboard')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/storyboard', { params: { path: { projectId: id } } })),
    retry: false,
  })
  if (sb.isLoading) return <Loading />
  if (sb.isError && !isNotFound(sb.error)) return <ErrorBox error={sb.error} />
  const data = sb.data?.data
  if (!data) return <Empty>{state.status === 'running' ? 'Строим раскадровку…' : 'Раскадровки пока нет.'}</Empty>
  const errors = sb.data?.errors ?? []
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span>
          Версия <b>{sb.data?.version}</b>
        </span>
        <span>Сцен: {data.scenes.length}</span>
        <span>Фонов: {data.backgrounds.length}</span>
        {errors.length ? <Badge tone="red">ошибок: {errors.length}</Badge> : <Badge tone="green">правила соблюдены</Badge>}
      </div>
      {errors.length > 0 && (
        <ul className="list-disc space-y-0.5 rounded-md border border-brand-red/40 bg-brand-red/5 py-2 pl-8 pr-3 text-sm text-brand-red">
          {errors.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}
      <div className="max-h-[32rem] overflow-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="sticky top-0 border-b bg-muted text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">#</th>
              <th className="px-3 py-2 font-medium">Текст</th>
              <th className="px-3 py-2 font-medium">Фон</th>
              <th className="px-3 py-2 font-medium">Поза</th>
              <th className="px-3 py-2 font-medium">Слова</th>
            </tr>
          </thead>
          <tbody>
            {data.scenes.map((s) => (
              <tr key={s.id} className="border-b align-top last:border-0">
                <td className="px-3 py-1.5 text-muted-foreground">{s.id}</td>
                <td className="px-3 py-1.5">{s.text}</td>
                <td className="px-3 py-1.5 font-mono text-xs">{s.background}</td>
                <td className="px-3 py-1.5 text-xs">{s.character?.pose ?? '—'}</td>
                <td className="px-3 py-1.5 text-xs tabular-nums text-muted-foreground">
                  {s.start_word}–{s.end_word}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
