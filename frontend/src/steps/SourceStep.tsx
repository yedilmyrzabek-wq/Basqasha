import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, unwrap } from '@/api/client'
import { projectKey, stepVersionKey, useInvalidateProject } from '@/api/hooks'
import { Empty, ErrorBox, Loading } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label, Textarea } from '@/components/ui/input'
import { countWords, fmtDuration } from '@/lib/utils'
import { isNotFound, type StepViewProps } from './types'

export default function SourceStep({ project, state }: StepViewProps) {
  const id = project.id
  const invalidate = useInvalidateProject(id)
  const source = useQuery({
    queryKey: [...projectKey(id), 'source', stepVersionKey(project, 'source')],
    queryFn: () => unwrap(api.GET('/api/projects/{projectId}/source', { params: { path: { projectId: id } } })),
    retry: false,
  })
  const [manualOpen, setManualOpen] = useState(false)
  const [text, setText] = useState('')
  const save = useMutation({
    mutationFn: () =>
      unwrap(
        api.PUT('/api/projects/{projectId}/source', {
          params: { path: { projectId: id } },
          body: { transcript: text.trim() },
        }),
      ),
    onSuccess: () => {
      setManualOpen(false)
      setText('')
    },
    onSettled: invalidate,
  })

  const s = source.data
  const showManual = manualOpen || state.status === 'failed'
  const tooShort = text.trim().length < 200

  return (
    <div className="grid gap-4">
      {source.isLoading ? (
        <Loading />
      ) : source.isError && !isNotFound(source.error) ? (
        <ErrorBox error={source.error} />
      ) : !s?.transcript ? (
        <Empty>
          {state.status === 'running' ? 'Скачиваем транскрипт…' : 'Транскрипта пока нет.'}
        </Empty>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm">
            {s.yt_title && <span className="font-medium">{s.yt_title}</span>}
            {s.yt_duration != null && <span className="text-muted-foreground">Длина: {fmtDuration(s.yt_duration)}</span>}
            {s.yt_views != null && (
              <span className="text-muted-foreground">Просмотры: {s.yt_views.toLocaleString('ru-RU')}</span>
            )}
            <Badge tone={s.origin === 'manual' ? 'yellow' : 'blue'}>
              {s.origin === 'manual' ? 'вставлен вручную' : 'yt-dlp'}
            </Badge>
            <span className="text-muted-foreground">
              {countWords(s.transcript)} слов · {s.transcript.length.toLocaleString('ru-RU')} символов
            </span>
          </div>
          <div className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-md border bg-paper p-4 text-sm leading-relaxed">
            {s.transcript}
          </div>
          <p className="text-xs text-muted-foreground">
            Транскрипт используется только на шагах 1–2 (бриф идеи) и для проверки похожести. В сценарий он не попадает.
          </p>
        </>
      )}

      {showManual ? (
        <div className="grid gap-2 rounded-md border p-4">
          <Label htmlFor="manual-transcript">Вставить транскрипт вручную</Label>
          <p className="text-xs text-muted-foreground">
            Если yt-dlp заблокирован: откройте видео на YouTube → «…» → «Показать текст видео», скопируйте и вставьте сюда.
            Таймкоды можно не удалять.
          </p>
          <Textarea id="manual-transcript" rows={10} value={text} onChange={(e) => setText(e.target.value)} />
          <div className="flex items-center gap-3">
            <Button disabled={tooShort || save.isPending} onClick={() => save.mutate()}>
              {save.isPending ? 'Сохраняем…' : 'Сохранить и продолжить'}
            </Button>
            {state.status !== 'failed' && (
              <Button variant="ghost" onClick={() => setManualOpen(false)}>
                Отмена
              </Button>
            )}
            <span className={tooShort ? 'text-xs text-brand-red' : 'text-xs text-muted-foreground'}>
              {text.trim().length} символов (минимум 200)
            </span>
          </div>
          <ErrorBox error={save.error} />
        </div>
      ) : (
        <div>
          <Button variant="outline" size="sm" onClick={() => setManualOpen(true)}>
            Вставить текст вручную
          </Button>
        </div>
      )}
    </div>
  )
}
