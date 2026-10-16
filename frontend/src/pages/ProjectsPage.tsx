import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, unwrap, type ProjectCreate } from '@/api/client'
import { useProjects, useSettings } from '@/api/hooks'
import { Empty, ErrorBox, Loading } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label, Select, Textarea } from '@/components/ui/input'
import { DURATION_OPTIONS, PROJECT_STATUS, stepTitle } from '@/lib/steps'
import { cn, fmtDate, fmtDuration, fmtUsd } from '@/lib/utils'

function NewProjectForm({ onClose }: { onClose: () => void }) {
  const settings = useSettings()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [mode, setMode] = useState<'url' | 'text'>('url')
  const [url, setUrl] = useState('')
  const [text, setText] = useState('')
  const [title, setTitle] = useState('')
  const [seconds, setSeconds] = useState<number | null>(null)
  const [sponsored, setSponsored] = useState(false)
  const target = seconds ?? settings.data?.target_seconds ?? 240

  const create = useMutation({
    mutationFn: (body: ProjectCreate) => unwrap(api.POST('/api/projects', { body })),
    onSuccess: (p) => {
      void qc.invalidateQueries({ queryKey: ['projects'] })
      navigate(`/projects/${p.id}`)
    },
  })

  const textTooShort = mode === 'text' && text.trim().length < 200
  const canSubmit = (mode === 'url' ? /^https?:\/\/\S+$/.test(url.trim()) : !textTooShort) && !create.isPending

  return (
    <Card className="mb-6">
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Новое видео</CardTitle>
        <Button variant="ghost" size="icon" aria-label="Закрыть" onClick={onClose}>
          <X />
        </Button>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault()
            if (!canSubmit) return
            create.mutate({
              ...(mode === 'url' ? { source_url: url.trim() } : { transcript: text.trim() }),
              ...(title.trim() ? { title: title.trim() } : {}),
              target_seconds: target,
              sponsored,
            })
          }}
        >
          <div className="inline-flex w-fit rounded-md border bg-muted p-0.5" role="tablist">
            {(
              [
                ['url', 'Ссылка YouTube'],
                ['text', 'Вставить текст'],
              ] as const
            ).map(([m, l]) => (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={mode === m}
                onClick={() => setMode(m)}
                className={cn(
                  'rounded px-3 py-1 text-sm font-medium',
                  mode === m ? 'bg-paper shadow-sm' : 'text-muted-foreground',
                )}
              >
                {l}
              </button>
            ))}
          </div>

          {mode === 'url' ? (
            <div className="grid gap-1.5">
              <Label htmlFor="np-url">Ссылка на видео-источник</Label>
              <Input
                id="np-url"
                placeholder="https://www.youtube.com/watch?v=…"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Берите свежие «залетевшие» видео (не старше ~2 лет). Если транскрипт не скачается — вставите текст вручную на шаге 1.
              </p>
            </div>
          ) : (
            <div className="grid gap-1.5">
              <Label htmlFor="np-text">Транскрипт источника</Label>
              <Textarea id="np-text" rows={8} value={text} onChange={(e) => setText(e.target.value)} />
              <p className={cn('text-xs', textTooShort ? 'text-brand-red' : 'text-muted-foreground')}>
                {text.trim().length} символов (минимум 200)
              </p>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-[1fr_auto_auto] sm:items-end">
            <div className="grid gap-1.5">
              <Label htmlFor="np-title">Рабочее название (необязательно)</Label>
              <Input id="np-title" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="np-dur">Длительность</Label>
              <Select id="np-dur" value={target} onChange={(e) => setSeconds(Number(e.target.value))}>
                {DURATION_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {fmtDuration(s)} мин
                  </option>
                ))}
              </Select>
            </div>
            <label className="flex h-9 items-center gap-2 text-sm">
              <input type="checkbox" checked={sponsored} onChange={(e) => setSponsored(e.target.checked)} />
              Спонсорское
            </label>
          </div>

          <ErrorBox error={create.error} />
          <div>
            <Button type="submit" variant="accent" disabled={!canSubmit}>
              {create.isPending ? 'Создаём…' : 'Создать и запустить шаг 1'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export default function ProjectsPage() {
  const projects = useProjects()
  const [creating, setCreating] = useState(false)
  const [showArchived, setShowArchived] = useState(false)
  const list = (projects.data ?? []).filter((p) => showArchived || p.status !== 'archived')

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">Проекты</h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
            Показать архив
          </label>
          {!creating && (
            <Button variant="accent" onClick={() => setCreating(true)}>
              <Plus /> Новое видео
            </Button>
          )}
        </div>
      </div>

      {creating && <NewProjectForm onClose={() => setCreating(false)} />}

      {projects.isLoading ? (
        <Loading />
      ) : projects.isError ? (
        <ErrorBox error={projects.error} />
      ) : list.length === 0 ? (
        <Empty>Проектов пока нет. Нажмите «Новое видео» и вставьте ссылку на видео-источник.</Empty>
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-medium">Название</th>
                <th className="px-4 py-2.5 font-medium">Статус</th>
                <th className="px-4 py-2.5 font-medium">Шаг</th>
                <th className="px-4 py-2.5 text-right font-medium">Длительность</th>
                <th className="px-4 py-2.5 text-right font-medium">Стоимость</th>
                <th className="px-4 py-2.5 text-right font-medium">Создан</th>
              </tr>
            </thead>
            <tbody>
              {list.map((p) => {
                const st = PROJECT_STATUS[p.status]
                return (
                  <tr key={p.id} className="border-b last:border-0 hover:bg-muted/40">
                    <td className="px-4 py-2.5">
                      <Link to={`/projects/${p.id}`} className="font-medium hover:text-brand-red hover:underline">
                        {p.title || 'Без названия'}
                      </Link>
                      {p.source_url && (
                        <div className="max-w-md truncate text-xs text-muted-foreground">{p.source_url}</div>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge tone={st.tone}>{st.label}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">{p.current_step ? stepTitle(p.current_step) : '—'}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {p.duration != null ? (
                        fmtDuration(p.duration)
                      ) : (
                        <span className="text-muted-foreground" title="Целевая длительность">
                          ~{fmtDuration(p.target_seconds)}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {fmtUsd(p.cost_usd)}
                      {p.budget_usd != null && <span className="text-muted-foreground"> / {fmtUsd(p.budget_usd)}</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right text-muted-foreground">{fmtDate(p.created_at)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
