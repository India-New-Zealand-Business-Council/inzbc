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
| `SIP_DECISION_SIGNING_KEY` | `apps/sip/core/audit_seal.py`, `services/api/persistence.py` | **Yes** | Optional, at least 32 bytes. Set, gated decisions are signed when recorded and verified on replay. Rotating it makes rows signed with the old key fail replay, so rotation needs a re-verification plan first. |
| `SIP_REQUIRE_SIGNED_DECISIONS` | `apps/sip/core/audit_seal.py` | No | Optional. `true` refuses an unsigned gated transition, both when recording and on replay. Needs the key. |

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

**Routine rotation of provider credentials (not exposed credentials or the decision-signing key):**
Use this sequence for a planned rollover where temporary overlap is acceptable:

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

## Exposure response, 24 Oct 2026

Credentials pasted into chat must be revoked at their issuing provider. Deleting a chat message,
removing a GitHub secret or changing a local variable does not revoke the credential.

1. Revoke the exposed Google app password first, in the affected Google account's app-password
   settings. This is a human account action; no revocation has been verified by this document.
2. Inventory the other exposed credentials by provider and purpose without copying their values.
   Revoke each exposed credential at its provider. Exposure takes priority over the routine
   overlap sequence above; accept a temporary service interruption if necessary.
3. Re-issue only credentials needed by an approved workload. Configure replacements through its
   environment secret store, with least scope and separate environments. Never put values in
   chat, this repository, a browser bundle, screenshots or a command transcript.
4. Verify a minimal approved call from the consuming environment, and record provider, credential
   identifier (not value), revocation date, replacement destination and verification outcome.
   Keep production launch and distribution disabled while #189 remains outstanding.

## Decision-signing key: rollout and rotation prerequisites

The deployed configuration has not been inspected or changed. The following is an operator plan,
not evidence that a key is set or that enforcement is enabled.

### Initial rollout

1. Inventory each deployed environment and its database, application version and server secret
   store. Confirm migration 0006 is applied. Identify open runs created before #448; close them
   through the normal authorised workflow before enabling enforcement. Closing a run does not
   make its historical unsigned decisions signed: retain a documented legacy replay path.
2. A human operator generates a cryptographically random key with at least 32 bytes of entropy
   directly in the secret-management workflow. Set `SIP_DECISION_SIGNING_KEY` server-side only;
   the implementation uses the UTF-8 bytes of that value. Keep environments separate. Do not
   echo, commit or expose it to the agent loop, model or frontend.
3. With enforcement still off, exercise an authenticated gated transition in staging, read it
   back and rehydrate it under the configured key. Verify the stored signature, a valid sealed
   rehearsal, refusal of tampering and refusal when a signed record is read without its key.
4. Once the legacy-run inventory is resolved, enable `SIP_REQUIRE_SIGNED_DECISIONS=true` in
   staging. Confirm an unsigned gated transition is refused and a legitimate signed one works.
   Recheck the application's legacy-history requirements before the tech lead enables it in
   production. This flag is not production launch approval; #55 and #189 remain separate gates.
5. Record environment, version, operator, date, resolved legacy run IDs and verification results
   without secrets. Do not mark rollout complete until those checks are observed.

### Rotation: preserve verifiability before changing the key

The current implementation reads one key and has no key ID or verification key ring. Replacing
that value makes old decision signatures and audit seals fail verification. Closing old runs
alone does not fix that. Do not use the provider-credential rollover above for this key.

1. Inventory all signed decisions, stored rehearsal logs and backups. Take an access-controlled
   immutable snapshot and retain the old key in the restricted secret store while it is needed
   for verification. Preserve the original artefacts and their hashes; do not rewrite history.
2. Before any planned rotation, verify every existing signature and seal with the current key
   using the current replay paths. Record counts, failures, artefact identifiers and software
   version; stop on a failure. Reverification proves the snapshot only while the key is trusted.
3. Implement and review a versioned key-ID/verification-key-ring path before changing the active
   signing key, or agree a separately reviewed offline archival-verification procedure. Neither
   capability is implemented by this document. Test mixed old/new records, restart, backup
   restore and rejection of unknown or revoked keys in staging.
4. Change the active signing key only after historical reads and replay have passed under the
   selected procedure. Keep old keys verification-only in the approved isolated workflow for as
   long as retained history requires them. Record the cutover and evidence before retiring any key.
5. If the signing key is exposed, pause affected signing and treat signatures under it as
   potentially forged. Preserve incident evidence and decide the trusted checkpoint and recovery
   procedure before resuming. A newly generated key cannot retroactively establish old authorship.

Per-approver asymmetric signatures remain ADR-0010's conditional next step. Do not issue staff
keys or build a new signing workflow until INZBC confirms that requirement.
