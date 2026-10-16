import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, unwrap } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject } from '@/api/hooks'
import { Empty, ErrorBox, Loading } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { fmtDuration } from '@/lib/utils'
import { isNotFound, type StepViewProps } from './types'

function CommentBox({ projectId, sceneId }: { projectId: string; sceneId: number }) {
  const invalidate = useInvalidateProject(projectId)
  const [text, setText] = useState('')
  const add = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/api/projects/{projectId}/preview/comments', {
          params: { path: { projectId } },
          body: { scene_id: sceneId, text: text.trim() },
        }),
      ),
    onSuccess: () => setText(''),
    onSettled: invalidate,
  })
  return (
    <form
      className="flex gap-1.5"
      onSubmit={(e) => {
        e.preventDefault()
        if (text.trim()) add.mutate()
      }}
    >
      <Input className="h-8" placeholder="Комментарий к сцене…" value={text} onChange={(e) => setText(e.target.value)} />
      <Button size="sm" type="submit" variant="outline" disabled={!text.trim() || add.isPending}>
        Добавить
      </Button>
      {add.isError && <span className="text-xs text-brand-red">ошибка</span>}
    </form>
  )
}

export default function PreviewStep({ project, state }: StepViewProps) {
  const id = project.id
  const invalidate = useInvalidateProject(id)
  const preview = useQuery({
    queryKey: [...projectKey(id), 'preview', stepVersionKey(project, 'preview')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/preview', { params: { path: { projectId: id } } })),
    retry: false,
  })
  const apply = useMutation({
    mutationFn: () =>
      unwrap(api.POST('/api/projects/{projectId}/preview/apply-comments', { params: { path: { projectId: id } } })),
    onSettled: invalidate,
  })
  const approve = useMutation({
    mutationFn: () => unwrap(api.POST('/api/projects/{projectId}/preview/approve', { params: { path: { projectId: id } } })),
    onSettled: invalidate,
  })

  if (preview.isLoading) return <Loading />
  if (preview.isError && !isNotFound(preview.error)) return <ErrorBox error={preview.error} />
  const p = preview.data
  if (!p?.contact_sheet_url && !p?.scenes?.length)
    return <Empty>{state.status === 'running' ? 'Рендерим кадры превью…' : 'Превью пока нет.'}</Empty>
  const open = (p.scenes ?? []).reduce((n, s) => n + (s.comments ?? []).filter((c) => !c.resolved).length, 0)

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant={state.wait_reason === 'approve_preview' ? 'accent' : 'default'}
          disabled={approve.isPending || state.status === 'running'}
          onClick={() => approve.mutate()}
        >
          Утвердить и рендерить
        </Button>
        <Button variant="outline" disabled={!open || apply.isPending || state.status === 'running'} onClick={() => apply.mutate()}>
          Применить комментарии ({open})
        </Button>
        <span className="text-sm text-muted-foreground">Раскадровка v{p.storyboard_version}</span>
      </div>
      <ErrorBox error={approve.error ?? apply.error} />
      {p.contact_sheet_url && (
        <a href={p.contact_sheet_url} target="_blank" rel="noreferrer">
          <img src={p.contact_sheet_url} alt="Лист превью" className="w-full rounded-md border" />
        </a>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        {(p.scenes ?? []).map((s) => (
          <div key={s.scene_id} className="grid grid-cols-[160px_1fr] gap-3 rounded-md border bg-paper p-2">
            {s.still_url ? (
              <img src={s.still_url} alt={`Сцена ${s.scene_id}`} className="aspect-video w-full rounded object-cover" loading="lazy" />
            ) : (
              <div className="aspect-video rounded bg-muted" />
            )}
            <div className="grid content-start gap-1.5 text-sm">
              <div className="text-xs text-muted-foreground">
                Сцена {s.scene_id} · {fmtDuration(s.start)}–{fmtDuration(s.end)}
              </div>
              <p className="line-clamp-3">{s.text}</p>
              {(s.comments ?? []).map((c) => (
                <p key={c.id} className={c.resolved ? 'text-xs text-muted-foreground line-through' : 'text-xs text-brand-blue'}>
                  » {c.text}
                </p>
              ))}
              {s.scene_id != null && <CommentBox projectId={id} sceneId={s.scene_id} />}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
