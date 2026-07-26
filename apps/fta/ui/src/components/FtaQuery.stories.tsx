import type { Meta, StoryObj } from '@storybook/react-vite'
import { FtaQuery } from './FtaQuery'
import { escalation, woolAnswer } from './fixtures'

function stubFetch(body: unknown) {
  return () => {
    window.fetch = (async () =>
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })) as typeof window.fetch
  }
}

const meta: Meta<typeof FtaQuery> = { component: FtaQuery, title: 'FTA/FtaQuery' }
export default meta

export const Matched: StoryObj<typeof FtaQuery> = {
  loaders: [
    stubFetch({ status: 'matched', query: 'wool', answers: [woolAnswer], action_required: null }),
  ],
}

export const NoMatch: StoryObj<typeof FtaQuery> = {
  loaders: [
    stubFetch({ status: 'no_match', query: 'zzzz', answers: [], action_required: escalation }),
  ],
}
