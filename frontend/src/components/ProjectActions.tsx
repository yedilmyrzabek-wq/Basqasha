import { useMutation } from '@tanstack/react-query'
import { Archive, ArchiveRestore, Square, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api, request, unwrap } from '@/api/client'
import { useInvalidateProject } from '@/api/hooks'
import { ErrorBox } from '@/components/common'
import { Button } from '@/components/ui/button'

type P = { id: string; title?: string | null; status: string }

/** «Остановить»: stops the running step within a second or two (it becomes failed → «Повторить»). */
export function StopButton({ projectId }: { projectId: string }) {
  const refresh = useInvalidateProject(projectId)
  const stop = useMutation({
    mutationFn: () => request(`/api/projects/${projectId}/stop`, { method: 'POST' }),
    onSettled: refresh,
  })
  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="border-brand-red/50 text-brand-red"
        disabled={stop.isPending || stop.isSuccess}
        onClick={() => stop.mutate()}
        title="Прервать выполнение шага (потраченное не возвращается)"
      >
        <Square className="size-3.5" /> {stop.isSuccess ? 'Останавливаем…' : 'Остановить'}
      </Button>
      <ErrorBox error={stop.error} />
    </>
  )
}

/** Archive / restore + delete (with its files). `compact` = icon buttons for table rows. */
export function ProjectActions({ project, compact = false }: { project: P; compact?: boolean }) {
  const refresh = useInvalidateProject(project.id)
  const navigate = useNavigate()
  const archived = project.status === 'archived'
  const archive = useMutation({
    mutationFn: () =>
      unwrap(
        api.PATCH('/api/projects/{projectId}', {
          params: { path: { projectId: project.id } },
          body: { status: archived ? 'active' : 'archived' },
        }),
      ),
    onSettled: refresh,
  })
  const remove = useMutation({
    mutationFn: () => request(`/api/projects/${project.id}?delete_files=true`, { method: 'DELETE' }),
    onSuccess: () => navigate('/'),
    onSettled: refresh,
  })
  const confirmDelete = () =>
    window.confirm(`Удалить проект «${project.title || 'Без названия'}» вместе со всеми файлами (картинки, озвучка, видео)? Это нельзя отменить.`) &&
    remove.mutate()
  return (
    <div className="flex items-center gap-1">
      <Button
        variant={compact ? 'ghost' : 'outline'}
        size="sm"
        disabled={archive.isPending}
        onClick={() => archive.mutate()}
        title={archived ? 'Вернуть из архива' : 'Убрать в архив (скрыть из списка, файлы остаются)'}
      >
        {archived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
        {!compact && (archived ? 'Вернуть из архива' : 'В архив')}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="text-brand-red hover:text-brand-red"
        disabled={remove.isPending}
        onClick={confirmDelete}
        title="Удалить проект и его файлы"
      >
        <Trash2 className="size-4" />
        {!compact && 'Удалить'}
      </Button>
      <ErrorBox error={archive.error ?? remove.error} />
    </div>
  )
}
