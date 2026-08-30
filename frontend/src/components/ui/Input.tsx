import type { InputHTMLAttributes } from 'react'
import { forwardRef } from 'react'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

const Input = forwardRef<HTMLInputElement, Props>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label className="text-xs font-medium text-ink-soft uppercase tracking-wider">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`w-full rounded-full bg-white border px-5 py-3 text-sm text-ink placeholder:text-ink-muted outline-none transition-all duration-500 ease-spring focus:ring-2 focus:ring-sage/10 ${
            error
              ? 'border-error-border focus:border-error/30 focus:ring-error/10'
              : 'border-border-warm focus:border-sage/30 focus:ring-sage/10'
          } ${className}`}
          {...props}
        />
        {error && <p className="text-xs text-error">{error}</p>}
      </div>
    )
  },
)

Input.displayName = 'Input'
export default Input
