import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, formData, unwrap } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject } from '@/api/hooks'
import { CopyButton, Dropzone, Empty, ErrorBox, Loading, Notice } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label, Select } from '@/components/ui/input'
import { fmtDuration } from '@/lib/utils'
import { isNotFound, type StepViewProps } from './types'

type ModelId = 'eleven_v4' | 'eleven_v3'
type Plan = 'free' | 'starter' | 'creator' | 'pro' | 'unknown'

export default function VoiceStep({ project, state }: StepViewProps) {
  const id = project.id
  const invalidate = useInvalidateProject(id)
  const voice = useQuery({
    queryKey: [...projectKey(id), 'voice', stepVersionKey(project, 'voice')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/voice', { params: { path: { projectId: id } } })),
    retry: false,
  })
  const [model, setModel] = useState<ModelId>('eleven_v4')
  const [plan, setPlan] = useState<Plan>('unknown')

  const upload = useMutation({
    mutationFn: (file: File) =>
      unwrap(
        api.POST('/api/projects/{projectId}/voice', {
          params: { path: { projectId: id } },
          // openapi-fetch types the multipart body as its schema; FormData is built by bodySerializer.
          body: { file: file as unknown as string, model_id: model, provider_plan: plan },
          bodySerializer: (b) => formData(b as Record<string, unknown>),
        }),
      ),
    onSettled: invalidate,
  })
  const accept = useMutation({
    mutationFn: () =>
      unwrap(api.POST('/api/projects/{projectId}/voice/accept-alignment', { params: { path: { projectId: id } } })),
    onSettled: invalidate,
  })

  if (voice.isLoading) return <Loading />
  if (voice.isError && !isNotFound(voice.error)) return <ErrorBox error={voice.error} />
  const v = voice.data
  if (!v?.tts_text)
    return (
      <Empty>
        {state.status === 'running' ? 'Готовим текст для озвучки…' : 'Текст для озвучки появится после утверждения сценария.'}
      </Empty>
    )

  const parts = v.tts_parts && v.tts_parts.length > 1 ? v.tts_parts : null
  const track = v.track
  const plainChars = v.tts_chars ?? v.tts_text.length

  return (
    <div className="grid gap-5">
      <section className="grid gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h3 className="font-semibold">1. Текст для ElevenLabs</h3>
          <Badge tone="blue">{v.model_hint || 'Модель: Eleven v4 / v3'}</Badge>
          <span className="text-sm tabular-nums text-muted-foreground">
            {plainChars.toLocaleString('ru-RU')} символов
          </span>
          {!parts && <CopyButton text={v.tts_text} label="Копировать текст для ElevenLabs" variant="accent" />}
        </div>
        <p className="text-xs text-muted-foreground">
          Только модели Eleven v4 и v3 поддерживают казахский. Вставьте текст целиком, без правок — синхронизация
          строится по нему.
        </p>
        {parts ? (
          <div className="grid gap-2">
            <Notice>Текст длиннее 5000 символов — разбит на {parts.length} части. Озвучьте по очереди и склейте в один mp3.</Notice>
            {parts.map((p, i) => (
              <div key={i} className="rounded-md border bg-paper p-3">
                <div className="mb-2 flex items-center gap-3">
                  <span className="text-sm font-medium">Часть {i + 1}</span>
                  <span className="text-xs text-muted-foreground">{p.length} символов</span>
                  <CopyButton text={p} label={`Копировать часть ${i + 1}`} />
                </div>
                <div className="max-h-48 overflow-auto whitespace-pre-wrap text-sm">{p}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md border bg-paper p-3 text-sm leading-relaxed">
            {v.tts_text}
          </div>
        )}
      </section>

      <section className="grid gap-3">
        <h3 className="font-semibold">2. Загрузите mp3</h3>
        <div className="flex flex-wrap gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="v-model">Модель</Label>
            <Select id="v-model" className="w-40" value={model} onChange={(e) => setModel(e.target.value as ModelId)}>
              <option value="eleven_v4">Eleven v4</option>
              <option value="eleven_v3">Eleven v3</option>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="v-plan">Тариф ElevenLabs</Label>
            <Select id="v-plan" className="w-40" value={plan} onChange={(e) => setPlan(e.target.value as Plan)}>
              <option value="unknown">не указан</option>
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="creator">Creator</option>
              <option value="pro">Pro</option>
            </Select>
          </div>
        </div>
        {plan === 'free' && (
          <Notice>На бесплатном тарифе ElevenLabs нельзя монетизировать озвучку — публикация будет заблокирована.</Notice>
        )}
        <Dropzone
          accept="audio/mpeg,.mp3"
          label={upload.isPending ? 'Загружаем…' : track ? 'Загрузить новую озвучку (mp3)' : 'Озвучка mp3'}
          disabled={upload.isPending || state.status === 'running'}
          onFile={(f) => upload.mutate(f)}
        />
        <ErrorBox error={upload.error} />
      </section>

      {track && (
        <section className="grid gap-3">
          <h3 className="font-semibold">3. Результат</h3>
          {track.url && <audio controls src={track.url} className="w-full" />}
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
            <span>
              Длительность: <b>{fmtDuration(track.duration)}</b>
              <span className="text-muted-foreground"> (цель {fmtDuration(project.target_seconds)})</span>
            </span>
            {track.wpm_measured != null && (
              <span>
                Темп: <b>{Math.round(track.wpm_measured)}</b> слов/мин
              </span>
            )}
            {track.anchored_ratio != null && (
              <span>
                Синхронизация: <b>{Math.round(track.anchored_ratio * 100)}%</b> предложений на паузах
              </span>
            )}
            {track.alignment_ok != null && (
              <Badge tone={track.alignment_ok ? 'green' : 'yellow'}>
                {track.alignment_ok ? 'синхронизация OK' : 'синхронизация неточная'}
              </Badge>
            )}
          </div>
          {state.wait_reason === 'review_alignment' && (
            <Notice>
              <div className="flex flex-wrap items-center gap-3">
                <span>
                  Меньше 90% предложений попали на паузы. Прослушайте: если речь ровная — примите; иначе перезапишите с
                  более чёткими паузами.
                </span>
                <Button size="sm" disabled={accept.isPending} onClick={() => accept.mutate()}>
                  Принять синхронизацию
                </Button>
              </div>
              <ErrorBox error={accept.error} className="mt-2" />
            </Notice>
          )}
        </section>
      )}
    </div>
  )
}
