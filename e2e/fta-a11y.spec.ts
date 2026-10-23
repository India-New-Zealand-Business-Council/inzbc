import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

/** The standalone FTA Explainer, as the docker image serves it, scanned with axe. */
test('the FTA Explainer has no WCAG 2.2 AA violations axe can detect, before and after a query', async ({ page }) => {
  const scan = async () => {
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze()
    return results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
  }
  await page.goto('/')
  expect(await scan()).toEqual([])
  await page.getByLabel('Ask about the NZ–India FTA').fill('wool')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page.getByRole('article').first()).toBeVisible()
  expect(await scan()).toEqual([])
})

test('a member can ask the FTA Explainer a question with the keyboard alone', async ({ page }) => {
  await page.goto('/')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused()
  await page.keyboard.press('Enter')
  const input = page.getByLabel('Ask about the NZ–India FTA')
  for (let i = 0; i < 20 && !(await input.evaluate((el) => el === document.activeElement)); i += 1) {
    await page.keyboard.press('Tab')
  }
  await expect(input).toBeFocused()
  await page.keyboard.type('wool')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('article').first()).toBeVisible()
})
