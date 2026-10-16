import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, formData, unwrap, type Schemas } from '@/api/client'
import { Dropzone, Empty, ErrorBox, Loading } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

type Pose = Schemas['Pose']

function PoseCard({ pose }: { pose: Pose }) {
  const qc = useQueryClient()
  const [name, setName] = useState(pose.name ?? '')
  const [tags, setTags] = useState((pose.tags ?? []).join(', '))
  const refresh = () => qc.invalidateQueries({ queryKey: ['poses'] })
  const update = useMutation({
    mutationFn: (body: { name?: string; tags?: string[]; active?: boolean }) =>
      unwrap(api.PATCH('/api/poses/{poseId}', { params: { path: { poseId: pose.id! } }, body })),
    onSettled: refresh,
  })
  const remove = useMutation({
    mutationFn: () => unwrap(api.DELETE('/api/poses/{poseId}', { params: { path: { poseId: pose.id! } } })),
    onSettled: refresh,
  })
  const nameOk = /^[a-z0-9_]{2,32}$/.test(name)
  return (
    <Card className="overflow-hidden">
      <div className="grid aspect-square place-items-center bg-[repeating-conic-gradient(#ece5d6_0_25%,#fffdf8_0_50%)] bg-[length:16px_16px] p-2">
        {pose.url && <img src={pose.url} alt={pose.name} className="max-h-full max-w-full object-contain" loading="lazy" />}
      </div>
      <div className="grid gap-2 p-3">
        <div className="flex items-center gap-2">
          <Badge tone={pose.active ? 'green' : 'neutral'}>{pose.active ? 'активна' : 'кандидат'}</Badge>
          <span className="text-xs text-muted-foreground">
            {pose.width}×{pose.height}
          </span>
        </div>
        <Input aria-label="Имя позы" className="h-8 font-mono text-xs" value={name} onChange={(e) => setName(e.target.value)} />
        <Input aria-label="Теги" className="h-8 text-xs" placeholder="теги через запятую" value={tags} onChange={(e) => setTags(e.target.value)} />
        <div className="flex flex-wrap gap-1.5">
          <Button
            size="sm"
            disabled={!nameOk || update.isPending}
            onClick={() =>
              update.mutate({
                name,
                tags: tags
                  .split(',')
                  .map((t) => t.trim())
                  .filter(Boolean),
              })
            }
          >
            Сохранить
          </Button>
          <Button size="sm" variant="outline" disabled={update.isPending} onClick={() => update.mutate({ active: !pose.active })}>
            {pose.active ? 'Выключить' : 'Включить'}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={remove.isPending}
            onClick={() => window.confirm(`Удалить позу ${pose.name}?`) && remove.mutate()}
          >
            Удалить
          </Button>
        </div>
        {!nameOk && <p className="text-xs text-brand-red">Имя: a–z, 0–9, _ (2–32)</p>}
        <ErrorBox error={update.error ?? remove.error} />
      </div>
    </Card>
  )
}

export default function PosesPage() {
  const qc = useQueryClient()
  const poses = useQuery({ queryKey: ['poses'], queryFn: () => unwrap(api.GET('/api/poses')) })
  const upload = useMutation({
    mutationFn: (file: File) =>
      unwrap(
        api.POST('/api/poses/sheets', {
          body: { file: file as unknown as string },
          bodySerializer: (b) => formData(b as Record<string, unknown>),
        }),
      ),
    onSettled: () => qc.invalidateQueries({ queryKey: ['poses'] }),
  })
  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-bold tracking-tight">Библиотека поз</h1>
      <Dropzone
        accept="image/png"
        label={upload.isPending ? 'Обрабатываем лист…' : 'Загрузить лист поз (PNG на зелёном фоне #00FF00)'}
        disabled={upload.isPending}
        onFile={(f) => upload.mutate(f)}
      />
      <ErrorBox error={upload.error} />
      {poses.isLoading ? (
        <Loading />
      ) : poses.isError ? (
        <ErrorBox error={poses.error} />
      ) : !poses.data?.length ? (
        <Empty>Поз пока нет.</Empty>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {poses.data.map((p) => (
            <PoseCard key={`${p.id}:${p.name}:${p.active}`} pose={p} />
          ))}
        </div>
      )}
    </div>
  )
}
