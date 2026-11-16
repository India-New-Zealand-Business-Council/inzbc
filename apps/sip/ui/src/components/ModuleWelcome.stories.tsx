import type { Meta, StoryObj } from '@storybook/react-vite'
import { ModuleWelcome } from './ModuleWelcome'

const meta: Meta<typeof ModuleWelcome> = {
  component: ModuleWelcome,
  title: 'SIP/Module Welcome',
  args: {
    storageKey: 'storybook.sip.welcome',
    title: 'Work a controlled SIP run',
    steps: ['Review the current run.', 'Record evidence through a named role.', 'Check the audit trail.'],
  },
  beforeEach: () => window.localStorage.removeItem('storybook.sip.welcome'),
}
export default meta

export const Expanded: StoryObj<typeof ModuleWelcome> = {}
