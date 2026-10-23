import { expect, test, type Page } from '@playwright/test'
import { mockPlatformApi, RUN } from './support/platformApi'

/**
 * The platform shell with the keyboard alone (WCAG 2.1.1, 2.4.1, 2.4.7): no mouse calls
 * anywhere in this file. The FTA Explainer's keyboard path is covered by its own spec against
 * the docker image.
 */

/** Tabs forward until `name` has focus, failing rather than looping forever. */
async function tabTo(page: Page, name: RegExp | string, limit = 60) {
  for (let i = 0; i < limit; i += 1) {
    await page.keyboard.press('Tab')
    const label = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null
      if (!el || el === document.body) return ''
      return (el.getAttribute('aria-label') ?? el.getAttribute('placeholder') ?? el.innerText ?? '').trim()
    })
    if (typeof name === 'string' ? label === name : name.test(label)) return page.locator(':focus')
  }
  throw new Error(`never reached ${name} by Tab`)
}

test('the skip link moves focus past the header into the page', async ({ page }) => {
  await mockPlatformApi(page)
  await page.goto('/')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused()
  await page.keyboard.press('Enter')
  // The next Tab lands inside <main>, not back on the first nav tab.
  await page.keyboard.press('Tab')
  const insideMain = await page.evaluate(() => document.querySelector('main')?.contains(document.activeElement) ?? false)
  expect(insideMain).toBe(true)
})

test('every module can be opened, and its introduction dismissed, from the keyboard', async ({ page }) => {
  await mockPlatformApi(page)
  await page.goto('/')
  const tab = await tabTo(page, 'FTA Explainer')
  await expect(tab).toHaveCSS('outline-style', 'solid')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { level: 1, name: 'FTA Explainer' })).toBeVisible()

  await tabTo(page, 'Got it')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('region', { name: 'How the FTA Explainer works' })).toBeHidden()
})

test('the assistant can be asked and answered from the keyboard', async ({ page }) => {
  const api = await mockPlatformApi(page)
  await page.goto('/')
  await tabTo(page, 'Overview')
  await page.keyboard.press('Enter')
  const box = page.getByLabel('Your question')
  await tabTo(page, /Ask about runs/)
  await expect(box).toBeFocused()
  await page.keyboard.type('Which run is in QA?')
  await page.keyboard.press('Enter')
  await expect(page.getByText(`${RUN.run_number} is in QA In Progress.`)).toBeVisible()
  expect(api.questions).toEqual(['Which run is in QA?'])
  // Focus returns to the box, ready for the next question.
  await expect(box).toBeFocused()
})
