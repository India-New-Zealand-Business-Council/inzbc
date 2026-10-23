import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { mockPlatformApi, RUN } from './support/platformApi'

/**
 * The platform shell (`apps/sip/ui`) in a real browser: first-visit onboarding, the module
 * introductions, the assistant and the run workflow screens, each scanned with axe against
 * WCAG 2.2 AA. The API is a stand-in (support/platformApi.ts); the FTA Explainer's own e2e
 * specs cover the real API through the docker image.
 */

const SCREENS = [
  'Overview',
  'Getting started',
  'Runs & Candidates',
  'Brief Builder',
  'QA Review',
  'CEO Decision',
  'Distribution',
  'FTA Explainer',
  'Comms Assistant',
  'Member Portal',
]

async function expectNoAxeViolations(page: import('@playwright/test').Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  const summary = results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
  expect(summary).toEqual([])
}

test('a first visit opens on Getting started, with the steps for the signed-in roles', async ({ page }) => {
  await mockPlatformApi(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1, name: 'Getting started' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 3, name: 'Analyst' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 3, name: 'Reviewer' })).toBeVisible()

  await page.getByRole('button', { name: 'Go to the platform overview' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'INZBC Platform' })).toBeVisible()

  // Onboarded: the next visit opens on the overview.
  await page.reload()
  await expect(page.getByRole('heading', { level: 1, name: 'INZBC Platform' })).toBeVisible()
})

test('each module shows its introduction once, then folds to one link', async ({ page }) => {
  await mockPlatformApi(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'FTA Explainer', exact: true }).click()
  const intro = page.getByRole('region', { name: 'How the FTA Explainer works' })
  await expect(intro).toBeVisible()
  await intro.getByRole('button', { name: 'Got it' }).click()
  await expect(intro).toBeHidden()

  await page.getByRole('button', { name: 'Comms Assistant', exact: true }).click()
  await expect(page.getByRole('region', { name: 'How the Comms Assistant works' })).toBeVisible()

  await page.getByRole('button', { name: 'FTA Explainer', exact: true }).click()
  await expect(page.getByRole('button', { name: 'How this works' })).toBeVisible()
})

test('the assistant answers from the home screen and says what it looked up', async ({ page }) => {
  const api = await mockPlatformApi(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Overview', exact: true }).click()
  await page.getByRole('button', { name: 'Which runs are waiting on QA?' }).click()
  await expect(page.getByText(`${RUN.run_number} is in QA In Progress.`)).toBeVisible()
  await expect(page.getByText('Looked up: Listed 1 run(s)')).toBeVisible()
  expect(api.questions).toEqual(['Which runs are waiting on QA?'])
})

test('the workflow screens name the run they act on', async ({ page }) => {
  await mockPlatformApi(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'QA Review', exact: true }).click()
  await expect(page.getByText(`Working run ${RUN.run_number}`)).toBeVisible()
})

for (const name of SCREENS) {
  test(`${name} has no WCAG 2.2 AA violations axe can detect`, async ({ page }) => {
    await mockPlatformApi(page)
    await page.goto('/')
    await page.getByRole('button', { name, exact: true }).click()
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.waitForLoadState('networkidle')
    await expectNoAxeViolations(page)
  })
}
