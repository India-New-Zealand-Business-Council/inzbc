# Meetings

Where the team's ceremonies and client meetings are recorded.

Quick discussion happens on WhatsApp; anything that decides something lands here, so no decision
depends on one person's phone. This mirrors the rule in
[issue #21](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/21).

## Cadence

| Meeting | When | Format | Who |
|---|---|---|---|
| Team stand-up | Daily, 17:00 NZT | Online | Bhanu, Roshan, Paras |
| Sprint review and retrospective | Fortnightly | Online | Bhanu, Roshan, Paras |
| Client meeting | As needed, when a decision or blocker requires the client | Online | Sunil Kaushal (CEO), plus whoever owns the item |

Each minute records its own format, because an individual meeting may differ from the usual pattern.

## Where things go

| Directory | Holds |
|---|---|
| `standups/` | Daily team stand-ups, one file per week with a dated entry per day |
| `client/` | Client meetings with INZBC, one file per meeting |

Client meetings are kept separate from internal stand-ups. The client record should be readable on
its own without internal engineering chatter around it.

## Rules

- **A decision recorded here is provisional until it is an ADR.** Anything architectural goes to
  `docs/decisions/` with the alternatives considered; the minute then links to it.
- **Actions carry an owner and a due date.** An action without an owner is a wish.
- **Blockers are raised within 24 hours**, per the team contract — the stand-up is the backstop, not
  the only channel.
- **`[[to confirm]]` marks anything not yet verified.** Same convention as the rest of the repo: a
  fact that is owed is marked, not guessed.

## A note on these records

Minutes for the week of 20–26 July 2026 were written up after the fact, reconstructed from the
project's timestamped record — merged pull requests and their review threads, issue #21, Discussion
#24, and board activity. Each file states what it was reconstructed from. Items that were discussed
but left no written trace are marked `[[to confirm]]` rather than reconstructed from memory and
presented as fact.

From the week of 27 July onward, minutes are taken live during the meeting using
[`_template.md`](_template.md), on rotation as agreed in the team contract.
