/**
 * Runs axe against every story in every built Storybook and fails on any violation.
 *
 * Each UI's Storybook sets `a11y: { test: 'error' }`, but `storybook build` only compiles the
 * stories; nothing executes those checks. This script does, using the same WCAG 2.2 AA tag set
 * as e2e/fta-a11y.spec.ts, so a story that renders an inaccessible state fails CI instead of
 * waiting for an audit.
 *
 * axe covers what can be detected automatically (contrast, names, roles, landmarks). It does not
 * prove focus order or keyboard paths; those still need keyboard tests such as the one in
 * e2e/fta-a11y.spec.ts.
 *
 * Usage (after `pnpm -r --if-present build-storybook`):
 *   node scripts/storybook_a11y.mjs
 *
 * Needs the root `@playwright/test` and `@axe-core/playwright` dev dependencies and a Chromium
 * from `pnpm exec playwright install chromium`.
 */
import AxeBuilder from '@axe-core/playwright'
import { chromium } from '@playwright/test'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { createServer } from 'node:http'
import { extname, join, resolve, sep } from 'node:path'

const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']
const TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.mjs': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
}

/** Serves one storybook-static folder on a free local port. Paths outside it are refused. */
function serve(root) {
  const base = resolve(root)
  const server = createServer((req, res) => {
    const path = decodeURIComponent(new URL(req.url, 'http://localhost').pathname)
    const file = resolve(base, `.${path === '/' ? '/index.html' : path}`)
    if (!file.startsWith(base + sep) || !existsSync(file)) {
      res.writeHead(404).end()
      return
    }
    res.writeHead(200, { 'Content-Type': TYPES[extname(file)] ?? 'application/octet-stream' })
    res.end(readFileSync(file))
  })
  return new Promise((ok) => server.listen(0, '127.0.0.1', () => ok(server)))
}

const builds = readdirSync('apps')
  .map((app) => join('apps', app, 'ui', 'storybook-static'))
  .filter((dir) => existsSync(join(dir, 'index.json')))
// Fail closed: a missing build would otherwise pass with nothing checked.
if (builds.length === 0) {
  console.error('No built Storybook found; run `pnpm -r --if-present build-storybook` first.')
  process.exit(1)
}

const browser = await chromium.launch()
const failures = []
let checked = 0
try {
  for (const dir of builds) {
    const index = JSON.parse(readFileSync(join(dir, 'index.json'), 'utf8'))
    const stories = Object.values(index.entries).filter((entry) => entry.type === 'story')
    if (stories.length === 0) failures.push(`${dir}: no stories to check`)
    const server = await serve(dir)
    const { port } = server.address()
    try {
      for (const story of stories) {
        const context = await browser.newContext()
        const page = await context.newPage()
        await page.goto(`http://127.0.0.1:${port}/iframe.html?id=${story.id}&viewMode=story`)
        await page.waitForSelector('#storybook-root > *', { timeout: 15_000 })
        const { violations } = await new AxeBuilder({ page }).include('#storybook-root').withTags(TAGS).analyze()
        checked += 1
        for (const v of violations) {
          failures.push(`${story.id}: ${v.id} (${v.impact}) at ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
        }
        await context.close()
      }
    } finally {
      server.close()
    }
  }
} finally {
  await browser.close()
}

console.log(`Checked ${checked} stories in ${builds.length} Storybooks against ${TAGS.join(', ')}.`)
if (failures.length > 0) {
  console.error(failures.join('\n'))
  process.exit(1)
}
