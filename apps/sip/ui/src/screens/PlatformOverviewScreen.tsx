import { SipOverview } from '@dashboard/components/SipOverview'

/** One control, its enforcement point, and where it is proven. */
interface Control {
  name: string
  detail: string
  where: string
}

// Every row here names a control that refuses something, and the file that does the refusing.
// The point of the screen is that a viewer can check any line against the code rather than take
// the summary on trust, so nothing is listed that does not have an enforcement point.
const CONTROLS: Control[] = [
  {
    name: 'Human gates on the run lifecycle',
    detail:
      'Three of the eleven run states need a recorded human decision. No automated component can cross them.',
    where: 'persistence.apply_transition, run_authorisations',
  },
  {
    name: 'Separation of duties',
    detail:
      'Checked against recorded acts, not job titles. The analyst on a run cannot record its QA result.',
    where: 'decisions.record_qa, runs.analyst_id',
  },
  {
    name: 'Release predicate',
    detail:
      'Distribution can only be authorised on a report already approved, ruled Continue, and clear of Critical QA failures.',
    where: 'decisions.record',
  },
  {
    name: 'Append-only audit',
    detail:
      'Fifteen triggers refuse UPDATE and DELETE; the application role is granted INSERT and SELECT only. The trigger catches mistakes, the grant catches malice.',
    where: 'schema.sql, audit_role.sql',
  },
  {
    name: 'Model data boundary',
    detail:
      'Member records, CRM notes, Board papers and private messages are refused before a redaction policy is even read.',
    where: 'prompt_boundary.check_source',
  },
  {
    name: 'Fail-closed by default',
    detail:
      'Distribution off unless enabled, CORS allowing no origins unless configured, a missing redaction policy refusing the call.',
    where: 'hardening.py, model_gateway.py',
  },
]

// Counted from the running system, not asserted, with the command that produces each one. These
// drift every time the surface grows -- they were last wrong by four operations and seventy-eight
// tests -- so the commands are recorded here rather than in someone's memory. A number on this
// screen that nobody can reproduce is worth less than no number at all.
//
//   operations/paths  curl -s localhost:8000/openapi.json | python -c "import json,sys;
//                       d=json.load(sys.stdin);p=d['paths'];
//                       print(sum(len(v) for v in p.values()), len(p))"
//   routers           ls services/api/*.py | xargs grep -l 'APIRouter(' | wc -l
//   tables/keys       select count(*) from information_schema.tables
//                       where table_schema='public' and table_type='BASE TABLE';
//                     ...table_constraints where constraint_type='FOREIGN KEY';
//   triggers          select count(distinct tgname) from pg_trigger t
//                       join pg_class c on c.oid=t.tgrelid where not t.tgisinternal;
//   tests             pytest services apps scripts -q --collect-only
//   CI jobs           the job keys in .github/workflows/ci.yml
//   AI SDK            grep -rl 'anthropic\|openai' --include=*.py services apps scripts
const SCALE: { value: string; label: string; note: string }[] = [
  { value: '60', label: 'REST operations', note: 'across 51 paths, 12 routers' },
  { value: '26', label: 'database tables', note: '50 foreign keys, 31 CHECK constraints' },
  { value: '15', label: 'append-only triggers', note: 'plus TRUNCATE guards' },
  { value: '1,191', label: 'automated tests', note: 'against a real Postgres' },
  { value: '9', label: 'CI jobs', note: 'gating every merge' },
  { value: '1', label: 'file importing an AI SDK', note: 'of ~10,000 lines' },
]

export function PlatformOverviewScreen() {
  return (
    <div className="space-y-8">
      <section
        aria-labelledby="scale-heading"
        className="rounded-2xl border border-inzbc-ink/10 bg-white p-6 shadow-sm"
      >
        <h2 id="scale-heading" className="text-lg font-bold text-inzbc-navy">
          What the platform is
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-700">
          A governed pipeline that turns public news into an approved intelligence brief, where
          every step is refusable and no one person can do two adjacent jobs. The model is one
          narrow edge of it: a single file in roughly ten thousand lines calls a provider, and the
          FTA Explainer answers without calling one at all.
        </p>

        <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
          {SCALE.map((item) => (
            <div
              key={item.label}
              className="rounded-xl border border-inzbc-ink/10 bg-inzbc-mist/60 p-4"
            >
              <dt className="text-xs font-semibold uppercase tracking-wide text-inzbc-ink/60">
                {item.label}
              </dt>
              <dd className="mt-1 text-2xl font-extrabold text-inzbc-navy">{item.value}</dd>
              <dd className="mt-0.5 text-xs text-slate-600">{item.note}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section
        aria-labelledby="controls-heading"
        className="rounded-2xl border border-inzbc-ink/10 bg-white p-6 shadow-sm"
      >
        <h2 id="controls-heading" className="text-lg font-bold text-inzbc-navy">
          The controls, and where each one refuses
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-700">
          Each of these is enforced in code and covered by a test. A control that exists only in a
          document is a documented intention, not a control.
        </p>

        <ul className="mt-5 grid gap-3 sm:grid-cols-2">
          {CONTROLS.map((control) => (
            <li
              key={control.name}
              className="rounded-xl border border-inzbc-ink/10 bg-inzbc-mist/40 p-4"
            >
              <h3 className="font-semibold text-inzbc-ink">{control.name}</h3>
              <p className="mt-1 text-sm text-slate-700">{control.detail}</p>
              <p className="mt-2 font-mono text-xs text-inzbc-ink/55">{control.where}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="live-heading">
        <h2 id="live-heading" className="mb-3 text-lg font-bold text-inzbc-navy">
          Live run status
        </h2>
        <p className="mb-4 max-w-3xl text-sm text-slate-700">
          Read from the API against the real database, not a fixture. An empty state here means
          there is no run yet, which is itself the honest answer.
        </p>
        <SipOverview />
      </section>
    </div>
  )
}
