# Incident response

What to do when something goes wrong, written for one person acting alone at short notice.

INZBC is one person holding every role. A plan that assumes an on-call rota, a separate security
team, or a second approver is a plan that will not be followed, so this one assumes none of that.
The trade-off is stated rather than hidden: several steps below say "record it and continue"
where a larger organisation would say "escalate".

## What counts as an incident

Three kinds, and they need different first moves.

**Something published that should not have been.** An AI-drafted brief with an unsourced claim, a
figure that turned out wrong, a member's details in a public place. The damage is reputational and
it compounds while it is visible.

**Member or personal data reached somewhere it should not.** An external model, a log, a
third-party service, the wrong recipient. The obligation here is legal as well as practical: the
Privacy Act 2020 requires notification to the Privacy Commissioner and affected people where the
breach is likely to cause serious harm.

**A credential is exposed.** Committed to git, pasted into a chat, present in a screenshot, or
held by someone who has left.

## First hour

The order matters, and it is deliberately not "investigate first".

**1. Stop the bleeding.** Take the content down, disable the credential, or set
`users.active = false` on the account. All three are reversible; leaving them running is not.
Deactivating a user takes effect on their next request, because sessions re-read `users.active`
rather than trusting what was true at sign-in.

**2. Write down what you know, with times.** In `docs/incidents/` as a dated file. Memory of an
incident degrades within hours and the record is what the later decisions rest on. Include what
you did in step 1, because that is itself a change to the system.

**3. Only then work out what happened.** The audit trail is the tool: `audit_log` records every
write with actor, action, record and timestamp, and is append-only, so it cannot have been edited
to hide the incident. `decision_records` shows who approved what and when.

## For each kind

### Something published that should not have been

- Remove it. On the website that is a Wix Vibe edit and publish; there is no API, so it is a
  manual step and it is fast.
- Check whether it was distributed as well as published. `distribution_deliveries` is append-only
  and records what actually went out, which is a different question from what was approved.
- Record a correction rather than a silent edit. BR1 requires the approval trail to survive, and a
  quiet fix leaves the record saying something was approved that no longer exists.
- If the claim was factual and wrong, correct the source too. `docs/fta-source-corpus.md` is where
  FTA facts live; a page fixed without the corpus fixed will regenerate wrong.

### Member or personal data in the wrong place

- Contain first: revoke the credential, delete the log, recall the message if the channel allows.
- **Assess whether serious harm is likely.** That is the Privacy Act test and it is a judgement,
  not a checkbox. Consider sensitivity, how many people, whether the recipient is identifiable and
  trustworthy, and whether the data can still be misused.
- If serious harm is likely, notify the Privacy Commissioner and the affected people as soon as
  practicable. The Commissioner's online notification form is the route.
- Record the assessment either way, including a decision not to notify and why. An unrecorded
  decision not to notify is indistinguishable later from not having considered it.

### An exposed credential

- Rotate it before anything else. `docs/secrets-register.md` lists each credential with its owner
  and scope.
- Assume it was used. Check what it could reach and look for signs it did.
- If it was committed to git, rotating is necessary and not sufficient: the value stays in history.
  `gitleaks` runs before every commit here, which is what usually prevents this.

## After

Within a week, while it is still accurate:

- What made it possible, in one sentence, without blame. The useful answer is almost always a
  missing control rather than a careless person.
- What control would have caught it, and whether that control is worth its cost.
- Whether the audit trail was actually sufficient to reconstruct events. If it was not, that is a
  finding in its own right.

## Access review, quarterly

Small enough to do in ten minutes, which is the point.

- Every row in `users`: is this person still involved? If not, `active = false`.
- Every row in `user_roles`: does this person still need this role? Disable rather than delete, so
  the assignment history survives.
- Every entry in `docs/secrets-register.md`: is it still needed, still owned by INZBC, and inside
  its 90-day rotation?
- Every account in `docs/account-licence-register.md`: is it organisation-owned rather than
  personal?

Record the date it was done. A review nobody can prove happened has the same evidential value as
one that did not.

## Joiners, movers, leavers

Access that outlives the person is the most common way a small organisation loses control of a
system, and it is a slow failure rather than a dramatic one: nothing breaks, so nobody notices.

**Joining.** Create the `users` row, grant the narrowest role that lets them do the job, and add
them to whichever external accounts they actually need. Roles are additive and easy to grant later;
an over-broad grant on day one is never revisited.

**Moving.** Grant the new role and revoke the old one in the same sitting. A role kept "just in
case" is how one person quietly accumulates enough access to satisfy separation of duties alone —
which defeats the control without anyone deciding to.

**Leaving.** Within a day, and this is the list that matters:

1. `users.active = false`. This is the single most effective step, because it takes effect on the
   next request rather than at next sign-in, and it covers every API route at once.
2. Remove them from the GitHub organisation.
3. Remove their admin rights on Wix, the registrar, Member Jungle, Zoho Backstage, EmailOctopus and
   every social account.
4. Rotate any shared credential they held. Removing a person does not un-know a secret.
5. Check the recovery paths: is their personal email or phone still the reset route for any
   account? This survives every other step on this list and is the one that gets missed.

**Do not delete the user row.** Deactivate it. The audit trail references `users.id`, and deleting
the person removes the meaning from every action they recorded — which is precisely the history
worth keeping after someone leaves.

**This engagement ends.** The team is here for sixteen weeks, so this is a scheduled event rather
than a hypothetical. It runs at handover, per the handover pack (#291), and the register's annual
supplier review is the backstop that catches anything the checklist above missed.

## What this does not cover

Availability incidents. The platform is on free-tier hosting for this engagement and there is no
uptime commitment to anyone, so an outage is an inconvenience rather than an incident. That
changes if INZBC runs this in production after handover, and the plan should change with it.
