import type { DailyBriefReport } from '../domain'
import { archiveFixture } from '../lib/fixtures'

interface Props {
  report: DailyBriefReport
}

/**
 * docs/sip-ui-spec.md Screen 4: a read-only status surface, not a workflow screen — "no write
 * controls of any kind ... If a field is empty (e.g. no send recorded yet), it shows as pending,
 * not as an error." Unlike the QA/CEO screens this has no entry-state gate: asking "did today's
 * brief go out" is meaningful at any point in a run's life, and the honest answer earlier on is
 * simply "pending," not "not reachable."
 *
 * `report.distribution.recipient` is the SIP-186 field as sourced (a single authorised recipient/
 * list reference, e2 in the QA checklist) — there is no "recipient count" in the source template,
 * so this renders that field as-is rather than inventing a numeric count it doesn't have.
 */
export function DistributionStatusScreen({ report }: Props) {
  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-inzbc-navy">Distribution Status</h2>
        <p className="mt-1 text-sm text-slate-600">
          Read-only status for run {report.runId} — no write controls on this screen.
        </p>
      </div>

      <dl className="grid gap-3 rounded-md border border-slate-200 bg-white p-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs text-slate-500">Current state</dt>
          <dd className="text-sm font-semibold text-inzbc-navy">{report.state}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Report / brief date</dt>
          <dd className="text-sm font-semibold text-inzbc-navy">{report.reportDate || 'Pending'}</dd>
        </div>
      </dl>

      <div className="rounded-md border border-slate-200 bg-white p-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">QA result</h3>
        {report.qa ? (
          <dl className="mt-2 space-y-1 text-sm text-slate-700">
            <div>
              Result: <strong>{report.qa.result}</strong>
            </div>
            <div>Reviewer: {report.qa.reviewer}</div>
            <div>Timestamp: {report.qa.timestamp}</div>
            {report.qa.criticalFailuresFound ? <div>Critical failures: {report.qa.criticalFailuresFound}</div> : null}
          </dl>
        ) : (
          <p className="mt-2 text-sm text-slate-500">Pending — QA has not been recorded yet.</p>
        )}
      </div>

      <div className="rounded-md border border-slate-200 bg-white p-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">CEO decision</h3>
        {report.decision ? (
          <dl className="mt-2 space-y-1 text-sm text-slate-700">
            <div>
              Decision: <strong>{report.decision.decision}</strong>
            </div>
            <div>Reason: {report.decision.reason}</div>
            <div>Recorded: {report.decision.decidedAt}</div>
            <div>Against version: {report.decision.reportVersion}</div>
            <div>
              Distribution authorised:{' '}
              <strong>
                {report.decision.distributionDecidedAt
                  ? report.decision.distributionAuthorised
                    ? 'Yes'
                    : 'No'
                  : 'Pending'}
              </strong>
            </div>
          </dl>
        ) : (
          <p className="mt-2 text-sm text-slate-500">Pending — no CEO decision recorded yet.</p>
        )}
      </div>

      <div className="rounded-md border border-slate-200 bg-white p-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">Distribution record</h3>
        {report.distribution ? (
          <dl className="mt-2 space-y-1 text-sm text-slate-700">
            <div>
              Sent: <strong>{report.distribution.sent ? 'Yes' : 'No'}</strong>
            </div>
            <div>Sender: {report.distribution.sender}</div>
            <div>Recipient: {report.distribution.recipient}</div>
            <div>Send time: {report.distribution.sendTime}</div>
            <div>Channel: {report.distribution.channel}</div>
            <div>Delivery result: {report.distribution.deliveryResult}</div>
            <div>Close-out status: {report.distribution.closeOutStatus}</div>
          </dl>
        ) : (
          <p className="mt-2 text-sm text-slate-500">
            Pending — no send recorded yet. Manual send happens outside this application
            (docs/sip/operator-guide.md Step 13); this screen only reflects what has already been
            recorded.
          </p>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-inzbc-navy">Run archive</h3>
        <p className="mt-1 text-xs text-slate-500">
          Past runs — for local development only, standing in for a not-yet-built history list
          (no `GET /api/reports` list endpoint exists yet).
        </p>
        <div className="mt-2 overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold text-slate-500">
                <th scope="col" className="px-3 py-2">
                  Run
                </th>
                <th scope="col" className="px-3 py-2">
                  Date
                </th>
                <th scope="col" className="px-3 py-2">
                  State
                </th>
                <th scope="col" className="px-3 py-2">
                  QA
                </th>
                <th scope="col" className="px-3 py-2">
                  Decision
                </th>
                <th scope="col" className="px-3 py-2">
                  Distribution
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {archiveFixture().map((run) => (
                <tr key={run.runId}>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">{run.runId}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">{run.reportDate}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">{run.state}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">{run.qaResult ?? 'Pending'}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">{run.decision ?? 'Pending'}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">
                    {run.distributionAuthorised === null ? 'Pending' : run.distributionAuthorised ? 'Yes' : 'No'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
