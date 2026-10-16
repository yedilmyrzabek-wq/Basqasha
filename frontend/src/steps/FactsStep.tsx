import { useMutation, useQuery } from '@tanstack/react-query'
import { ExternalLink, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { api, unwrap, type Fact, type FactRow } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject } from '@/api/hooks'
import { Empty, ErrorBox, Loading, Notice } from '@/components/common'
import { Badge, type BadgeTone } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, Label, Select, Textarea } from '@/components/ui/input'
import { isNotFound, type StepViewProps } from './types'

const STATUS: Record<Fact['status'], { label: string; tone: BadgeTone }> = {
  verified: { label: 'проверен', tone: 'green' },
  unverified: { label: 'не проверен', tone: 'yellow' },
  conflicting: { label: 'противоречит', tone: 'red' },
  rejected: { label: 'отклонён', tone: 'neutral' },
}

function onScreenProblem(f: Fact): string | null {
  if (!f.on_screen) return null
  if (f.status !== 'verified') return 'На экран — только проверенные факты'
  if (f.sources.length < 2) return 'На экран — нужно ≥ 2 источника'
  if (!f.sources.some((s) => s.is_primary)) return 'На экран — нужен ≥ 1 первичный источник'
  return null
}

function nextFactId(rows: FactRow[]): string {
  const nums = rows.map((r) => Number(r.fact.id.slice(1))).filter((n) => !Number.isNaN(n))
  return `f${String((nums.length ? Math.max(...nums) : 0) + 1).padStart(2, '0')}`
}

function FactEditor({
  initial,
  pending,
  error,
  onSave,
  onCancel,
}: {
  initial: Fact
  pending: boolean
  error: unknown
  onSave: (f: Fact) => void
  onCancel: () => void
}) {
  const [f, setF] = useState<Fact>(initial)
  const problem = onScreenProblem(f)
  const clean = (): Fact => ({
    id: f.id,
    claim: f.claim.trim(),
    value: f.value?.trim() ? f.value.trim() : null,
    status: f.status,
    sources: f.sources
      .filter((s) => s.url.trim())
      .map((s) => ({ url: s.url.trim(), is_primary: !!s.is_primary, ...(s.title?.trim() ? { title: s.title.trim() } : {}) })),
    on_screen: !!f.on_screen,
    ...(f.note?.trim() ? { note: f.note.trim() } : {}),
  })
  return (
    <div className="grid gap-3 bg-muted/30 p-3">
      <div className="grid gap-3 md:grid-cols-[1fr_180px_160px]">
        <div className="grid gap-1.5">
          <Label>Утверждение</Label>
          <Textarea rows={2} value={f.claim} onChange={(e) => setF({ ...f, claim: e.target.value })} />
        </div>
        <div className="grid gap-1.5">
          <Label>Значение (число/дата)</Label>
          <Input value={f.value ?? ''} onChange={(e) => setF({ ...f, value: e.target.value })} />
        </div>
        <div className="grid gap-1.5">
          <Label>Статус</Label>
          <Select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value as Fact['status'] })}>
            {Object.entries(STATUS).map(([k, v]) => (
              <option key={k} value={k}>
                {v.label}
              </option>
            ))}
          </Select>
        </div>
      </div>
      <div className="grid gap-1.5">
        <Label>Источники</Label>
        {f.sources.map((s, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2">
            <Input
              className="min-w-64 flex-[2]"
              placeholder="https://…"
              value={s.url}
              onChange={(e) => setF({ ...f, sources: f.sources.map((x, j) => (j === i ? { ...x, url: e.target.value } : x)) })}
            />
            <Input
              className="min-w-40 flex-1"
              placeholder="Название"
              value={s.title ?? ''}
              onChange={(e) => setF({ ...f, sources: f.sources.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)) })}
            />
            <label className="flex items-center gap-1.5 text-sm" title="gov.kz, stat.gov.kz, ООН/Всемирный банк, рецензируемые статьи">
              <input
                type="checkbox"
                checked={!!s.is_primary}
                onChange={(e) =>
                  setF({ ...f, sources: f.sources.map((x, j) => (j === i ? { ...x, is_primary: e.target.checked } : x)) })
                }
              />
              первичный
            </label>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Удалить источник"
              onClick={() => setF({ ...f, sources: f.sources.filter((_, j) => j !== i) })}
            >
              <X />
            </Button>
          </div>
        ))}
        <div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setF({ ...f, sources: [...f.sources, { url: '', is_primary: false }] })}
          >
            <Plus /> Источник
          </Button>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
        <div className="grid gap-1.5">
          <Label>Заметка</Label>
          <Input value={f.note ?? ''} onChange={(e) => setF({ ...f, note: e.target.value })} />
        </div>
        <label className="flex h-9 items-center gap-2 text-sm">
          <input type="checkbox" checked={!!f.on_screen} onChange={(e) => setF({ ...f, on_screen: e.target.checked })} />
          Показывать цифру на экране
        </label>
      </div>
      {problem && <Notice>{problem}</Notice>}
      <ErrorBox error={error} />
      <div className="flex gap-2">
        <Button size="sm" disabled={pending || f.claim.trim().length < 3 || !!problem} onClick={() => onSave(clean())}>
          Сохранить
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Отмена
        </Button>
      </div>
    </div>
  )
}

export default function FactsStep({ project, state }: StepViewProps) {
  const id = project.id
  const invalidate = useInvalidateProject(id)
  const facts = useQuery({
    queryKey: [...projectKey(id), 'facts', stepVersionKey(project, 'facts')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/facts', { params: { path: { projectId: id } } })),
    retry: false,
  })
  const [editing, setEditing] = useState<string | null>(null) // row id or 'new'

  const save = useMutation({
    mutationFn: ({ rowId, fact }: { rowId: string; fact: Fact }) =>
      rowId === 'new'
        ? unwrap(api.POST('/api/projects/{projectId}/facts', { params: { path: { projectId: id } }, body: fact }))
        : unwrap(
            api.PUT('/api/projects/{projectId}/facts/{factId}', {
              params: { path: { projectId: id, factId: rowId } },
              body: fact,
            }),
          ),
    onSuccess: () => setEditing(null),
    onSettled: invalidate,
  })
  const remove = useMutation({
    mutationFn: (factId: string) =>
      unwrap(api.DELETE('/api/projects/{projectId}/facts/{factId}', { params: { path: { projectId: id, factId } } })),
    onSettled: invalidate,
  })

  if (facts.isLoading) return <Loading />
  if (facts.isError && !isNotFound(facts.error)) return <ErrorBox error={facts.error} />
  const rows = facts.data ?? []
  const counts = rows.reduce<Record<string, number>>((acc, r) => ({ ...acc, [r.fact.status]: (acc[r.fact.status] ?? 0) + 1 }), {})

  return (
    <div className="grid gap-3">
      {rows.length === 0 && editing !== 'new' ? (
        <Empty>{state.status === 'running' ? 'Ищем и проверяем факты…' : 'Фактов пока нет.'}</Empty>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted-foreground">Всего {rows.length}:</span>
            {Object.entries(STATUS).map(([k, v]) =>
              counts[k] ? (
                <Badge key={k} tone={v.tone}>
                  {v.label}: {counts[k]}
                </Badge>
              ) : null,
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Непроверенные, спорные и отклонённые факты не используются как цифры в сценарии. Правка фактов делает сценарий
            устаревшим.
          </p>
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">ID</th>
                  <th className="px-3 py-2 font-medium">Утверждение</th>
                  <th className="px-3 py-2 font-medium">Значение</th>
                  <th className="px-3 py-2 font-medium">Статус</th>
                  <th className="px-3 py-2 font-medium">Источники</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) =>
                  editing === r.id ? (
                    <tr key={r.id} className="border-b">
                      <td colSpan={6}>
                        <FactEditor
                          initial={r.fact}
                          pending={save.isPending}
                          error={save.error}
                          onSave={(fact) => save.mutate({ rowId: r.id, fact })}
                          onCancel={() => setEditing(null)}
                        />
                      </td>
                    </tr>
                  ) : (
                    <tr key={r.id} className="border-b align-top last:border-0">
                      <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{r.fact.id}</td>
                      <td className="px-3 py-2">
                        {r.fact.claim}
                        {r.fact.note && <div className="mt-0.5 text-xs text-muted-foreground">{r.fact.note}</div>}
                        {r.edited_by_operator && <div className="mt-0.5 text-xs text-brand-blue">изменён вручную</div>}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {r.fact.value ?? '—'}
                        {r.fact.on_screen && (
                          <div>
                            <Badge tone="ink" className="mt-1">
                              на экране
                            </Badge>
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <Badge tone={STATUS[r.fact.status].tone}>{STATUS[r.fact.status].label}</Badge>
                      </td>
                      <td className="px-3 py-2">
                        <ul className="space-y-0.5">
                          {r.fact.sources.map((s, i) => (
                            <li key={i} className="max-w-xs truncate">
                              <a
                                href={s.url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-brand-blue hover:underline"
                                title={s.url}
                              >
                                <ExternalLink className="size-3 shrink-0" />
                                {s.title || new URL(s.url, 'http://x').hostname}
                              </a>
                              {s.is_primary && <span className="ml-1 text-xs text-[#2b7a44]">первичный</span>}
                            </li>
                          ))}
                          {r.fact.sources.length === 0 && <li className="text-muted-foreground">—</li>}
                        </ul>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" aria-label="Изменить" onClick={() => setEditing(r.id)}>
                            <Pencil />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Удалить"
                            disabled={remove.isPending}
                            onClick={() => window.confirm(`Удалить факт ${r.fact.id}?`) && remove.mutate(r.id)}
                          >
                            <Trash2 />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
      <ErrorBox error={remove.error} />
      {editing === 'new' ? (
        <div className="rounded-md border">
          <FactEditor
            initial={{ id: nextFactId(rows), claim: '', value: null, status: 'unverified', sources: [], on_screen: false }}
            pending={save.isPending}
            error={save.error}
            onSave={(fact) => save.mutate({ rowId: 'new', fact })}
            onCancel={() => setEditing(null)}
          />
        </div>
      ) : (
        <div>
          <Button variant="outline" size="sm" onClick={() => setEditing('new')}>
            <Plus /> Добавить факт
          </Button>
        </div>
      )}
    </div>
  )
}
