import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import type { RunState } from '../domain'
import { stateBadgeClass } from './runState'

/**
 * The states the UI believes exist. Listed here rather than derived from the type, because a type
 * cannot be read at runtime -- the `satisfies` below is what keeps this list and `RunState` in
 * step, so a state added to one and not the other fails to compile.
 */
const UI_STATES = [
  'Draft',
  'Run Authorised',
  'Coverage Locked',
  'Scanning',
  'Candidate Review',
  'Report Drafted',
  'QA In Progress',
  'QA Failed',
  'Awaiting CEO Decision',
  'Continue',
  'Continue With Correction',
  'Approved for Manual Distribution',
  'Distributed',
  'Closed',
  'Paused',
  'Stopped',
  'Corrected',
  'Withdrawn',
] as const satisfies readonly RunState[]

/** Every value in the `run_state` enum, read from the schema that defines it. */
function databaseStates(): string[] {
  const schema = readFileSync(join(__dirname, '../../../../../database/schema.sql'), 'utf8')
  const enumBody = /create type run_state\s+as enum \(([^)]*)\)/i.exec(schema)?.[1]
  if (!enumBody) throw new Error('run_state enum not found in database/schema.sql')
  return [...enumBody.matchAll(/'([^']+)'/g)].map((match) => match[1]!)
}

describe('RunState', () => {
  it('covers every state the database can actually store', () => {
    // AppShell casts `run.state` to RunState. The cast is only honest while this holds: two states
    // (Corrected, Withdrawn) were in the enum and missing from the union, so a run in either
    // satisfied the type at compile time and contradicted it at runtime. Nothing broke, because
    // every consumer takes a string and defaults -- but an exhaustive switch would have been
    // wrong, and TypeScript would have agreed with it.
    expect([...UI_STATES].sort()).toEqual(databaseStates().sort())
  })

  it('gives an unknown state a neutral badge rather than no class at all', () => {
    // The reason the gap above was survivable, and worth keeping true: a state this build has
    // never heard of still renders as a badge instead of an unstyled fragment.
    expect(stateBadgeClass('Some Future State')).toBe('bg-slate-100 text-slate-700')
    expect(stateBadgeClass('Distributed')).not.toBe('bg-slate-100 text-slate-700')
  })
})
