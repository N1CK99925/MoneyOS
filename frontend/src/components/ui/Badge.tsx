interface Props {
  variant?: 'default' | 'sage'
  children: React.ReactNode
  className?: string
}

export default function Badge({ variant = 'default', children, className = '' }: Props) {
  const variants = {
    default: 'bg-parchment/60 text-ink-muted border-border-faint',
    sage: 'bg-sage-pale text-sage border-sage/10',
  }

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
