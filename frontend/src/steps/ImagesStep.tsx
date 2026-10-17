import { useMutation, useQuery } from '@tanstack/react-query'
import { ImageOff } from 'lucide-react'
import { useRef, useState } from 'react'
import { api, formData, unwrap, type Schemas } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject } from '@/api/hooks'
import { CopyButton, Empty, ErrorBox, Loading } from '@/components/common'
import { Badge, type BadgeTone } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/input'
import { isNotFound, type StepViewProps } from './types'

type Slot = Schemas['ImageSlot'] & { flow_prompt?: string }
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
          <div className="flex items-start gap-1.5">
            <p className="line-clamp-3 flex-1 text-xs text-muted-foreground" title={slot.flow_prompt ?? slot.prompt}>
              {slot.prompt}
            </p>
            <CopyButton text={slot.flow_prompt ?? slot.prompt ?? ''} label="" aria-label="Копировать промпт для Flow" />
          </div>
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

const uploadOne = async (projectId: string, slot: string, file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch(`/api/projects/${projectId}/images/${slot}/upload`, { method: 'POST', body: fd })
  if (!r.ok) throw new Error(`${slot}: ${(await r.text()) || r.status}`)
}

/**
 * Manual mode: copy all prompts for Google Flow, then upload many files at once. A file whose name contains
 * a slot id (bg07.png, bg07_flow.jpg) goes to that slot; the rest fill the empty slots in name order.
 */
function ManualBar({ projectId, slots, disabled }: { projectId: string; slots: Slot[]; disabled: boolean }) {
  const invalidate = useInvalidateProject(projectId)
  const input = useRef<HTMLInputElement>(null)
  const [done, setDone] = useState<string | null>(null)
  const empty = slots.filter((s) => !s.url)
  const all = slots.map((s) => `${s.slot}: ${s.flow_prompt ?? s.prompt}`).join('\n\n')
  const emptyText = empty.map((s) => `${s.slot}: ${s.flow_prompt ?? s.prompt}`).join('\n\n')
  const bulk = useMutation({
    mutationFn: async (files: File[]) => {
      const ids = slots.map((s) => s.slot ?? '')
      const byName = new Map<string, File>()
      const rest: File[] = []
      for (const f of [...files].sort((a, b) => a.name.localeCompare(b.name))) {
        const m = f.name.toLowerCase().match(/bg\d+/)
        const id = m && ids.includes(m[0]) ? m[0] : null
        if (id && !byName.has(id)) byName.set(id, f)
        else rest.push(f)
      }
      for (const s of empty) if (!byName.has(s.slot ?? '') && rest.length) byName.set(s.slot ?? '', rest.shift()!)
      for (const [slot, f] of byName) await uploadOne(projectId, slot, f)
      return byName.size
    },
    onSuccess: (n) => setDone(`Загружено: ${n}`),
    onSettled: invalidate,
  })
  return (
    <div className="grid gap-2 rounded-md border border-brand-blue/30 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <b>Ручной режим (Google Flow)</b>
        <span className="text-muted-foreground">
          без картинки: {empty.length} из {slots.length}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <CopyButton text={emptyText || all} label={empty.length ? `Копировать промпты пустых (${empty.length})` : 'Копировать все промпты'} />
        {empty.length > 0 && empty.length < slots.length && <CopyButton text={all} label="Копировать все" />}
        <Button size="sm" variant="accent" disabled={disabled || bulk.isPending} onClick={() => input.current?.click()}>
          {bulk.isPending ? 'Загружаем…' : 'Загрузить пачкой'}
        </Button>
        <input
          ref={input}
          type="file"
          multiple
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={(e) => {
            const fs = Array.from(e.target.files ?? [])
            if (fs.length) bulk.mutate(fs)
            e.target.value = ''
          }}
        />
        {done && <span className="text-xs text-[#2b7a44]">{done}</span>}
      </div>
      <p className="text-xs text-muted-foreground">
        Назови файлы как слот (bg01.png, bg02.png…) — тогда каждый попадёт на своё место. Без номера файлы заполнят пустые
        слоты по порядку. В каждом промпте уже есть стиль; приложи в Flow 1–2 образца из library/style/samples.
      </p>
      <ErrorBox error={bulk.error} />
    </div>
  )
}

/** Placeholder backgrounds from library/style/samples — lets a project reach the video without image billing. */
function SamplesBar({ projectId, disabled }: { projectId: string; disabled: boolean }) {
  const invalidate = useInvalidateProject(projectId)
  const fill = useMutation({
    mutationFn: async (allSlots: boolean) => {
      const r = await fetch(`/api/projects/${projectId}/images/use-samples?all_slots=${allSlots}`, { method: 'POST' })
      if (!r.ok) throw new Error((await r.text()) || `HTTP ${r.status}`)
    },
    onSettled: invalidate,
  })
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button size="sm" variant="outline" disabled={disabled || fill.isPending} onClick={() => fill.mutate(false)}>
        Тестовые фоны для пустых
      </Button>
      <Button size="sm" variant="ghost" disabled={disabled || fill.isPending} onClick={() => fill.mutate(true)}>
        Заменить все тестовыми
      </Button>
      <span className="text-xs text-muted-foreground">
        Фоны-заглушки из библиотеки — чтобы дойти до видео без генерации картинок.
      </span>
      <ErrorBox error={fill.error} />
    </div>
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
    <div className="grid gap-3">
      {(state.wait_reason === 'manual_images' || slots.some((s) => !s.url)) && (
        <ManualBar projectId={id} slots={slots} disabled={state.status === 'running'} />
      )}
      <SamplesBar projectId={id} disabled={state.status === 'running'} />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {slots.map((s) => (
          <SlotCard key={`${s.slot}:${s.url}:${s.attempts}`} projectId={id} slot={s} />
        ))}
      </div>
    </div>
  )
}
