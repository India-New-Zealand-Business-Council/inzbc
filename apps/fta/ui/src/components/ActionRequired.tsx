import { useId } from 'react'
import type { ActionRequired as ActionRequiredModel } from '../api/client'

/**
 * The escalation state for a query with no confirmed corpus match.
 *
 * Deliberately a different component with a different visual treatment from `Answer`, not a
 * variant of it. The product's core promise is that it does not guess; rendering "contact INZBC"
 * inside the same bordered card as a cited tariff outcome would give guidance the visual
 * authority of a sourced finding. The dashed alert border, the distinct palette and the
 * "No verified answer" heading all exist to make the difference legible before anyone reads a
 * word.
 */
export function ActionRequired({ result }: { result: ActionRequiredModel }) {
  const headingId = useId()
  return (
    // Dashed crimson border on a near-white crimson tint — deliberately not Answer's solid
    // navy/tangerine card (see this component's doc comment above): the dashed border and the
    // brand's alert colour (docs/design-decisions.md; the same token apps/sip/ui uses for
    // Critical-fail states) make the "this is not a finding" distinction legible before anyone
    // reads a word, not just via the heading text.
    <section
      className="mt-4 rounded-md border-2 border-dashed border-inzbc-crimson bg-inzbc-crimson/5 p-4"
      aria-labelledby={headingId}
    >
      <h3 id={headingId} className="text-base font-bold text-inzbc-crimson sm:text-lg">
        No verified answer — action required
      </h3>
      <p className="mt-1 text-slate-800">{result.message}</p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm [&_dd]:text-slate-700 [&_dt]:font-semibold [&_dt]:text-inzbc-crimson">
        <dt>Confidence</dt>
        <dd>
          {result.confidence} — {result.confidence_meaning}
        </dd>
        <dt>Next step</dt>
        <dd>{result.next_step}</dd>
        <dt>Escalation</dt>
        <dd>{result.escalation_path}</dd>
        <dt>Status</dt>
        <dd>{result.status_line}</dd>
      </dl>
      <p className="mt-3 border-t border-inzbc-crimson/20 pt-2 text-xs text-slate-500">{result.disclaimer}</p>
    </section>
  )
}
