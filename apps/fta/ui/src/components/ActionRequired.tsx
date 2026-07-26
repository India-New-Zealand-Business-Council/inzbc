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
  return (
    <section className="fta-action-required" aria-labelledby="action-required-heading">
      <h3 id="action-required-heading">No verified answer — action required</h3>
      <p>{result.message}</p>
      <dl>
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
      <p className="fta-disclaimer">{result.disclaimer}</p>
    </section>
  )
}
