import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, CircleDashed, XCircle } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { api, unwrap, type Settings as ApiSettings } from '@/api/client'
import { useHealth, useSettings } from '@/api/hooks'
import { ErrorBox, Loading } from '@/components/common'
import { MinutesInput } from '@/components/MinutesInput'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label, Select, Textarea } from '@/components/ui/input'
import { cn, fmtDate, fmtUsd } from '@/lib/utils'

type Claude = { script: string; text: string; cheap: string; effort: string }
type Settings = ApiSettings & {
  claude?: Claude
  image_source?: 'gemini' | 'manual' | 'samples'
  backgrounds_count?: number
}
type Models = {
  claude: { id: string; label: string }[]
  claude_effort: string[]
  gemini: { text: string[]; image: string[]; embed: string[] }
  gemini_error?: string | null
}
type Mode = Settings['script_writer']

function Field({ label, hint, children, htmlFor }: { label: string; hint?: string; children: ReactNode; htmlFor: string }) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

/** Dropdown of available models; the current value is kept even if the list does not have it. */
function ModelSelect({
  id,
  value,
  options,
  onChange,
}: {
  id: string
  value: string
  options: { id: string; label?: string }[]
  onChange: (v: string) => void
}) {
  const all = options.some((o) => o.id === value) || !value ? options : [{ id: value, label: `${value} (текущая)` }, ...options]
  return (
    <Select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
      {all.map((o) => (
        <option key={o.id} value={o.id}>
          {o.label ?? o.id}
        </option>
      ))}
    </Select>
  )
}

function Status({ ok, label }: { ok: boolean | undefined; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm">
      {ok === undefined ? (
        <CircleDashed className="size-4 text-muted-foreground" />
      ) : ok ? (
        <CheckCircle2 className="size-4 text-brand-green" />
      ) : (
        <XCircle className="size-4 text-brand-red" />
      )}
      {label}
    </span>
  )
}

const IMAGE_SOURCES: { v: NonNullable<Settings['image_source']>; label: string }[] = [
  { v: 'gemini', label: 'Gemini API — генерирует сам (≈ $0.05 за фон)' },
  { v: 'manual', label: 'Вручную — система пишет промпты, я делаю в Google Flow и загружаю' },
  { v: 'samples', label: 'Тестовые фоны из библиотеки (для проверки, не для публикации)' },
]

function ImagesBlock({ s, setS, models }: { s: Settings; setS: (s: Settings) => void; models?: Models }) {
  const src = s.image_source ?? 'gemini'
  return (
    <div className="grid gap-4 rounded-md border p-3 md:grid-cols-2">
      <Field label="Фоны (картинки)" htmlFor="image-source">
        <Select id="image-source" value={src} onChange={(e) => setS({ ...s, image_source: e.target.value as Settings['image_source'] })}>
          {IMAGE_SOURCES.map((o) => (
            <option key={o.v} value={o.v}>
              {o.label}
            </option>
          ))}
        </Select>
      </Field>
      {src === 'gemini' && (
        <Field label="Модель картинок (Gemini)" htmlFor="m-image" hint="Проверка готовой картинки — дешёвой моделью Gemini">
          <ModelSelect
            id="m-image"
            value={s.models?.image ?? ''}
            options={(models?.gemini.image ?? []).map((id) => ({ id }))}
            onChange={(v) => setS({ ...s, models: { ...s.models!, image: v } })}
          />
        </Field>
      )}
      {src === 'manual' && (
        <p className="self-end text-xs text-muted-foreground">
          На шаге «Картинки» появятся английские промпты для каждого фона (уже со стилем): копируешь в Google Flow, потом
          загружаешь картинки пачкой — как mp3 на шаге «Озвучка». Gemini не тратится.
        </p>
      )}
    </div>
  )
}

function ClaudeTab({ s, setS, models }: { s: Settings; setS: (s: Settings) => void; models?: Models }) {
  const c = s.claude ?? { script: 'claude-opus-5-5', text: 'sonnet', cheap: 'haiku', effort: 'medium' }
  const set = (k: keyof Claude) => (v: string) => setS({ ...s, claude: { ...c, [k]: v } })
  const opts = models?.claude ?? []
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">
        Все тексты — идея, факты, сценарий, проверка оригинальности, раскадровка, метаданные — пишет Claude через{' '}
        <code>claude -p</code> по подписке ($0). Gemini используется только для картинок (если выбран ниже).
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Идея и сценарий" htmlFor="c-script" hint="Самое важное — лучше Opus">
          <ModelSelect id="c-script" value={c.script} options={opts} onChange={set('script')} />
        </Field>
        <Field label="Усилие (effort) для сценария" htmlFor="c-effort" hint="medium — баланс скорости и качества">
          <Select id="c-effort" value={c.effort} onChange={(e) => set('effort')(e.target.value)}>
            {(models?.claude_effort ?? ['low', 'medium', 'high', 'xhigh', 'max']).map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Факты, раскадровка, судья оригинальности, метаданные" htmlFor="c-text">
          <ModelSelect id="c-text" value={c.text} options={opts} onChange={set('text')} />
        </Field>
        <Field label="Быстрые проверки" htmlFor="c-cheap">
          <ModelSelect id="c-cheap" value={c.cheap} options={opts} onChange={set('cheap')} />
        </Field>
      </div>
      <ImagesBlock s={s} setS={setS} models={models} />
    </div>
  )
}

function GeminiTab({ s, setS, models }: { s: Settings; setS: (s: Settings) => void; models?: Models }) {
  const m = s.models!
  const set = (k: keyof NonNullable<Settings['models']>) => (v: string) => setS({ ...s, models: { ...m, [k]: v } })
  const text = (models?.gemini.text ?? []).map((id) => ({ id }))
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">Всё через Gemini API (платно, по токенам): тексты, поиск фактов, эмбеддинги и картинки.</p>
      {models?.gemini_error && <p className="text-xs text-brand-red">Список моделей Gemini не загрузился: {models.gemini_error}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Идея и сценарий" htmlFor="g-script">
          <ModelSelect id="g-script" value={m.script} options={text} onChange={set('script')} />
        </Field>
        <Field label="Факты, раскадровка, метаданные" htmlFor="g-text">
          <ModelSelect id="g-text" value={m.text} options={text} onChange={set('text')} />
        </Field>
        <Field label="Дешёвая (проверки)" htmlFor="g-cheap">
          <ModelSelect id="g-cheap" value={m.cheap} options={text} onChange={set('cheap')} />
        </Field>
        <Field label="Эмбеддинги (похожесть)" htmlFor="g-embed">
          <ModelSelect
            id="g-embed"
            value={m.embed}
            options={(models?.gemini.embed ?? []).map((id) => ({ id }))}
            onChange={set('embed')}
          />
        </Field>
      </div>
      <ImagesBlock s={s} setS={setS} models={models} />
    </div>
  )
}

function SettingsForm({ initial }: { initial: Settings }) {
  const qc = useQueryClient()
  const [s, setS] = useState<Settings>(initial)
  const [tab, setTab] = useState<Mode>(initial.script_writer)
  const models = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const r = await fetch('/api/models')
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      return (await r.json()) as Models
    },
    staleTime: 3600_000,
  })
  const num = (k: keyof Settings) => (e: React.ChangeEvent<HTMLInputElement>) => setS({ ...s, [k]: Number(e.target.value) })
  const save = useMutation({
    mutationFn: () => {
      const { keys: _keys, ...body } = s
      return unwrap(api.PUT('/api/settings', { body: body as ApiSettings }))
    },
    onSuccess: (data) => qc.setQueryData(['settings'], data),
  })
  const targetWords = Math.round((s.wpm_voice * s.target_seconds) / 60)
  const bg = Number(s.backgrounds_count ?? 30)
  const TABS: { v: Mode; label: string }[] = [
    { v: 'claude_code', label: 'Claude CLI (подписка)' },
    { v: 'gemini', label: 'Gemini API' },
  ]

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
    >
      <Card>
        <CardHeader>
          <CardTitle>Кто делает тексты</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="flex flex-wrap items-center gap-2">
            {TABS.map((t) => (
              <button
                key={t.v}
                type="button"
                onClick={() => setTab(t.v)}
                className={cn(
                  'rounded-md border px-4 py-2 text-sm font-medium',
                  tab === t.v ? 'border-ink bg-ink text-paper' : 'bg-paper hover:bg-muted',
                )}
              >
                {t.label}
                {s.script_writer === t.v && <span className="ml-2 text-xs opacity-80">● используется</span>}
              </button>
            ))}
          </div>
          {s.script_writer !== tab && (
            <div className="flex flex-wrap items-center gap-3 rounded-md border border-brand-yellow/60 bg-brand-yellow/15 p-2 text-sm">
              Сейчас используется {TABS.find((t) => t.v === s.script_writer)?.label}.
              <Button type="button" size="sm" variant="accent" onClick={() => setS({ ...s, script_writer: tab })}>
                Использовать {TABS.find((t) => t.v === tab)?.label}
              </Button>
              <span className="text-xs text-muted-foreground">и нажми «Сохранить настройки»</span>
            </div>
          )}
          {tab === 'claude_code' ? (
            <ClaudeTab s={s} setS={setS} models={models.data} />
          ) : (
            <GeminiTab s={s} setS={setS} models={models.data} />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Стиль картинок</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <Field label="STYLE SUFFIX — добавляется к каждому промпту фона" htmlFor="style">
            <Textarea
              id="style"
              rows={6}
              className="font-mono text-xs"
              value={s.style_suffix ?? ''}
              onChange={(e) => setS({ ...s, style_suffix: e.target.value })}
            />
          </Field>
          <Field
            label="Количество разных фонов на видео"
            htmlFor="bg-count"
            hint={`≈ $${(bg * 0.053).toFixed(2)} на видео через Gemini (≈ $0.05 за фон), вручную — бесплатно. Не больше числа сцен (~1 сцена на 5 с).`}
          >
            <Input
              id="bg-count"
              type="number"
              min={4}
              max={300}
              step={1}
              value={bg}
              onChange={(e) => setS({ ...s, backgrounds_count: Number(e.target.value) })}
            />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Длительность и проверки</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Field label="Длительность по умолчанию" htmlFor="dur" hint={`≈ ${targetWords} слов. Любая: от 1 до 60 минут`}>
            <MinutesInput id="dur" seconds={s.target_seconds} onCommit={(sec) => setS({ ...s, target_seconds: sec })} />
          </Field>
          <Field label="Темп голоса, слов/мин" htmlFor="wpm" hint="Уточняется по последним 5 загруженным mp3">
            <Input id="wpm" type="number" min={60} max={200} step={1} value={s.wpm_voice} onChange={num('wpm_voice')} />
          </Field>
          <Field label="Порог похожести (0–1)" htmlFor="sim" hint="Только для режима Gemini (эмбеддинги)">
            <Input
              id="sim"
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={s.similarity_threshold}
              onChange={num('similarity_threshold')}
            />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Бюджеты, $</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Field label="Лимит на проект" htmlFor="b-proj" hint="Шаг остановится и попросит поднять лимит">
            <Input id="b-proj" type="number" min={0} step={0.5} value={s.budget_project_usd} onChange={num('budget_project_usd')} />
          </Field>
          <Field label="Предупреждение на проект" htmlFor="b-warn">
            <Input
              id="b-warn"
              type="number"
              min={0}
              step={0.5}
              value={s.budget_project_warn_usd}
              onChange={num('budget_project_warn_usd')}
            />
          </Field>
          <Field label="Стоп за месяц" htmlFor="b-month">
            <Input
              id="b-month"
              type="number"
              min={0}
              step={1}
              value={s.budget_month_stop_usd}
              onChange={num('budget_month_stop_usd')}
            />
          </Field>
        </CardContent>
      </Card>

      <ErrorBox error={save.error} />
      <div className="sticky bottom-0 flex items-center gap-3 border-t bg-background/95 py-3">
        <Button type="submit" variant="accent" disabled={save.isPending}>
          {save.isPending ? 'Сохраняем…' : 'Сохранить настройки'}
        </Button>
        {save.isSuccess && <span className="text-sm text-[#2b7a44]">Сохранено</span>}
      </div>
    </form>
  )
}

export default function SettingsPage() {
  const settings = useSettings()
  const health = useHealth()
  const month = useQuery({ queryKey: ['costs', 'month'], queryFn: () => unwrap(api.GET('/api/costs')), retry: false })

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div>
        <h1 className="mb-4 text-2xl font-bold tracking-tight">Настройки</h1>
        {settings.isLoading ? (
          <Loading />
        ) : settings.isError ? (
          <ErrorBox error={settings.error} />
        ) : (
          <SettingsForm initial={settings.data! as Settings} />
        )}
      </div>
      <aside className="grid content-start gap-4 lg:pt-12">
        <Card>
          <CardHeader>
            <CardTitle>Ключи и сервисы</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            <p className="text-xs text-muted-foreground">Ключи хранятся только в .env — здесь лишь проверка, что они заданы.</p>
            <Status ok={settings.data?.keys?.gemini} label="GEMINI_API_KEY" />
            <Status ok={settings.data?.keys?.database} label="DATABASE_URL" />
            <Status ok={health.data ? health.data.db === 'ok' : undefined} label="База данных (Supabase)" />
            {health.data?.db_hint && <p className="text-xs text-brand-red">{health.data.db_hint}</p>}
            {Object.entries(health.data?.tools ?? {}).map(([k, v]) => (
              <Status key={k} ok={v} label={k} />
            ))}
            <p className="text-xs text-muted-foreground">Последний бэкап: {fmtDate(health.data?.last_backup_at)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Расходы за месяц</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1 text-sm">
            {month.isError ? (
              <ErrorBox error={month.error} />
            ) : (
              <>
                <p className="text-xl font-semibold tabular-nums">
                  {fmtUsd(month.data?.total_usd)}
                  <span className="text-sm font-normal text-muted-foreground"> / {fmtUsd(month.data?.limit_usd)}</span>
                </p>
                {Object.entries(month.data?.by_model ?? {}).map(([m, v]) => (
                  <div key={m} className="flex justify-between text-muted-foreground">
                    <span className="truncate">{m}</span>
                    <span className="tabular-nums">{fmtUsd(v)}</span>
                  </div>
                ))}
              </>
            )}
          </CardContent>
        </Card>
      </aside>
    </div>
  )
}
