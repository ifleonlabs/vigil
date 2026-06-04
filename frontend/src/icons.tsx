/** Inline stroke icons (Heroicons-style) — no emoji, themeable via currentColor. */
import type { ReactNode } from 'react'

const svg = (children: ReactNode) => (
  <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">{children}</svg>
)

export const Icon = {
  up: svg(<path d="M20 6 9 17l-5-5" />),
  down: svg(<path d="M18 6 6 18M6 6l12 12" />),
  changed: svg(<path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16" />),
  none: svg(<><circle cx="12" cy="12" r="9" /><path d="M12 8v4" /></>),
  refresh: svg(<><path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8" /><path d="M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16" /></>),
  trash: svg(<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />),
  pause: svg(<path d="M10 4H6v16h4zM18 4h-4v16h4z" />),
  play: svg(<path d="M6 4l14 8-14 8z" />),
  plus: svg(<path d="M12 5v14M5 12h14" />),
  eye: svg(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></>),
}

export const statusIcon = (s: string) =>
  s === 'up' ? Icon.up : s === 'down' ? Icon.down : s === 'changed' ? Icon.changed : Icon.none
