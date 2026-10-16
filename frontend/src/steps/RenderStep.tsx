import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { api, unwrap } from '@/api/client'
import { projectKey, stepVersionKey } from '@/api/hooks'
import { Empty, ErrorBox, Loading } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { fmtDate, fmtDuration } from '@/lib/utils'
import { isNotFound, type StepViewProps } from './types'

const KIND = { preview: 'превью', full: 'полное видео', short: 'Shorts' } as const

function downloadUrl(url: string) {
  return url + (url.includes('?') ? '&' : '?') + 'download=1'
}

export default function RenderStep({ project, state }: StepViewProps) {
  const id = project.id
  const renders = useQuery({
    queryKey: [...projectKey(id), 'renders', stepVersionKey(project, 'render')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/renders', { params: { path: { projectId: id } } })),
    retry: false,
  })
  if (renders.isLoading) return <Loading />
  if (renders.isError && !isNotFound(renders.error)) return <ErrorBox error={renders.error} />
  const list = (renders.data ?? []).filter((r) => r.url && r.kind !== 'preview')
  if (!list.length) return <Empty>{state.status === 'running' ? 'Рендерим видео…' : 'Видео ещё не отрендерено.'}</Empty>
  const main = list.find((r) => r.kind === 'full') ?? list[0]
  return (
    <div className="grid gap-4">
      <video key={main.url} controls src={main.url!} className="w-full rounded-md border bg-ink" />
      <ul className="grid gap-2">
        {list.map((r) => (
          <li key={r.id} className="flex flex-wrap items-center gap-3 rounded-md border bg-paper px-3 py-2 text-sm">
            <Badge tone={r.kind === 'full' ? 'ink' : 'blue'}>{r.kind ? KIND[r.kind] : '—'}</Badge>
            <span className="tabular-nums">{fmtDuration(r.duration)}</span>
            <span className="text-muted-foreground">{fmtDate(r.created_at)}</span>
            <Button asChild size="sm" variant="outline" className="ml-auto">
              <a href={downloadUrl(r.url!)} download>
                <Download /> Скачать
              </a>
            </Button>
          </li>
        ))}
      </ul>
    </div>
  )
}
