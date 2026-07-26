import type { StorybookConfig } from '@storybook/react-vite'

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(ts|tsx)'],
  // a11y only. WCAG 2.2 AA is a requirement (REQ-U-03), so accessibility feedback belongs in the
  // component workshop rather than an audit at the end.
  addons: ['@storybook/addon-a11y'],
  framework: { name: '@storybook/react-vite', options: {} },
  // Private repo: no anonymous usage telemetry leaving the build.
  core: { disableTelemetry: true },
}

export default config
