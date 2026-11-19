import type { Meta, StoryObj } from '@storybook/react-vite'
import { Header } from './Header'

const meta: Meta<typeof Header> = { component: Header, title: 'Dashboard/Shared Header' }
export default meta

export const Default: StoryObj<typeof Header> = {}
