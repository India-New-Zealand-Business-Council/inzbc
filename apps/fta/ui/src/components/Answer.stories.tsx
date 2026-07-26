import type { Meta, StoryObj } from '@storybook/react-vite'
import { Answer } from './Answer'
import { woolAnswer } from './fixtures'

const meta: Meta<typeof Answer> = { component: Answer, title: 'FTA/Answer' }
export default meta

export const Sourced: StoryObj<typeof Answer> = { args: { answer: woolAnswer } }

export const WithNotes: StoryObj<typeof Answer> = {
  args: {
    answer: {
      ...woolAnswer,
      topic: 'Dairy - albumins',
      sector: 'Dairy',
      treatment: '50% tariff cut within a quota.',
      notes: 'Not a blanket dairy exclusion; see the separate milk, cheese and butter entry.',
    },
  },
}
