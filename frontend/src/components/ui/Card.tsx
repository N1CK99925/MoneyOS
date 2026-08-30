import type { HTMLAttributes, ReactNode } from 'react'
import { forwardRef } from 'react'

interface Props extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'interactive'
  children?: ReactNode
}

const Card = forwardRef<HTMLDivElement, Props>(
  ({ variant = 'default', className = '', children, ...props }, ref) => {
    const base = 'rounded-[1.5rem] bg-cream-dark border border-border-faint p-1 transition-all duration-700 ease-spring'

    const variants = {
      default: '',
      elevated: 'shadow-card',
      interactive: 'hover:border-border-warm/60 hover:shadow-card-hover',
    }

    return (
      <div ref={ref} className={`${base} ${variants[variant]} ${className}`} {...props}>
        <div className="h-full rounded-[calc(1.5rem-4px)] bg-white border border-border-faint/50 inset-highlight">
          {children}
        </div>
      </div>
    )
  },
)

Card.displayName = 'Card'
export default Card
