import type { Meta, StoryObj } from '@storybook/react-vite'

const swatches = [
  ['Navy', 'bg-inzbc-navy text-white'],
  ['Blue', 'bg-inzbc-blue text-white'],
  ['Forest', 'bg-inzbc-forest text-white'],
  ['Lime', 'bg-inzbc-lime text-inzbc-navy'],
  ['Tangerine', 'bg-inzbc-tangerine text-inzbc-navy'],
  ['Mist', 'bg-inzbc-mist text-inzbc-ink'],
]

function DesignTokens() {
  return (
    <section className="grid max-w-4xl gap-3 sm:grid-cols-3" aria-label="INZBC design tokens">
      {swatches.map(([name, classes]) => (
        <div key={name} className={`rounded-xl border border-inzbc-navy/10 p-5 ${classes}`}>
          <strong>{name}</strong>
        </div>
      ))}
    </section>
  )
}

const meta: Meta<typeof DesignTokens> = {
  component: DesignTokens,
  title: 'Design System/Tokens',
}
export default meta

export const Palette: StoryObj<typeof DesignTokens> = {}
