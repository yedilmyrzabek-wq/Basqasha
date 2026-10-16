import { AlertTriangle, Check, Copy, Loader2, Upload } from 'lucide-react'
import { useRef, useState, type ReactNode } from 'react'
import { errorText } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button, type ButtonProps } from '@/components/ui/button'
import { copyText, cn } from '@/lib/utils'
import { STEP_STATUS } from '@/lib/steps'
import type { StepStatus } from '@/api/client'

export function StepStatusBadge({ status }: { status: StepStatus }) {
  const s = STEP_STATUS[status]
  return (
    <Badge tone={s.tone}>
      {status === 'running' && <Loader2 className="size-3 animate-spin" />}
      {s.label}
    </Badge>
  )
}

export function Loading({ text = 'Загрузка…' }: { text?: string }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" /> {text}
    </div>
  )
}

export function ErrorBox({ error, className }: { error: unknown; className?: string }) {
  if (!error) return null
  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-2 rounded-md border border-brand-red/40 bg-brand-red/10 px-3 py-2 text-sm text-brand-red',
        className,
      )}
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0" />
      <span className="max-h-48 overflow-auto whitespace-pre-wrap break-words">{errorText(error)}</span>
    </div>
  )
}

export function Notice({ children, tone = 'yellow' }: { children: ReactNode; tone?: 'yellow' | 'blue' }) {
  return (
    <div
      className={cn(
        'rounded-md border px-3 py-2 text-sm',
        tone === 'yellow' ? 'border-brand-yellow/60 bg-brand-yellow/15' : 'border-brand-blue/40 bg-brand-blue/10',
      )}
    >
      {children}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-md border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">{children}</div>
}

export function CopyButton({
  text,
  label = 'Копировать',
  ...props
}: { text: string; label?: string } & Omit<ButtonProps, 'onClick'>) {
  const [done, setDone] = useState(false)
  return (
    <Button
      variant="outline"
      size="sm"
      {...props}
      onClick={async () => {
        if (await copyText(text)) {
          setDone(true)
          setTimeout(() => setDone(false), 1500)
        }
      }}
    >
      {done ? <Check /> : <Copy />}
      {done ? 'Скопировано' : label}
    </Button>
  )
}

export function Dropzone({
  accept,
  label,
  disabled,
  onFile,
}: {
  accept: string
  label: string
  disabled?: boolean
  onFile: (f: File) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  return (
    <div
      role="button"
      tabIndex={0}
      aria-disabled={disabled}
      onClick={() => !disabled && input.current?.click()}
      onKeyDown={(e) => {
        if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          input.current?.click()
        }
      }}
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        const f = e.dataTransfer.files[0]
        if (f && !disabled) onFile(f)
      }}
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-center text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        over ? 'border-brand-blue bg-brand-blue/10' : 'border-input bg-paper hover:bg-muted/40',
        disabled && 'cursor-not-allowed opacity-50',
      )}
    >
      <Upload className="size-6 text-muted-foreground" />
      <span>{label}</span>
      <span className="text-xs text-muted-foreground">Перетащите файл сюда или нажмите для выбора</span>
      <input
        ref={input}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) onFile(f)
          e.target.value = ''
        }}
      />
    </div>
  )
}
