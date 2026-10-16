import { useMutation, useQuery } from '@tanstack/react-query'
import { CheckCircle2 } from 'lucide-react'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, unwrap, type Schemas } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject, useSettings } from '@/api/hooks'
import { Empty, ErrorBox, Loading, Notice } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/input'
import { cn, countWords, fmtDuration } from '@/lib/utils'
import { isNotFound, type StepViewProps } from './types'

type Script = Schemas['Script']
type Flagged = NonNullable<NonNullable<Script['originality']>['flagged_sentences']>[number]

const VERDICT = {
  pass: { label: 'Оригинально', tone: 'green' },
  pass_after_rewrite: { label: 'Оригинально после переписывания', tone: 'green' },
  fail: { label: 'Слишком похоже на источник', tone: 'red' },
} as const

const WRITER: Record<string, string> = { gemini: 'Gemini', claude_code: 'Claude Code', operator: 'оператор' }

function readDraft(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeDraft(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    /* storage unavailable — drafts just won't persist */
  }
}

/** Wraps every occurrence of the flagged sentences in <mark>. */
function highlight(text: string, needles: string[]): ReactNode[] {
  const ranges: [number, number][] = []
  for (const n of needles) {
    const t = n.trim()
    if (!t) continue
    let i = text.indexOf(t)
    while (i >= 0) {
      ranges.push([i, i + t.length])
      i = text.indexOf(t, i + t.length)
    }
  }
  ranges.sort((a, b) => a[0] - b[0])
  const out: ReactNode[] = []
  let pos = 0
  ranges.forEach(([s, e], k) => {
    if (s < pos) return
    out.push(text.slice(pos, s))
    out.push(
      <mark key={k} className="rounded bg-brand-red/20 px-0.5 text-ink">
        {text.slice(s, e)}
      </mark>,
    )
    pos = e
  })
  out.push(text.slice(pos))
  return out
}

function ScriptEditor({ project, script, waiting }: { project: StepViewProps['project']; script: Script; waiting: boolean }) {
  const id = project.id
  const invalidate = useInvalidateProject(id)
  const settings = useSettings()
  // Unsaved edits survive switching steps / reloads (per project + version).
  const draftKey = `script-draft:${id}:${script.version ?? 0}`
  const [text, setTextState] = useState(() => readDraft(draftKey) ?? script.text ?? '')
  const dirty = text !== (script.text ?? '')
  const setText = (v: string) => {
    setTextState(v)
    writeDraft(draftKey, v === (script.text ?? '') ? null : v)
  }
  useEffect(() => {
    if (!dirty) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  const wpm = project.wpm_voice ?? settings.data?.wpm_voice ?? 110
  const target = script.target_words ?? project.target_words ?? Math.round((wpm * project.target_seconds) / 60)
  const words = useMemo(() => countWords(text), [text])
  const est = (words / wpm) * 60
  const deviation = target ? (words - target) / target : 0
  const within = Math.abs(deviation) <= 0.08
  const threshold = settings.data?.similarity_threshold ?? 0.8
  const flagged: Flagged[] = script.originality?.flagged_sentences ?? []

  const save = useMutation({
    mutationFn: () =>
      unwrap(
        api.PUT('/api/projects/{projectId}/script', {
          params: { path: { projectId: id } },
          body: { text, version: script.version ?? 0 },
        }),
      ),
    onSuccess: () => writeDraft(draftKey, null),
    onSettled: invalidate,
  })
  const approve = useMutation({
    mutationFn: async () => {
      if (dirty) await save.mutateAsync()
      return unwrap(api.POST('/api/projects/{projectId}/script/approve', { params: { path: { projectId: id } } }))
    },
    onSettled: invalidate,
  })

  const o = script.originality
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-md border bg-paper px-4 py-2.5 text-sm">
        <span>
          Версия <b>{script.version ?? '—'}</b>
        </span>
        {script.data?.writer && (
          <span className="text-muted-foreground">
            Автор: {WRITER[script.data.writer.kind] ?? script.data.writer.kind}
            {script.data.writer.model ? ` (${script.data.writer.model})` : ''}
          </span>
        )}
        <span className={cn('tabular-nums', within ? 'text-[#2b7a44]' : 'font-semibold text-brand-red')}>
          {words} слов из {target} ({deviation >= 0 ? '+' : ''}
          {Math.round(deviation * 100)}%, допуск ±8%)
        </span>
        <span className="tabular-nums">
          ≈ {fmtDuration(est)} <span className="text-muted-foreground">при {Math.round(wpm)} сл/мин</span>
        </span>
        <span className="text-muted-foreground">цель {fmtDuration(project.target_seconds)}</span>
        {script.approved && !dirty && (
          <Badge tone="green">
            <CheckCircle2 className="size-3" /> Утверждён
          </Badge>
        )}
        {dirty && <Badge tone="yellow">Есть несохранённые правки</Badge>}
      </div>

      <Textarea
        aria-label="Текст сценария"
        className="min-h-[24rem] font-[inherit] text-[15px]"
        value={text}
        onChange={(e) => setText(e.target.value)}
        spellCheck={false}
        lang={project.language}
      />

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? 'Сохраняем…' : 'Сохранить'}
        </Button>
        <Button
          variant={waiting ? 'accent' : 'default'}
          disabled={approve.isPending || !text.trim()}
          onClick={() => approve.mutate()}
          title="Повторно проверит похожесть отредактированного текста и запустит шаг 5"
        >
          {approve.isPending ? 'Проверяем…' : 'Утвердить'}
        </Button>
        {dirty && (
          <Button variant="ghost" onClick={() => setText(script.text ?? '')}>
            Отменить правки
          </Button>
        )}
        {script.llm_draft && script.llm_draft !== text && (
          <Button variant="ghost" onClick={() => setText(script.llm_draft ?? '')}>
            Вернуть черновик ИИ
          </Button>
        )}
      </div>
      <ErrorBox error={save.error ?? approve.error} />
      {!within && words > 0 && (
        <Notice>
          Длина вне допуска: нужно {Math.round(target * 0.92)}–{Math.round(target * 1.08)} слов. Утвердить можно, но длительность
          видео будет отличаться от цели.
        </Notice>
      )}

      <div className="grid gap-3 rounded-md border p-4">
        <div className="flex flex-wrap items-center gap-3">
          <h3 className="font-semibold">Отчёт о похожести</h3>
          {o ? (
            <>
              {o.verdict && <Badge tone={VERDICT[o.verdict].tone}>{VERDICT[o.verdict].label}</Badge>}
              {o.max_similarity != null && (
                <span className={cn('text-sm tabular-nums', o.max_similarity >= threshold && 'font-semibold text-brand-red')}>
                  макс. похожесть {o.max_similarity.toFixed(2)} (порог {threshold.toFixed(2)})
                </span>
              )}
            </>
          ) : (
            <span className="text-sm text-muted-foreground">ещё не проверялся</span>
          )}
        </div>
        {flagged.length > 0 && (
          <>
            <ul className="grid gap-2 text-sm">
              {flagged.map((f, i) => (
                <li key={i} className="rounded-md border-l-4 border-brand-red bg-brand-red/5 px-3 py-2">
                  <div className="flex items-start justify-between gap-3">
                    <span>
                      <span className="text-muted-foreground">#{f.index}</span> {f.text}
                    </span>
                    {f.similarity != null && <Badge tone="red">{f.similarity.toFixed(2)}</Badge>}
                  </div>
                  {f.source_excerpt && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      Источник: «{f.source_excerpt}»
                    </div>
                  )}
                </li>
              ))}
            </ul>
            <details>
              <summary className="cursor-pointer text-sm text-muted-foreground">Текст с подсветкой похожих фраз</summary>
              <div className="mt-2 whitespace-pre-wrap rounded-md bg-paper p-3 text-sm leading-relaxed">
                {highlight(text, flagged.map((f) => f.text ?? ''))}
              </div>
            </details>
          </>
        )}
        {o && flagged.length === 0 && <p className="text-sm text-muted-foreground">Похожих фраз не найдено.</p>}
      </div>
    </div>
  )
}

export default function ScriptStep({ project, state }: StepViewProps) {
  const id = project.id
  const script = useQuery({
    queryKey: [...projectKey(id), 'script', stepVersionKey(project, 'script')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/script', { params: { path: { projectId: id } } })),
    retry: false,
  })
  if (script.isLoading) return <Loading />
  if (script.isError && !isNotFound(script.error)) return <ErrorBox error={script.error} />
  const s = script.data
  if (!s || s.text == null)
    return <Empty>{state.status === 'running' ? 'Пишем сценарий и проверяем похожесть…' : 'Сценария пока нет.'}</Empty>
  return (
    <ScriptEditor
      key={`${s.version}:${s.approved}`}
      project={project}
      script={s}
      waiting={state.wait_reason === 'approve_script'}
    />
  )
}
