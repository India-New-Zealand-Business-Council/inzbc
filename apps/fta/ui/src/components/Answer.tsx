import { useId } from 'react'
import type { Answer as AnswerModel } from '../api/client'

/**
 * Renders one sourced FTA finding. Every field here is evidence or the presentation the
 * Information Standard requires alongside it — citation, effective date, confidence and the
 * approved disclaimer are not optional decoration.
 *
 * The heading id comes from `useId`, never from `answer.topic`. Topic is prose: 13 of the 18
 * corpus entries contain spaces, and `aria-labelledby` takes a space-separated list of IDREFs,
 * so a topic-derived id silently fails to resolve and the article loses its accessible name.
 * `answer.id` is the stable corpus code and is used as the React key instead.
 */
export function Answer({ answer }: { answer: AnswerModel }) {
  const headingId = useId()
  return (
    // Tangerine left-accent + navy/10 border on white — the accent/highlight colour, per the
    // brand guide, against the same card treatment used throughout apps/comms/ui and
    // apps/sip/ui. Distinct from ActionRequired's dashed crimson card below by design (see that
    // component's doc comment) — a sourced finding must never look like an unverified escalation.
    <article
      className="mt-4 rounded-md border border-inzbc-navy/10 border-l-4 border-l-inzbc-tangerine bg-white p-4 shadow-sm"
      aria-labelledby={headingId}
    >
      <h3 id={headingId} className="text-base font-bold text-inzbc-navy sm:text-lg">
        {answer.topic}
      </h3>
      <p className="text-sm text-slate-600">{answer.sector}</p>
      <p className="mt-1 text-slate-800">{answer.treatment}</p>
      {answer.notes ? <p className="mt-1 text-sm text-slate-600">{answer.notes}</p> : null}
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm [&_dd]:text-slate-700 [&_dt]:font-semibold [&_dt]:text-inzbc-navy">
        <dt>Confidence</dt>
        <dd>
          {answer.confidence} — {answer.confidence_meaning}
        </dd>
        <dt>Source</dt>
        <dd>{answer.citation}</dd>
        <dt>Verified</dt>
        <dd>
          <time dateTime={answer.verified_at}>{answer.verified_at}</time>
        </dd>
        <dt>Status</dt>
        <dd>{answer.status_line}</dd>
        <dt>Next step</dt>
        <dd>{answer.next_step}</dd>
      </dl>
      <p className="mt-3 border-t border-inzbc-navy/10 pt-2 text-xs text-slate-500">{answer.disclaimer}</p>
    </article>
  )
}
