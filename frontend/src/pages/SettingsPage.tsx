import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, CircleDashed, XCircle } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { api, unwrap, type Settings } from '@/api/client'
import { useHealth, useSettings } from '@/api/hooks'
import { ErrorBox, Loading } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label, Select, Textarea } from '@/components/ui/input'
import { DURATION_OPTIONS } from '@/lib/steps'
import { fmtDate, fmtDuration, fmtUsd } from '@/lib/utils'

const MODEL_FIELDS: { key: keyof NonNullable<Settings['models']>; label: string }[] = [
  { key: 'text', label: 'Текст (бриф, факты, раскадровка)' },
  { key: 'script', label: 'Сценарий' },
  { key: 'cheap', label: 'Дешёвая (проверки)' },
  { key: 'image', label: 'Картинки' },
  { key: 'embed', label: 'Эмбеддинги (похожесть)' },
]

function Field({ label, hint, children, htmlFor }: { label: string; hint?: string; children: ReactNode; htmlFor: string }) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
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

function SettingsForm({ initial }: { initial: Settings }) {
  const qc = useQueryClient()
  const [s, setS] = useState<Settings>(initial)
  const num = (k: keyof Settings) => (e: React.ChangeEvent<HTMLInputElement>) => setS({ ...s, [k]: Number(e.target.value) })
  const save = useMutation({
    mutationFn: () => {
      const { keys: _keys, ...body } = s
      return unwrap(api.PUT('/api/settings', { body: body as Settings }))
    },
    onSuccess: (data) => qc.setQueryData(['settings'], data),
  })
  const targetWords = Math.round((s.wpm_voice * s.target_seconds) / 60)

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
          <CardTitle>Модели</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {MODEL_FIELDS.map((m) => (
            <Field key={m.key} label={m.label} htmlFor={`m-${m.key}`}>
              <Input
                id={`m-${m.key}`}
                value={s.models?.[m.key] ?? ''}
                onChange={(e) => setS({ ...s, models: { ...s.models!, [m.key]: e.target.value } })}
              />
            </Field>
          ))}
          <Field label="Кто пишет сценарий" htmlFor="writer">
            <Select
              id="writer"
              value={s.script_writer}
              onChange={(e) => setS({ ...s, script_writer: e.target.value as Settings['script_writer'] })}
            >
              <option value="gemini">Gemini</option>
              <option value="claude_code">Claude Code (подписка, CLI)</option>
            </Select>
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Стиль картинок</CardTitle>
        </CardHeader>
        <CardContent>
          <Field label="STYLE SUFFIX — добавляется к каждому промпту фона" htmlFor="style">
            <Textarea
              id="style"
              rows={6}
              className="font-mono text-xs"
              value={s.style_suffix ?? ''}
              onChange={(e) => setS({ ...s, style_suffix: e.target.value })}
            />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Длительность и проверки</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Field label="Длительность по умолчанию" htmlFor="dur" hint={`≈ ${targetWords} слов`}>
            <Select id="dur" value={s.target_seconds} onChange={(e) => setS({ ...s, target_seconds: Number(e.target.value) })}>
              {DURATION_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  {fmtDuration(d)} мин
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Темп голоса, слов/мин" htmlFor="wpm" hint="Уточняется по последним 5 загруженным mp3">
            <Input id="wpm" type="number" min={60} max={200} step={1} value={s.wpm_voice} onChange={num('wpm_voice')} />
          </Field>
          <Field label="Порог похожести (0–1)" htmlFor="sim" hint="Выше порога — фраза считается заимствованной">
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
      <div className="flex items-center gap-3">
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
          <SettingsForm initial={settings.data!} />
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
