# Secrets register and rotation policy

Names and scopes only. **No value ever appears in this repository**, including in an example file,
a comment, a test fixture or a commit message.

Written for issue #115, which blocks the end-to-end collector run in Roshan's worklog.

## What the code actually reads

Every environment variable the platform reads, found by grepping `os.getenv` and `os.environ`
across `apps`, `services` and `scripts` rather than from memory.

| Name | Read by | Secret? | Required |
|---|---|---|---|
| `OPENAI_API_KEY` | `services/api/model_gateway.py` | **Yes** | For any live model call. Absent, the gateway raises rather than fabricating. |
| `DATABASE_URL` | `services/api/persistence.py`, the persistence tests | **Yes** (contains a password) | For persistence. Tests skip cleanly without it. |
| `SIP_MODEL_NAME` | `services/api/model_gateway.py` | No | Optional. Defaults to `gpt-4.1-mini`. |
| `REDACTION_POLICY_PATH` | `services/api/redaction.py` | No (a path) | **Yes for any model call.** Absent, every call is refused. See `docs/redaction-policy.md`. |

CI supplies `DATABASE_URL` itself for the Postgres service container, with throwaway credentials
defined inline in `ci.yml`. Those are not secrets and must never be reused anywhere real.

## Two findings that need action

**Six secrets on `inzbc` are unused.** `EMAIL_FROM`, `EMAIL_PASSWORD`, `EMAIL_TO`,
`GOOGLE_SCRIPT_URL`, `NEWSAPI_KEY` and `OPENAI_API_KEY` are set as repository secrets, and **no
workflow in this repository reads any of them**. Grep `.github/` for `secrets.` and it returns
nothing.

They appear to have been copied from `daily-india-nz-news-agent`, which holds the same six plus
`PERPLEXITY_API_KEY`. An unused credential is pure attack surface: it can leak but cannot be missed
if it does. Either wire them up or remove them from this repository.

**The same credentials live in two repositories.** That doubles the rotation burden and makes it
possible to rotate one and believe you are done. If both genuinely need the same key, it belongs at
the organisation level, set once and inherited, not pasted twice. Organisation secrets need an org
admin, so this is Sunil's to action.

## Where each secret belongs

| Secret | Scope | Why |
|---|---|---|
| `OPENAI_API_KEY` | **Organisation**, both repos | Both the collector and the platform gateway call the same account. One value, one rotation. |
| `PERPLEXITY_API_KEY` | Repository, news agent only | Only the collector uses it today. Move to org if the gateway gains a second provider (#36). |
| `NEWSAPI_KEY` | Repository, news agent only | Collection engine. Nothing in this repo reads it. |
| `EMAIL_FROM` / `EMAIL_TO` / `EMAIL_PASSWORD` | Repository, news agent only | The daily brief send. Manual distribution during the controlled launch means the platform does not send mail. |
| `GOOGLE_SCRIPT_URL` | Repository, news agent only | Collection-side integration. |
| `DATABASE_URL` | Repository, per environment | Different value per environment; never shared between staging and anything real. |

## Rotation policy

**Every 90 days, and immediately on any of these:** someone with access leaves the project, a value
appears anywhere it should not (a log, a screenshot, a shared document, a commit), a provider
reports suspicious use, or the capstone team hands over.

The 90-day clock starts at the `Updated` timestamp GitHub shows in `gh secret list`. As at 1 August
2026 every secret in both repositories dates from 22 to 25 July 2026, so the first scheduled
rotation falls in late October 2026.

**How to rotate**, in this order, because the reverse order causes an outage:

1. Create the new credential at the provider. Do not revoke the old one yet.
2. Update the secret in GitHub, at the org level where the table above says organisation.
3. Run the workflow that uses it and confirm it succeeds.
4. Revoke the old credential at the provider.
5. Record the date and who did it in `docs/wix-changes-log.md`'s sibling for infrastructure, or in
   the handover pack if that does not exist yet.

**Handover.** `client-answers.md` A1 and A4 say every account and credential is INZBC-owned and that
Sunil is the initial administrator. At the end of the placement every secret must be rotated by
INZBC, not merely transferred, because the outgoing team has seen the current values. That is a
rotation event, not an administrative one.

## Rules

- No value in the repository. Not in `.env.example`, not in a comment, not in a test.
- A secret scan runs before pushing (`PROJECT-RULES.md`). `gitleaks` is not currently installed on every
  machine, which is a gap worth closing.
- Personal accounts hold nothing of record (`client-answers.md` A1). A secret that exists only in
  one person's local environment is an outage waiting for that person to be unavailable, which is
  what #115 exists to prevent.
- Least scope that works: repository over organisation unless two repositories genuinely share the
  credential, and environment-scoped where GitHub supports it.

## Still with INZBC

- Promote `OPENAI_API_KEY` to an organisation secret. Needs an org admin.
- Decide whether the six unused secrets on `inzbc` are removed or wired up.
- Confirm the billing account behind `OPENAI_API_KEY` is INZBC-owned, not a developer's
  (`client-answers.md` B1 proposes this; it is not confirmed).
