import type { ReactNode } from 'react'

// Shared width/padding for every full-bleed section (Header, Footer, main content) so the page
// reads as one consistent layout, not independently-guessed widths per component. max-w-7xl
// (80rem/1280px), not max-w-2xl (42rem/672px): the previous width left large dead margins on
// desktop/laptop screens — a member portal with a dashboard grid needs room for multiple columns
// side by side, not a single narrow reading column. Padding steps up with viewport (px-4 ->
// sm:px-6 -> lg:px-8) rather than a single fixed value, so mobile keeps comfortable edge spacing
// without over-padding on wide screens.
export function Container({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 ${className}`.trim()}>{children}</div>
}
