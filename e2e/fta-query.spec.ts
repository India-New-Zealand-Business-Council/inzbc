import { expect, test } from '@playwright/test'

/**
 * Issue #100's first two acceptance criteria, against the real running service (no mocked
 * response) — the same two queries the `docker` CI job already proves at the HTTP level
 * (`q=wool` matches, `q=zzzznotathing` doesn't), now asserted through the actual rendered UI
 * a member sees, not just the JSON.
 */

test('a member can query and see a sourced answer', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Ask about the NZ–India FTA').fill('wool')
  await page.getByRole('button', { name: 'Search' }).click()

  // Real corpus fields (citation, confidence, verified date) are present on the rendered
  // card, not just a bare "match found" — matches Answer.tsx's own evidence requirement.
  const answer = page.getByRole('article').first()
  await expect(answer).toBeVisible()
  await expect(answer.getByText('Source', { exact: true })).toBeVisible()
  await expect(answer.getByText('Confidence', { exact: true })).toBeVisible()
  await expect(answer.getByText('Verified', { exact: true })).toBeVisible()

  // Never the escalation state alongside a real match.
  await expect(page.getByText('No verified answer')).not.toBeVisible()
})

test('a no-match query escalates — never a fabricated answer', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Ask about the NZ–India FTA').fill('zzzznotathing')
  await page.getByRole('button', { name: 'Search' }).click()

  await expect(page.getByRole('heading', { name: 'No verified answer — action required' })).toBeVisible()
  // The escalation section, never Answer's article element — ActionRequired.tsx is a
  // deliberately distinct component precisely so this never renders as a sourced finding.
  await expect(page.getByRole('article')).toHaveCount(0)
})
