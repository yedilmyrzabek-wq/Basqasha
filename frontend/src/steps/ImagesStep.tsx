import { useMutation, useQuery } from '@tanstack/react-query'
import { ImageOff } from 'lucide-react'
import { useRef, useState } from 'react'
import { api, formData, unwrap, type Schemas } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject } from '@/api/hooks'
import { Empty, ErrorBox, Loading } from '@/components/common'
import { Badge, type BadgeTone } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/input'
import { isNotFound, type StepViewProps } from './types'

type Slot = Schemas['ImageSlot']
const QA: Record<NonNullable<Slot['qa_status']>, { label: string; tone: BadgeTone }> = {
  pending: { label: 'проверка', tone: 'neutral' },
  passed: { label: 'QA пройден', tone: 'green' },
  failed: { label: 'QA не пройден', tone: 'red' },
  needs_manual: { label: 'нужна вручную', tone: 'yellow' },
  manual_approved: { label: 'своя картинка', tone: 'blue' },
}

function SlotCard({ projectId, slot }: { projectId: string; slot: Slot }) {
  const invalidate = useInvalidateProject(projectId)
  const [editing, setEditing] = useState(false)
  const [prompt, setPrompt] = useState(slot.prompt ?? '')
  const fileInput = useRef<HTMLInputElement>(null)
  const name = slot.slot ?? ''
  const regen = useMutation({
    mutationFn: (newPrompt?: string) =>
      unwrap(
        api.POST('/api/projects/{projectId}/images/{slot}/regenerate', {
          params: { path: { projectId, slot: name } },
          body: newPrompt ? { prompt: newPrompt } : {},
        }),
      ),
    onSuccess: () => setEditing(false),
    onSettled: invalidate,
  })
  const upload = useMutation({
    mutationFn: (file: File) =>
      unwrap(
        api.POST('/api/projects/{projectId}/images/{slot}/upload', {
          params: { path: { projectId, slot: name } },
          body: { file: file as unknown as string },
          bodySerializer: (b) => formData(b as Record<string, unknown>),
        }),
      ),
    onSettled: invalidate,
  })
  const qa = slot.qa_status ? QA[slot.qa_status] : null
  return (
    <Card className="overflow-hidden">
      <div className="aspect-video bg-muted">
        {slot.url ? (
          <a href={slot.url} target="_blank" rel="noreferrer">
            <img src={slot.url} alt={name} className="size-full object-cover" loading="lazy" />
          </a>
        ) : (
          <div className="grid size-full place-items-center text-muted-foreground">
            <ImageOff className="size-8" />
          </div>
        )}
      </div>
      <div className="grid gap-2 p-3 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono font-semibold">{name}</span>
          {qa && <Badge tone={qa.tone}>{qa.label}</Badge>}
          {slot.attempts != null && <span className="text-xs text-muted-foreground">попыток: {slot.attempts}</span>}
        </div>
        {slot.qa_notes && <p className="text-xs text-brand-red">{slot.qa_notes}</p>}
        {!!slot.used_in_scenes?.length && (
          <p className="text-xs text-muted-foreground">Сцены: {slot.used_in_scenes.join(', ')}</p>
        )}
        {editing ? (
          <>
            <Textarea rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
            <div className="flex gap-2">
              <Button size="sm" disabled={regen.isPending || !prompt.trim()} onClick={() => regen.mutate(prompt.trim())}>
                Сгенерировать
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
                Отмена
              </Button>
            </div>
          </>
        ) : (
          <p className="line-clamp-3 text-xs text-muted-foreground" title={slot.prompt}>
            {slot.prompt}
          </p>
        )}
        <div className="flex flex-wrap gap-1.5">
          <Button size="sm" variant="outline" disabled={regen.isPending} onClick={() => regen.mutate(undefined)}>
            Перегенерировать
          </Button>
          <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
            Изменить промпт
          </Button>
          <Button size="sm" variant="outline" disabled={upload.isPending} onClick={() => fileInput.current?.click()}>
            Загрузить свою
          </Button>
          <input
            ref={fileInput}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) upload.mutate(f)
              e.target.value = ''
            }}
          />
        </div>
        <ErrorBox error={regen.error ?? upload.error} />
      </div>
    </Card>
  )
}

export default function ImagesStep({ project, state }: StepViewProps) {
  const id = project.id
  const images = useQuery({
    queryKey: [...projectKey(id), 'images', stepVersionKey(project, 'images')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/images', { params: { path: { projectId: id } } })),
    retry: false,
    refetchInterval: state.status === 'running' ? 3000 : false,
  })
  if (images.isLoading) return <Loading />
  if (images.isError && !isNotFound(images.error)) return <ErrorBox error={images.error} />
  const slots = images.data ?? []
  if (!slots.length) return <Empty>{state.status === 'running' ? 'Генерируем картинки…' : 'Картинок пока нет.'}</Empty>
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {slots.map((s) => (
        <SlotCard key={`${s.slot}:${s.url}:${s.attempts}`} projectId={id} slot={s} />
      ))}
    </div>
  )
}
