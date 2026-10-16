import type { BadgeTone } from '@/components/ui/badge'
import type { Project, ProjectDetail, StepKey, StepState, StepStatus, WaitReason } from '@/api/client'

export const STEPS: { key: StepKey; title: string; hint: string }[] = [
  { key: 'source', title: 'Источник', hint: 'Транскрипт и метаданные видео' },
  { key: 'idea', title: 'Идея', hint: 'Бриф и 3 варианта для Казахстана' },
  { key: 'facts', title: 'Факты', hint: 'Поиск и проверка фактов' },
  { key: 'script', title: 'Сценарий', hint: 'Казахский текст + проверка похожести' },
  { key: 'voice', title: 'Озвучка', hint: 'Текст для ElevenLabs → mp3' },
  { key: 'storyboard', title: 'Раскадровка', hint: 'Сцены по ~5 с' },
  { key: 'images', title: 'Картинки', hint: '12–15 фонов + автопроверка' },
  { key: 'preview', title: 'Превью', hint: 'Лист кадров и комментарии' },
  { key: 'render', title: 'Рендер', hint: 'Финальный MP4 + Shorts' },
  { key: 'metadata', title: 'Метаданные', hint: 'Заголовки, описание, теги' },
]

export const STEP_STATUS: Record<StepStatus, { label: string; tone: BadgeTone }> = {
  pending: { label: 'Ожидает', tone: 'neutral' },
  running: { label: 'Выполняется', tone: 'blue' },
  waiting_operator: { label: 'Ждёт вас', tone: 'yellow' },
  done: { label: 'Готово', tone: 'green' },
  failed: { label: 'Ошибка', tone: 'red' },
  stale: { label: 'Устарел', tone: 'neutral' },
}

export const WAIT_REASON: Record<WaitReason, string> = {
  choose_angle: 'Выберите вариант идеи',
  approve_script: 'Проверьте и утвердите сценарий',
  upload_voice: 'Озвучьте текст в ElevenLabs и загрузите mp3',
  review_alignment: 'Проверьте синхронизацию голоса',
  manual_images: 'Загрузите недостающие картинки вручную',
  approve_preview: 'Проверьте превью и утвердите',
  budget_exceeded: 'Превышен бюджет проекта — увеличьте лимит',
  confirm_similar_topic: 'Похожая тема уже была — подтвердите',
}

export const PROJECT_STATUS: Record<Project['status'], { label: string; tone: BadgeTone }> = {
  active: { label: 'В работе', tone: 'blue' },
  waiting_operator: { label: 'Ждёт вас', tone: 'yellow' },
  failed: { label: 'Ошибка', tone: 'red' },
  ready: { label: 'Готово', tone: 'green' },
  published: { label: 'Опубликовано', tone: 'ink' },
  archived: { label: 'В архиве', tone: 'neutral' },
}

export const DURATION_OPTIONS = [180, 210, 240, 270, 300]

export function stepTitle(key: StepKey): string {
  return STEPS.find((s) => s.key === key)?.title ?? key
}

export function stepState(project: ProjectDetail | undefined, key: StepKey): StepState {
  return project?.steps.find((s) => s.step === key) ?? { step: key, status: 'pending' }
}

/** The step the operator should look at: waiting/failed/running first, then current_step. */
export function focusStep(project: ProjectDetail): StepKey {
  const ordered = STEPS.map((s) => stepState(project, s.key))
  const hot =
    ordered.find((s) => s.status === 'waiting_operator') ??
    ordered.find((s) => s.status === 'failed') ??
    ordered.find((s) => s.status === 'running')
  if (hot) return hot.step
  if (project.current_step) return project.current_step
  return (ordered.find((s) => s.status !== 'done') ?? ordered[ordered.length - 1]).step
}

/** Poll every 2 s while something runs or the next step is queued (OpenAPI description). */
export function shouldPoll(project: ProjectDetail | undefined): boolean {
  if (!project) return false
  const ordered = STEPS.map((s) => stepState(project, s.key))
  if (ordered.some((s) => s.status === 'running')) return true
  const next = ordered.find((s) => s.status !== 'done')
  return !!next && next.status === 'pending' && project.status === 'active'
}
