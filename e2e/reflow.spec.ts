import { expect, test } from '@playwright/test'

/**
 * Issue #100's 320px case. The CSS fix (box-sizing reset, PR #91) was verified once by a
 * one-off Chromium measurement and nothing has guarded it since — this is that guard, run at
 * WCAG 2.2 SC 1.4.10's own reference width (320px) via the `320px-reflow` Playwright project.
 *
 * Checked with a rendered answer on screen, not just the empty form: the dense state (query
 * input, Search button and a full evidence card all at once) is where a reflow regression
 * would actually show up, not the idle page.
 */
test('the FTA query flow reflows at 320px with no horizontal scroll or clipping', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Ask about the NZ–India FTA').fill('wool')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page.getByRole('article').first()).toBeVisible()

  const viewportWidth = page.viewportSize()!.width

  // No horizontal scroll: the document's own scrollable width never exceeds the viewport.
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
  expect(scrollWidth).toBeLessThanOrEqual(viewportWidth)

  // No clipping: each key element is fully inside the viewport, not just present in the DOM.
  // A clipped-but-"visible" element (overflow: hidden cutting off its right edge) would pass
  // toBeVisible() while failing this.
  const landmarks = [
    page.getByRole('heading', { name: 'INZBC FTA Explainer' }),
    page.getByLabel('Ask about the NZ–India FTA'),
    page.getByRole('button', { name: 'Search' }),
    page.getByRole('article').first(),
  ]
  for (const locator of landmarks) {
    const box = await locator.boundingBox()
    expect(box, `${await locator.evaluate((el) => el.outerHTML.slice(0, 80))} has no layout box`).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewportWidth)
  }
})
