import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, unwrap } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject } from '@/api/hooks'
import { CopyButton, Empty, ErrorBox, Loading, Notice } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Input, Label } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { isNotFound, type StepViewProps } from './types'

export default function MetadataStep({ project, state }: StepViewProps) {
  const id = project.id
  const invalidate = useInvalidateProject(id)
  const meta = useQuery({
    queryKey: [...projectKey(id), 'metadata', stepVersionKey(project, 'metadata')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/metadata', { params: { path: { projectId: id } } })),
    retry: false,
  })
  const [ytUrl, setYtUrl] = useState('')
  const publish = useMutation({
    mutationFn: () =>
      unwrap(api.POST('/api/projects/{projectId}/publish', { params: { path: { projectId: id } }, body: { url: ytUrl.trim() } })),
    onSettled: invalidate,
  })

  if (meta.isLoading) return <Loading />
  if (meta.isError && !isNotFound(meta.error)) return <ErrorBox error={meta.error} />
  const m = meta.data
  if (!m) return <Empty>{state.status === 'running' ? 'Пишем заголовки и описание…' : 'Метаданных пока нет.'}</Empty>
  const chapters = m.chapters.map((c) => `${c.at} ${c.title}`).join('\n')
  const tags = (m.tags ?? []).join(', ')

  return (
    <div className="grid gap-5 text-sm">
      <section className="grid gap-2">
        <h3 className="font-semibold">Заголовки</h3>
        {m.titles.map((t, i) => (
          <div key={i} className="flex items-center gap-3 rounded-md border bg-paper px-3 py-2">
            <span className="flex-1">{t}</span>
            <span className={cn('text-xs tabular-nums', t.length > 60 ? 'text-brand-red' : 'text-muted-foreground')}>
              {t.length}/60
            </span>
            <CopyButton text={t} />
          </div>
        ))}
      </section>
      <section className="grid gap-2">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold">Описание</h3>
          <CopyButton text={m.description} />
        </div>
        <div className="whitespace-pre-wrap rounded-md border bg-paper p-3">{m.description}</div>
      </section>
      <section className="grid gap-2">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold">Главы</h3>
          <CopyButton text={chapters} />
        </div>
        <pre className="whitespace-pre-wrap rounded-md border bg-paper p-3 font-[inherit]">{chapters}</pre>
      </section>
      {(tags || m.hashtags?.length) && (
        <section className="grid gap-2">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold">Теги</h3>
            {tags && <CopyButton text={tags} />}
          </div>
          {tags && <p>{tags}</p>}
          {!!m.hashtags?.length && <p className="text-brand-blue">{m.hashtags.join(' ')}</p>}
        </section>
      )}
      <section className="grid gap-2">
        <h3 className="font-semibold">Текст на превью (обложку)</h3>
        <div className="flex flex-wrap gap-2">
          {m.thumbnail_texts.map((t, i) => (
            <div key={i} className="flex items-center gap-2 rounded-md border bg-paper px-3 py-1.5">
              <b>{t}</b>
              <CopyButton text={t} label="" aria-label="Копировать" />
            </div>
          ))}
        </div>
      </section>
      <section className="grid gap-1">
        <h3 className="font-semibold">Чек-лист публикации</h3>
        <ul className="list-disc pl-5">
          <li>«Для детей»: нет</li>
          <li>Раскрытие ИИ (изменённый/синтетический контент): {m.checklist.ai_disclosure ? 'ДА — отметить' : 'не требуется'}</li>
          <li>Платное продвижение: {m.checklist.paid_promotion ? 'ДА — отметить' : 'нет'}</li>
          {m.checklist.voice_plan_paid === false && (
            <li className="text-brand-red">Озвучка сделана на бесплатном тарифе ElevenLabs — публиковать нельзя</li>
          )}
        </ul>
      </section>
      <section className="grid gap-2 rounded-md border p-3">
        <Label htmlFor="yt-url">После загрузки в YouTube Studio вставьте ссылку на видео</Label>
        <div className="flex gap-2">
          <Input id="yt-url" placeholder="https://youtu.be/…" value={ytUrl} onChange={(e) => setYtUrl(e.target.value)} />
          <Button disabled={!/^https?:\/\//.test(ytUrl.trim()) || publish.isPending} onClick={() => publish.mutate()}>
            Отметить опубликованным
          </Button>
        </div>
        <ErrorBox error={publish.error} />
        {project.status === 'published' && <Notice tone="blue">Проект отмечен как опубликованный.</Notice>}
      </section>
    </div>
  )
}
