import type { Answer as AnswerModel } from '../api/client'

/**
 * Renders one sourced FTA finding. Every field here is evidence or the presentation the
 * Information Standard requires alongside it — citation, effective date, confidence and the
 * approved disclaimer are not optional decoration.
 */
export function Answer({ answer }: { answer: AnswerModel }) {
  return (
    <article className="fta-answer" aria-labelledby={`answer-${answer.topic}`}>
      <h3 id={`answer-${answer.topic}`}>{answer.topic}</h3>
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
