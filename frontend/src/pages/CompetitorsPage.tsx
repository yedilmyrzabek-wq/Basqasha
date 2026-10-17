import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, ImagePlus, RefreshCw, Sparkles, Trash2 } from 'lucide-react'
import { useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { request } from '@/api/client'
import { CopyButton, Empty, ErrorBox, Loading, Notice } from '@/components/common'
import { Badge, type BadgeTone } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label, Textarea } from '@/components/ui/input'
import { cn, fmtDate, fmtDuration } from '@/lib/utils'

// ------------------------------------------------------------------ types + api
type Status = 'pending' | 'running' | 'done' | 'failed'
type Idea = { title_kk: string; why_ru: string; source_url?: string | null; priority?: number }
type Analysis = {
  summary: string
  why_it_works: { aspect: string; insight: string }[]
  audience: string
  title_pattern: string
  thumbnail_concept: string
  hook: string
  apply_for_us: string[]
  rules: { area: string; rule: string }[]
  video_ideas: Idea[]
  learn_score: number
}
type Item = {
  id: string
  kind: 'video' | 'channel' | 'image'
  url: string | null
  title: string
  channel: string | null
  views: number | null
  duration_s: number | null
  published: string | null
  notes: string
  images: string[]
  info: Record<string, unknown> & {
    channel_subscribers?: number | null
    median_views?: number | null
    top_videos?: { title: string; views: number; url: string }[]
  }
  status: Status
  error: string | null
  analysis: Analysis | null
  created_at: string
}
type DocChange = { path: string; action: 'update' | 'create' | 'delete'; reason: string; content: string; old?: string | null }
type Report = {
  id: string
  kind: 'synthesis' | 'question'
  question: string | null
  status: Status
  error: string | null
  data:
    | (Partial<{ summary: string; doc_changes: DocChange[]; film_next: Idea[]; applied: string[]; answer_md: string }> &
        Record<string, unknown>)
    | null
  applied_at: string | null
  created_at: string
}

const busy = (s: Status) => s === 'pending' || s === 'running'
const fmtViews = (v: number | null | undefined) =>
  v == null ? '—' : v >= 1e6 ? `${(v / 1e6).toFixed(1)} млн` : v >= 1e3 ? `${Math.round(v / 1e3)} тыс` : String(v)

const STATUS: Record<Status, { label: string; tone: BadgeTone }> = {
  pending: { label: 'в очереди', tone: 'neutral' },
  running: { label: 'разбирается…', tone: 'yellow' },
  done: { label: 'разобрано', tone: 'green' },
  failed: { label: 'ошибка', tone: 'red' },
}
const ASPECT: Record<string, string> = {
  topic: 'тема', title: 'заголовок', thumbnail: 'обложка', hook: 'хук', structure: 'структура', pacing: 'темп',
  visuals: 'визуал', audio: 'звук', character: 'персонаж', emotion: 'эмоция', community: 'аудитория', other: 'другое',
}
const AREA: Record<string, string> = {
  ideas: 'идеи', titles: 'заголовки', thumbnails: 'обложки', script: 'сценарий', storyboard: 'раскадровка',
  visuals: 'визуал', audio: 'звук', publishing: 'публикация',
}

function useInvalidate() {
  const qc = useQueryClient()
  return () => {
    void qc.invalidateQueries({ queryKey: ['growth'] })
  }
}

// ------------------------------------------------------------------ add form
function AddForm() {
  const invalidate = useInvalidate()
  const [url, setUrl] = useState('')
  const [notes, setNotes] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const input = useRef<HTMLInputElement>(null)
  const add = useMutation({
    mutationFn: () => {
      const fd = new FormData()
      fd.append('url', url.trim())
      fd.append('notes', notes.trim())
      files.forEach((f) => fd.append('files', f))
      return request<Item>('/api/growth/items', { method: 'POST', body: fd })
    },
    onSuccess: () => {
      setUrl('')
      setNotes('')
      setFiles([])
    },
    onSettled: invalidate,
  })
  return (
    <Card>
      <CardHeader>
        <CardTitle>Добавить пример</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            add.mutate()
          }}
        >
          <div className="grid gap-1.5">
            <Label htmlFor="g-url">Ссылка на видео или канал YouTube</Label>
            <Input
              id="g-url"
              placeholder="https://www.youtube.com/watch?v=…  или  https://www.youtube.com/@канал"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="g-notes">Почему это круто (твой комментарий — агент опирается на него)</Label>
            <Textarea
              id="g-notes"
              rows={3}
              placeholder="Например: обложка — 2 слова и крупный довольный персонаж; название — простой вопрос; 14 млн просмотров за месяц"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => input.current?.click()}>
              <ImagePlus className="size-4" /> Обложки / скрины
            </Button>
            <input
              ref={input}
              type="file"
              multiple
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => {
                setFiles([...files, ...Array.from(e.target.files ?? [])])
                e.target.value = ''
              }}
            />
            {files.map((f, i) => (
              <span key={i} className="rounded bg-muted px-2 py-0.5 text-xs">
                {f.name}
              </span>
            ))}
            <div className="flex-1" />
            <Button type="submit" variant="accent" disabled={add.isPending || (!url.trim() && !files.length)}>
              {add.isPending ? 'Добавляем…' : 'Добавить и разобрать'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Для видео система сама скачает название, просмотры, обложку и начало субтитров; для канала — самые
            просматриваемые видео и их обложки. Можно и без ссылки — только скрин + комментарий.
          </p>
          <ErrorBox error={add.error} />
        </form>
      </CardContent>
    </Card>
  )
}

// ------------------------------------------------------------------ pieces
function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="grid gap-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      {children}
    </div>
  )
}

function CreateProjectButton({ url }: { url?: string | null }) {
  const navigate = useNavigate()
  const create = useMutation({
    mutationFn: () => request<{ id: string }>('/api/projects', { method: 'POST', body: { source_url: url, language: 'kk' } }),
    onSuccess: (p) => navigate(`/projects/${p.id}`),
  })
  if (!url || !/youtu/.test(url)) return null
  return (
    <>
      <Button size="sm" variant="outline" disabled={create.isPending} onClick={() => create.mutate()}>
        {create.isPending ? 'Создаём…' : 'Создать проект'}
      </Button>
      <ErrorBox error={create.error} />
    </>
  )
}

function IdeaList({ ideas }: { ideas: Idea[] }) {
  return (
    <ul className="grid gap-2">
      {ideas.map((d, i) => (
        <li key={i} className="grid gap-1 rounded-md border bg-paper p-2">
          <div className="flex flex-wrap items-center gap-2">
            {d.priority != null && <Badge tone="ink">{d.priority}</Badge>}
            <b>{d.title_kk}</b>
            <CopyButton text={d.title_kk} label="" aria-label="Копировать" />
          </div>
          <p className="text-xs text-muted-foreground">{d.why_ru}</p>
          {d.source_url && (
            <div className="flex flex-wrap items-center gap-2">
              <a href={d.source_url} target="_blank" rel="noreferrer" className="truncate text-xs text-brand-blue">
                {d.source_url}
              </a>
              <CreateProjectButton url={d.source_url} />
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}

function AnalysisView({ a }: { a: Analysis }) {
  return (
    <div className="grid gap-3 text-sm">
      <p>{a.summary}</p>
      <Section title="Почему работает">
        <ul className="grid gap-1">
          {a.why_it_works.map((w, i) => (
            <li key={i} className="flex gap-2">
              <Badge tone="blue" className="shrink-0">
                {ASPECT[w.aspect] ?? w.aspect}
              </Badge>
              <span>{w.insight}</span>
            </li>
          ))}
        </ul>
      </Section>
      <div className="grid gap-3 md:grid-cols-2">
        <Section title="Формула заголовка">
          <p>{a.title_pattern}</p>
        </Section>
        <Section title="Обложка">
          <p>{a.thumbnail_concept}</p>
        </Section>
        <Section title="Хук (первые секунды)">
          <p>{a.hook}</p>
        </Section>
        <Section title="Что нравится зрителям">
          <p>{a.audience}</p>
        </Section>
      </div>
      <Section title="Что делаем у себя">
        <ul className="list-disc pl-5">
          {a.apply_for_us.map((x, i) => (
            <li key={i}>{x}</li>
          ))}
        </ul>
      </Section>
      {!!a.rules.length && (
        <Section title="Правила для плейбука">
          <ul className="grid gap-1">
            {a.rules.map((r, i) => (
              <li key={i} className="flex gap-2">
                <Badge className="shrink-0">{AREA[r.area] ?? r.area}</Badge>
                <span>{r.rule}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {!!a.video_ideas.length && (
        <Section title="Идеи для нас">
          <IdeaList ideas={a.video_ideas} />
        </Section>
      )}
    </div>
  )
}

function ItemCard({ it }: { it: Item }) {
  const invalidate = useInvalidate()
  const [open, setOpen] = useState(false)
  const [notes, setNotes] = useState(it.notes)
  const [editing, setEditing] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const patch = useMutation({
    mutationFn: (files: File[]) => {
      const fd = new FormData()
      fd.append('notes', notes)
      files.forEach((f) => fd.append('files', f))
      return request<Item>(`/api/growth/items/${it.id}`, { method: 'PATCH', body: fd })
    },
    onSuccess: () => setEditing(false),
    onSettled: invalidate,
  })
  const again = useMutation({
    mutationFn: () => request<Item>(`/api/growth/items/${it.id}/analyze`, { method: 'POST' }),
    onSettled: invalidate,
  })
  const del = useMutation({
    mutationFn: () => request(`/api/growth/items/${it.id}`, { method: 'DELETE' }),
    onSettled: invalidate,
  })
  const st = STATUS[it.status]
  const top = it.info?.top_videos ?? []
  return (
    <Card className="overflow-hidden">
      <div className="grid gap-3 p-3 md:grid-cols-[240px_1fr]">
        <div className="grid content-start gap-1.5">
          {it.images.slice(0, 4).map((src) => (
            <a key={src} href={src} target="_blank" rel="noreferrer">
              <img src={src} alt="" className="w-full rounded border object-cover" loading="lazy" />
            </a>
          ))}
          {!it.images.length && <div className="grid aspect-video place-items-center rounded border bg-muted text-xs text-muted-foreground">нет картинки</div>}
        </div>
        <div className="grid content-start gap-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={st.tone}>{st.label}</Badge>
            <Badge>{it.kind === 'channel' ? 'канал' : it.kind === 'video' ? 'видео' : 'скрин'}</Badge>
            {it.analysis && <Badge tone="ink" title="Сколько можно взять (0–10)">польза {it.analysis.learn_score}/10</Badge>}
            <div className="flex-1" />
            <Button size="sm" variant="ghost" disabled={busy(it.status) || again.isPending} onClick={() => again.mutate()} title="Разобрать заново">
              <RefreshCw className="size-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={del.isPending}
              onClick={() => window.confirm('Удалить пример?') && del.mutate()}
              title="Удалить"
            >
              <Trash2 className="size-4" />
            </Button>
          </div>
          <div className="font-semibold">
            {it.url ? (
              <a href={it.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:underline">
                {it.title || it.url} <ExternalLink className="size-3.5" />
              </a>
            ) : (
              it.title || 'Скрин без ссылки'
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {[
              it.channel,
              it.views != null && `${fmtViews(it.views)} просмотров`,
              it.duration_s && fmtDuration(it.duration_s),
              it.published && fmtDate(it.published),
              it.info?.channel_subscribers != null && `${fmtViews(it.info.channel_subscribers)} подписчиков`,
              it.info?.median_views != null && `медиана ${fmtViews(it.info.median_views)}`,
            ]
              .filter(Boolean)
              .join(' · ')}
          </p>
          {editing ? (
            <div className="grid gap-2">
              <Textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
              <div className="flex gap-2">
                <Button size="sm" disabled={patch.isPending} onClick={() => patch.mutate([])}>
                  Сохранить и разобрать заново
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
                  Отмена
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2 rounded-md bg-brand-yellow/15 px-2 py-1.5">
              <p className="flex-1 whitespace-pre-wrap">{it.notes || <span className="text-muted-foreground">Без комментария</span>}</p>
              <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
                Изменить
              </Button>
              <Button size="sm" variant="ghost" title="Добавить скрины" onClick={() => input.current?.click()}>
                <ImagePlus className="size-4" />
              </Button>
              <input
                ref={input}
                type="file"
                multiple
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={(e) => {
                  const fs = Array.from(e.target.files ?? [])
                  if (fs.length) patch.mutate(fs)
                  e.target.value = ''
                }}
              />
            </div>
          )}
          {!!top.length && (
            <details className="text-xs">
              <summary className="cursor-pointer text-muted-foreground">Топ видео канала ({top.length})</summary>
              <ul className="mt-1 grid gap-0.5">
                {top.map((v) => (
                  <li key={v.url}>
                    <a href={v.url} target="_blank" rel="noreferrer" className="hover:underline">
                      {v.title}
                    </a>{' '}
                    — {fmtViews(v.views)}
                  </li>
                ))}
              </ul>
            </details>
          )}
          {it.error && <p className="text-xs text-brand-red">{it.error}</p>}
          {it.analysis && (
            <>
              <p>{it.analysis.summary}</p>
              <button type="button" className="justify-self-start text-sm font-medium text-brand-blue hover:underline" onClick={() => setOpen(!open)}>
                {open ? 'Свернуть разбор' : 'Открыть разбор'}
              </button>
            </>
          )}
          <ErrorBox error={patch.error ?? again.error ?? del.error} />
        </div>
      </div>
      {open && it.analysis && (
        <div className="border-t bg-paper/60 p-4">
          <AnalysisView a={it.analysis} />
        </div>
      )}
    </Card>
  )
}

// ------------------------------------------------------------------ growth manager panel
function DocChangeRow({ c, applied, onApply, pending }: { c: DocChange; applied: boolean; onApply: () => void; pending: boolean }) {
  const [open, setOpen] = useState(false)
  const label = { update: 'обновить', create: 'создать', delete: 'удалить' }[c.action]
  return (
    <li className="grid gap-1 rounded-md border p-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={c.action === 'delete' ? 'red' : c.action === 'create' ? 'green' : 'blue'}>{label}</Badge>
        <code className="text-xs">{c.path}</code>
        <div className="flex-1" />
        {applied ? (
          <Badge tone="green">применено</Badge>
        ) : (
          <Button size="sm" variant="outline" disabled={pending} onClick={onApply}>
            Применить
          </Button>
        )}
      </div>
      <p className="text-xs text-muted-foreground">{c.reason}</p>
      {c.action !== 'delete' && (
        <>
          <button type="button" className="justify-self-start text-xs text-brand-blue hover:underline" onClick={() => setOpen(!open)}>
            {open ? 'Скрыть текст' : 'Показать новый текст'}
          </button>
          {open && <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded bg-muted p-2 text-xs">{c.content}</pre>}
        </>
      )}
    </li>
  )
}

function SynthesisView({ r }: { r: Report }) {
  const invalidate = useInvalidate()
  const apply = useMutation({
    mutationFn: (paths?: string[]) => request(`/api/growth/reports/${r.id}/apply`, { method: 'POST', body: paths ? { paths } : {} }),
    onSettled: invalidate,
  })
  const d = r.data ?? {}
  const changes = d.doc_changes ?? []
  const applied = new Set(d.applied ?? [])
  const left = changes.filter((c) => !applied.has(c.path))
  return (
    <div className="grid gap-3 text-sm">
      <p className="text-xs text-muted-foreground">{fmtDate(r.created_at)}</p>
      {d.summary && <p>{d.summary}</p>}
      {!!d.film_next?.length && (
        <Section title="Что снимать дальше">
          <IdeaList ideas={d.film_next} />
        </Section>
      )}
      {!!changes.length && (
        <Section title="Изменения в доках">
          <div className="flex items-center gap-2">
            <Button size="sm" variant="accent" disabled={!left.length || apply.isPending} onClick={() => apply.mutate(undefined)}>
              {apply.isPending ? 'Применяем…' : left.length ? `Применить все (${left.length})` : 'Всё применено'}
            </Button>
            <span className="text-xs text-muted-foreground">старые версии сохраняются в data/growth/history</span>
          </div>
          <ul className="grid gap-2">
            {changes.map((c) => (
              <DocChangeRow key={c.path} c={c} applied={applied.has(c.path)} pending={apply.isPending} onApply={() => apply.mutate([c.path])} />
            ))}
          </ul>
          <ErrorBox error={apply.error} />
        </Section>
      )}
    </div>
  )
}

function GrowthPanel({ reports, hasDone }: { reports: Report[]; hasDone: boolean }) {
  const invalidate = useInvalidate()
  const [q, setQ] = useState('')
  const [showPlaybook, setShowPlaybook] = useState(false)
  const playbook = useQuery({
    queryKey: ['growth', 'playbook'],
    queryFn: () => request<{ path: string; text: string }>('/api/growth/playbook'),
  })
  const run = useMutation({
    mutationFn: (body: { kind: 'synthesis' | 'question'; question?: string }) =>
      request<Report>('/api/growth/reports', { method: 'POST', body }),
    onSuccess: (_r, body) => body.kind === 'question' && setQ(''),
    onSettled: invalidate,
  })
  const synth = reports.find((r) => r.kind === 'synthesis')
  const questions = reports.filter((r) => r.kind === 'question')
  return (
    <div className="grid content-start gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="size-5" /> Growth-менеджер
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <p className="text-muted-foreground">
            Сводит все разборы в <b>плейбук</b> (правила, которые ИИ читает перед каждым новым видео), обновляет доки
            (референс-каналы, бэклог тем) и говорит, что снимать дальше.
          </p>
          <Button
            variant="accent"
            disabled={!hasDone || run.isPending || (synth && busy(synth.status))}
            onClick={() => run.mutate({ kind: 'synthesis' })}
          >
            {synth && busy(synth.status) ? 'Думает… (1–3 мин)' : 'Обновить плейбук и доки'}
          </Button>
          {!hasDone && <p className="text-xs text-muted-foreground">Сначала добавь хотя бы один пример.</p>}
          {synth?.status === 'failed' && <p className="text-xs text-brand-red">{synth.error}</p>}
          {synth?.status === 'done' && <SynthesisView r={synth} />}
          <div className="grid gap-1 border-t pt-3">
            <button type="button" className="justify-self-start text-sm font-medium text-brand-blue hover:underline" onClick={() => setShowPlaybook(!showPlaybook)}>
              {showPlaybook ? 'Скрыть плейбук' : 'Открыть текущий плейбук'}
            </button>
            {showPlaybook &&
              (playbook.data?.text ? (
                <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded bg-muted p-2 text-xs">{playbook.data.text}</pre>
              ) : (
                <p className="text-xs text-muted-foreground">Плейбука ещё нет — нажми «Обновить плейбук и доки».</p>
              ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Спросить агента</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <Textarea
            rows={3}
            placeholder="Например: что снять на этой неделе? какая обложка лучше для темы про сон? почему у PsychToons такие просмотры?"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <Button disabled={!q.trim() || run.isPending} onClick={() => run.mutate({ kind: 'question', question: q.trim() })}>
            Спросить
          </Button>
          <ErrorBox error={run.error} />
          {questions.map((r) => (
            <div key={r.id} className="grid gap-1 rounded-md border p-2">
              <p className="font-medium">{r.question}</p>
              {busy(r.status) && <p className="text-xs text-muted-foreground">Думает…</p>}
              {r.status === 'failed' && <p className="text-xs text-brand-red">{r.error}</p>}
              {r.data?.answer_md && <div className="whitespace-pre-wrap">{r.data.answer_md}</div>}
              {!!r.data?.film_next?.length && <IdeaList ideas={r.data.film_next} />}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

// ------------------------------------------------------------------ page
export default function CompetitorsPage() {
  const items = useQuery({
    queryKey: ['growth', 'items'],
    queryFn: () => request<Item[]>('/api/growth/items'),
    refetchInterval: (q) => ((q.state.data ?? []).some((i) => busy(i.status)) ? 3000 : false),
  })
  const reports = useQuery({
    queryKey: ['growth', 'reports'],
    queryFn: () => request<Report[]>('/api/growth/reports'),
    refetchInterval: (q) => ((q.state.data ?? []).some((r) => busy(r.status)) ? 3000 : false),
  })
  const list = items.data ?? []
  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Анализ конкурентов</h1>
        <p className="text-sm text-muted-foreground">
          Скидывай удачные видео и каналы со своим комментарием — ИИ разберёт, почему они заходят, и превратит это в
          правила для наших следующих видео.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_420px]">
        <div className={cn('grid content-start gap-4')}>
          <AddForm />
          {items.isLoading ? (
            <Loading />
          ) : items.isError ? (
            <ErrorBox error={items.error} />
          ) : list.length ? (
            list.map((it) => <ItemCard key={it.id} it={it} />)
          ) : (
            <Empty>Пока пусто. Добавь первое видео, которое тебе понравилось.</Empty>
          )}
          {list.some((i) => i.status === 'failed') && (
            <Notice>Если видео не скачалось — добавь скрин обложки и комментарий без ссылки, разбор всё равно сработает.</Notice>
          )}
        </div>
        <GrowthPanel reports={reports.data ?? []} hasDone={list.some((i) => i.status === 'done')} />
      </div>
    </div>
  )
}
