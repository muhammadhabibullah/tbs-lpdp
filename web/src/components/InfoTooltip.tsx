import { useEffect, useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'

export default function InfoTooltip({
  label,
  className = '',
  children,
}: {
  label: ReactNode
  className?: string
  children: ReactNode
}) {
  const descriptionId = useId()
  const rootRef = useRef<HTMLSpanElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current?.contains(event.target as Node)) return
      setOpen(false)
      triggerRef.current?.blur()
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [open])

  return (
    <span
      ref={rootRef}
      className={`info-tooltip ${open ? 'is-open' : ''}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => {
        if (document.activeElement !== triggerRef.current) setOpen(false)
      }}
    >
      <button
        ref={triggerRef}
        type="button"
        className={`package-badge info-tooltip-trigger ${className}`.trim()}
        aria-describedby={descriptionId}
        aria-expanded={open}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen(true)}
      >
        {label}
        <span className="info-tooltip-mark" aria-hidden="true">
          i
        </span>
      </button>
      <span className="info-tooltip-content" id={descriptionId} role="tooltip">
        {children}
      </span>
    </span>
  )
}
