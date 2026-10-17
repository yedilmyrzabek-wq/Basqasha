import { useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

/** Video length in minutes (any value 1–60, step 0.5); reports seconds. Commits on blur / Enter. */
export function MinutesInput({
  seconds,
  onCommit,
  id,
  className,
  disabled,
}: {
  seconds: number
  onCommit: (seconds: number) => void
  id?: string
  className?: string
  disabled?: boolean
}) {
  const [v, setV] = useState(String(seconds / 60))
  useEffect(() => setV(String(seconds / 60)), [seconds])
  const commit = () => {
    const m = Number(v.replace(',', '.'))
    if (!Number.isFinite(m) || m < 1 || m > 60) {
      setV(String(seconds / 60))
      return
    }
    const s = Math.round(m * 60)
    if (s !== seconds) onCommit(s)
  }
  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      <Input
        id={id}
        type="number"
        min={1}
        max={60}
        step={0.5}
        className="h-8 w-20"
        value={v}
        disabled={disabled}
        onChange={(e) => setV(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            commit()
          }
        }}
      />
      <span className="text-sm text-muted-foreground">мин</span>
    </div>
  )
}
