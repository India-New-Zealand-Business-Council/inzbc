import type { Meta, StoryObj } from '@storybook/react-vite'
import { ActionRequired } from './ActionRequired'
import { escalation } from './fixtures'

/**
 * Sits beside FTA/Answer on purpose: reviewing the two side by side is how you confirm the
 * escalation state never reads as a sourced finding.
 */
const meta: Meta<typeof ActionRequired> = {
  component: ActionRequired,
  title: 'FTA/ActionRequired',
}
export default meta

export const NoVerifiedAnswer: StoryObj<typeof ActionRequired> = { args: { result: escalation } }
