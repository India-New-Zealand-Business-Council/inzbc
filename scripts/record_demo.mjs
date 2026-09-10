/**
 * Records a narrated walkthrough of the INZBC platform.
 *
 * Produces two files in scripts/demo-recording/:
 *   inzbc-demo.webm  — the screen recording, captions burned into the frame
 *   inzbc-demo.vtt   — the same captions as a subtitle track, for an editor or player
 *
 * Captions are drawn by injecting a fixed overlay into the page, so they reach the
 * video without a separate compositing step. The overlay is removed before every
 * click, so it can never cover the thing being demonstrated.
 *
 * Usage:
 *   node scripts/record_demo.mjs
 *   node scripts/record_demo.mjs --url http://localhost:5174 --run RUN-SEED-06
 *
 * Needs the app running (scripts/platform.cmd) and playwright available.
 */
import { chromium } from 'playwright'
import { mkdirSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const args = Object.fromEntries(
  process.argv.slice(2).reduce((pairs, arg, i, all) => {
    if (arg.startsWith('--')) pairs.push([arg.slice(2), all[i + 1]])
    return pairs
  }, []),
)

const URL = args.url ?? 'http://localhost:5173'
const RUN = args.run ?? 'RUN-SEED-06'
const OUT = join(process.cwd(), 'scripts', 'demo-recording')
const SIZE = { width: 1280, height: 720 }

mkdirSync(OUT, { recursive: true })

const cues = []
let started = 0
const OVERLAY_ID = '__inzbc_caption__'

/** Show a caption, hold it long enough to read, and record its timing for the .vtt. */
async function say(page, text, holdMs = 4200) {
  const from = Date.now() - started
  await page.evaluate(
    ([id, message]) => {
      let el = document.getElementById(id)
      if (!el) {
        el = document.createElement('div')
        el.id = id
        Object.assign(el.style, {
          position: 'fixed',
          left: '0',
          right: '0',
          bottom: '0',
          zIndex: '2147483647',
          padding: '16px 40px',
          background: 'rgba(22, 9, 51, 0.94)',
          color: '#ffffff',
          font: '500 18px/1.5 Calibri, system-ui, sans-serif',
          textAlign: 'center',
          pointerEvents: 'none',
        })
        document.body.appendChild(el)
      }
      el.textContent = message
    },
    [OVERLAY_ID, text],
  )
  await page.waitForTimeout(holdMs)
  cues.push({ from, to: Date.now() - started, text })
}

async function clearCaption(page) {
  await page.evaluate((id) => document.getElementById(id)?.remove(), OVERLAY_ID)
}

async function go(page, name) {
  await clearCaption(page)
  await page.getByRole('button', { name, exact: true }).click()
  await page.waitForTimeout(900)
}

function toVtt(entries) {
  const stamp = (ms) => {
    const h = String(Math.floor(ms / 3600000)).padStart(2, '0')
    const m = String(Math.floor(ms / 60000) % 60).padStart(2, '0')
    const s = String(Math.floor(ms / 1000) % 60).padStart(2, '0')
    return `${h}:${m}:${s}.${String(ms % 1000).padStart(3, '0')}`
  }
  return (
    'WEBVTT\n\n' +
    entries.map((c, i) => `${i + 1}\n${stamp(c.from)} --> ${stamp(c.to)}\n${c.text}\n`).join('\n')
  )
}

const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: SIZE,
  recordVideo: { dir: OUT, size: SIZE },
})
const page = await context.newPage()

const failures = []
page.on('console', (m) => m.type() === 'error' && failures.push(m.text()))

started = Date.now()
await page.goto(URL, { waitUntil: 'domcontentloaded' })
await page.waitForTimeout(1500)

// ---------------------------------------------------------------- overview
await say(page, 'INZBC AI Operating System — four modules on one governed backend.')
await say(
  page,
  'The landing page answers one question: is there a real system here? Every number has ' +
    'the command that reproduces it recorded beside it in the source.',
  5200,
)
await say(
  page,
  'One file out of roughly ten thousand lines imports an AI SDK. The FTA Explainer calls ' +
    'no model at all.',
  5000,
)
await say(
  page,
  'Six controls, each naming the file that enforces it. A control that exists only in a ' +
    'document is a documented intention, not a control.',
  5200,
)

// ------------------------------------------------------- runs & candidates
await go(page, 'Runs & Candidates')
await say(
  page,
  'Ten runs, straight from PostgreSQL. The states are the real lifecycle — Draft, ' +
    'Scanning, Report Drafted, QA Failed, Paused, Distributed, Stopped.',
  5600,
)
await say(
  page,
  'The QA column separates Passed, Failed and "not yet run". A run that has not reached ' +
    'QA has no result, which is a different fact from a failure.',
  5400,
)

await clearCaption(page)
const row = page.locator('li').filter({ hasText: RUN }).first()
await row.scrollIntoViewIfNeeded()
await row.getByRole('button', { name: 'Work this run' }).click()
await page.waitForTimeout(1200)
await say(page, `${RUN} is now the working run. The next four screens follow it.`, 3800)

// ----------------------------------------------------------- brief builder
await go(page, 'Brief Builder')
await say(
  page,
  'The header names the run, so the screen can never be ambiguous about what you are editing.',
  4400,
)
await say(
  page,
  'Source coverage is the SIP-185 mandatory register — 112 sources, grouped by category ' +
    'rather than listed flat. A source with no recorded outcome is a Critical stop at QA.',
  6000,
)
await say(
  page,
  "Below are this run's own scored candidates, with source, sector routing, signal strength " +
    'and verification state.',
  4800,
)

// --------------------------------------------------------------- qa review
await go(page, 'QA Review')
await say(
  page,
  'QA Review reads the run state and refuses to open until the brief has been submitted. ' +
    'That is not an error page — it is the state machine.',
  5600,
)

// ------------------------------------------------------------ ceo decision
await go(page, 'CEO Decision')
await say(
  page,
  'The CEO decision screen refuses for the same reason, and names the state it is refusing from.',
  5200,
)
await say(
  page,
  'Three separate decisions live here: the CEO ruling, report approval and distribution ' +
    'authority. Separate, because a status column cannot distinguish "not decided" from "refused".',
  6400,
)

// ------------------------------------------------------------ distribution
await go(page, 'Distribution')
await say(
  page,
  'Read-only by design — no write controls anywhere on this screen. Everything unrecorded ' +
    'shows as pending rather than as an error.',
  5200,
)
await say(
  page,
  'The run archive below is every run this instance has recorded, read from GET /api/runs. ' +
    'These used to be three hard-coded placeholder rows.',
  5400,
)

// ----------------------------------------------------------- fta explainer
await go(page, 'FTA Explainer')
await clearCaption(page)
await page.getByRole('searchbox').fill('dairy')
await page.getByRole('button', { name: 'Search' }).click()
await page.waitForTimeout(1400)
await say(page, 'Four sourced answers — and the first one is the interesting one.', 4000)
await say(
  page,
  'Milk, cheese and butter are excluded from India’s tariff concessions. But read the ' +
    'note: a widely reported comparison is Tier 2, is not a tariff fact, and no Tier 1 source ' +
    'establishes it — so it is deliberately not asserted.',
  7000,
)
await say(
  page,
  'The system is stating what it refuses to claim, and why. Every answer carries its ' +
    'confidence, source, verified date and next step.',
  5600,
)
await say(
  page,
  'There is no model call anywhere in this path. A question with no match routes to INZBC ' +
    'rather than producing an answer.',
  5200,
)

// --------------------------------------------------------- comms assistant
await go(page, 'Comms Assistant')
await say(
  page,
  'Before any input: drafts only. Nothing here sends or publishes, and a named reviewer must ' +
    'approve every draft.',
  5000,
)
await say(
  page,
  '"Redaction removes formatted identifiers such as emails and phone numbers; it cannot remove ' +
    'a name." The system states the limit of its own protection.',
  6000,
)

// ------------------------------------------------------------ member portal
await go(page, 'Member Portal')
await say(
  page,
  'An interface shell, and it says so. Membership stays in Member Jungle — INZBC’s system ' +
    'of record — rather than being duplicated here.',
  5400,
)
await say(
  page,
  'Nothing in this system is deployed. production_enabled is false, because that is the ' +
    'council’s decision and it has not been made.',
  5400,
)

await clearCaption(page)
await page.waitForTimeout(800)

const video = page.video()
await context.close()
await browser.close()

if (video) {
  const target = join(OUT, 'inzbc-demo.webm')
  renameSync(await video.path(), target)
  console.log(`video    ${target}`)
}
writeFileSync(join(OUT, 'inzbc-demo.vtt'), toVtt(cues), 'utf8')
console.log(`captions ${join(OUT, 'inzbc-demo.vtt')} (${cues.length} cues)`)
console.log(`length   ~${Math.round(cues.at(-1).to / 1000)}s`)
if (failures.length) {
  console.log(`\nconsole errors during the walkthrough (${failures.length}):`)
  failures.forEach((f) => console.log(`  ${f}`))
} else {
  console.log('no console errors during the walkthrough')
}
