import '@testing-library/jest-dom/vitest'

// A session is seeded for every test, so a test about a screen does not have to know that a write
// fetches `GET /api/session` for a CSRF token first. Mocking that second endpoint in every test
// would make the suite assert the plumbing rather than the behaviour.
//
// `src/api/session.test.ts` clears it and exercises the real fetch path; that is where the
// session's own behaviour is proven.
import { beforeEach } from 'vitest'
import { seedSession } from './src/api/session'

beforeEach(() => {
  seedSession({
    userId: '00000000-0000-0000-0000-0000000000aa',
    name: 'Test Principal',
    roles: ['Analyst', 'Reviewer', 'SIP Owner'],
    csrfToken: 'a-real-token',
  })
})
