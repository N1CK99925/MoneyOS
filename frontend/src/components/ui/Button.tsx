import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { forwardRef } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
  iconRight?: ReactNode
}

const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = 'primary', iconRight, className = '', children, ...props }, ref) => {
    const base =
      'group inline-flex items-center gap-0 rounded-full text-sm font-medium transition-all duration-700 ease-spring active:scale-[0.97] disabled:opacity-30 disabled:cursor-not-allowed'

    const variants = {
      primary:
        'bg-ink text-cream pl-6 pr-2 py-2.5 hover:bg-ink-soft',
      secondary:
        'bg-white border border-border-warm text-ink px-6 py-3 hover:bg-parchment/40',
      ghost:
        'bg-transparent text-ink-muted px-4 py-2 hover:text-ink hover:bg-parchment/40',
    }

    return (
      <button
        ref={ref}
        className={`${base} ${variants[variant]} ${className}`}
        {...props}
      >
        <span>{children}</span>
        {iconRight && (
          <span className="w-8 h-8 rounded-full bg-cream/10 flex items-center justify-center ml-3 transition-all duration-500 ease-spring group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:bg-cream/20">
            {iconRight}
          </span>
        )}
      </button>
    )
  },
)

Button.displayName = 'Button'
export default Button
