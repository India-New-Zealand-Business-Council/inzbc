import { expect, test } from '@playwright/test'
import { mockPlatformApi } from './support/platformApi'

/**
 * Friday's regression pass found this gap: reflow.spec.ts (#100) guards the FTA Explainer's
 * query flow at 320px (WCAG 2.2 SC 1.4.10), but nothing guards the platform shell at all — and
 * Brief Builder is denser than anything FTA renders: a 112-row mandatory-source table
 * (BriefBuilderScreen.tsx, from lib/fixtures.ts, no API needed to populate it) plus the scored
 * candidate list, both expandable, both real content rather than placeholder text. That is
 * exactly the shape of UI most likely to clip or force horizontal scroll at a narrow width, and
 * it was never checked.
 */
test.use({ viewport: { width: 320, height: 640 } })

test('Brief Builder reflows at 320px with no horizontal scroll or clipping', async ({ page }) => {
  await mockPlatformApi(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Brief Builder', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Brief Builder' })).toBeVisible()
  const gotIt = page.getByRole('button', { name: 'Got it' })
  if (await gotIt.isVisible().catch(() => false)) await gotIt.click()

  const viewportWidth = page.viewportSize()!.width

  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
  expect(scrollWidth).toBeLessThanOrEqual(viewportWidth)

  // Expand one mandatory-source group and check its row, not just the collapsed header — a
  // collapsed accordion hides the exact long-label-plus-count row most likely to overflow.
  await page.getByRole('button', { name: 'Expand all' }).click()
  const landmarks = [
    page.getByRole('heading', { level: 1, name: 'Brief Builder' }),
    page.getByText(/mandatory sources/).first(),
    page.getByRole('button', { name: 'Collapse all' }),
  ]
  for (const locator of landmarks) {
    const box = await locator.boundingBox()
    expect(box, `${await locator.evaluate((el) => el.outerHTML.slice(0, 80))} has no layout box`).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewportWidth)
  }
})
