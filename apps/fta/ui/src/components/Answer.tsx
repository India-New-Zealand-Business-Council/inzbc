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
    <article className="fta-answer" aria-labelledby={headingId}>
      <h3 id={headingId}>{answer.topic}</h3>
      <p className="fta-meta">{answer.sector}</p>
      <p>{answer.treatment}</p>
      {answer.notes ? <p className="fta-meta">{answer.notes}</p> : null}
      <dl className="fta-meta">
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
      <p className="fta-disclaimer">{answer.disclaimer}</p>
    </article>
  )
}
