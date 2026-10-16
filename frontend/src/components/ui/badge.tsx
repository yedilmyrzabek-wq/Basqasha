import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap',
  {
    variants: {
      tone: {
        neutral: 'border-border bg-muted text-muted-foreground',
        blue: 'border-brand-blue/30 bg-brand-blue/10 text-brand-blue',
        green: 'border-brand-green/30 bg-brand-green/10 text-[#2b7a44]',
        yellow: 'border-brand-yellow/50 bg-brand-yellow/20 text-[#8a6410]',
        red: 'border-brand-red/30 bg-brand-red/10 text-brand-red',
        ink: 'border-ink bg-ink text-paper',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
)

export type BadgeTone = NonNullable<VariantProps<typeof badgeVariants>['tone']>

export function Badge({
  className,
  tone,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}
