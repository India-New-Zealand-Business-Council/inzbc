"""Postgres persistence adapter for SIP candidates (#121).

Split from `persistence.py` (which is `runs`-specific by its own docstring) rather than folded in,
since candidates are a distinct table with no `version` column - `candidates` has no optimistic
concurrency to reason about, so there is no compare-and-swap contract shared with `RunRepository`
worth unifying.

**Why explicit commands, not a blanket PATCH** (the point of #121 itself): a PATCH can't produce a
meaningful audit record because the server never learns which action the caller intended - a row
that went from `signal=None` to `signal=Critical` and `verification=Unverified` to `Verified` in
one PATCH could be a scoring pass, a verification pass, or both, and `audit_log.action` would have
to guess. Each method here writes its own named action (`candidate.verify`, `candidate.score`,
`candidate.route`, `candidate.merge`), same transaction as the update, same pattern
`RunRepository.apply_transition` already established for runs (#118).

`PATCH /api/candidates/:id` (mechanical scoring during collection, via
`apps/sip/collector/assessment.py`) is a **separate, still-valid path** - ADR-0005 explicitly kept
it, calling it "unrelated to decision authority" (0005 §7). This module does not replace it; it
adds the commands that do need a named decision on the record.

**The verification gate is stronger here than the client-side version.**
`apps/sip/collector/verification.py`'s `enforce_verification_gate` is reused unchanged, but the
collector-side caller (`assessment.py`) has no live read of the candidate and has to be told
`current_signal`/`current_verification` explicitly, raising `MissingCurrentSignalError` when
neither the patch nor the caller supplies one - an unknown current state must not be assumed safe.
This module always has a live row (it reads before it writes, same transaction), so "current" is
never unknown and that failure mode does not exist here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from apps.sip.collector.verification import enforce_verification_gate
from apps.sip.pipeline.models import SignalStrength, SourceConfidence, VerificationState
from services.api.audit import record_audit
from services.api.auth import canonical_actor


class _Unset:
    """Sentinel for "this scoring field was not supplied", which `None` cannot express.

    `ScoreIn` defaults every scoring field to `None`, so before this existed a caller who sent
    only `nz_relevance` had the other four written as NULL over whatever was stored (#323). There
    was no value meaning "leave this alone": omitting the key and sending an explicit null reached
    `record_score` identically. The route now passes only the fields present in
    `model_fields_set`, and everything else stays `UNSET` and is left out of the UPDATE entirely.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return "UNSET"


UNSET = _Unset()


class SelfVerificationError(RuntimeError):
    """The actor is verifying a candidate they captured or assessed.

    Its own type rather than a generic refusal, because a caller should be able to say which
    control refused. This is BR8, not a permissions problem, and telling an operator "forbidden"
    when the real answer is "you cannot check your own work" sends them to the wrong fix.
    """


@dataclass(frozen=True)
class CandidateRecord:
    id: str
    run_id: str
    headline: str
    source_id: str | None
    url: str | None
    summary: str | None
    published_at: str | None
    captured_at: str
    in_coverage_window: bool | None
    nz_relevance: int | None
    india_relevance: int | None
    member_relevance: int | None
    signal: SignalStrength | None
    confidence: SourceConfidence | None
    verification: VerificationState
    duplicate_of: str | None
    included: bool | None
    reason: str | None
    proposed_routing: str | None


_SELECT_COLUMNS = (
    "id, run_id, headline, source_id, url, summary, published_at, captured_at, "
    "in_coverage_window, nz_relevance, india_relevance, member_relevance, signal, "
    "confidence, verification, duplicate_of, included, reason, proposed_routing"
)


def _row_to_record(row: dict) -> CandidateRecord:
    return CandidateRecord(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        headline=row["headline"],
        source_id=str(row["source_id"]) if row["source_id"] else None,
        url=row["url"],
        summary=row["summary"],
        published_at=row["published_at"].isoformat() if row["published_at"] else None,
        captured_at=row["captured_at"].isoformat(),
        in_coverage_window=row["in_coverage_window"],
        nz_relevance=row["nz_relevance"],
        india_relevance=row["india_relevance"],
        member_relevance=row["member_relevance"],
        signal=SignalStrength(row["signal"]) if row["signal"] else None,
        confidence=SourceConfidence(row["confidence"]) if row["confidence"] else None,
        verification=VerificationState(row["verification"]),
        duplicate_of=str(row["duplicate_of"]) if row["duplicate_of"] else None,
        included=row["included"],
        reason=row["reason"],
        proposed_routing=row["proposed_routing"],
    )


class CandidateRepository:
    """Postgres-backed persistence for `candidates`. See module docstring for the audit contract."""

    def __init__(self, database_url: str | None = None):
        # Read at construction, not at import time - same reasoning as RunRepository.
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def capture(
        self,
        *,
        run_id: str,
        headline: str,
        source_id: str | None,
        url: str | None,
        summary: str | None,
        published_at: str | None,
        in_coverage_window: bool | None,
        actor_id: str,
    ) -> CandidateRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "insert into candidates (run_id, headline, source_id, url, summary, "
                "published_at, in_coverage_window, captured_by) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s) "
                f"returning {_SELECT_COLUMNS}",
                (run_id, headline, source_id, url, summary, published_at, in_coverage_window,
                 actor_id),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="candidate.capture",
                record_type="candidates",
                record_id=str(row["id"]),
                new_value=headline,
                reason="candidate captured",
            )
            conn.commit()
        return _row_to_record(row)

    def get(self, candidate_id: str) -> CandidateRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"select {_SELECT_COLUMNS} from candidates where id = %s", (candidate_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"no candidate {candidate_id!r}")
        return _row_to_record(row)

    def list_for_run(self, run_id: str) -> list[CandidateRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_SELECT_COLUMNS} from candidates where run_id = %s "
                "order by captured_at desc",
                (run_id,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def _get_locked(self, conn: psycopg.Connection, candidate_id: str) -> dict:
        """Read and lock the current row inside the caller's transaction.

        `for update` is what the name always promised and did not do. Every separation-of-duties
        and verification check in this module reads the row, decides, then writes; without the
        lock a concurrent `record_score` could set `assessed_by` between another caller's read
        and its update, so the decision was made against a row that no longer existed by the time
        it was acted on. Comments elsewhere in this file cited a lock that was not being taken.

        There is still no `version` column on `candidates`, so this is pessimistic locking rather
        than the compare-and-swap `RunRepository` uses for `runs`. That is the right trade here:
        these are short transactions with no human step inside them, unlike a run sitting in
        `Awaiting CEO Decision` for hours.
        """
        row = conn.execute(
            f"select {_SELECT_COLUMNS} from candidates where id = %s for update",
            (candidate_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"no candidate {candidate_id!r}")
        return row

    @staticmethod
    def _require_candidate_exception(
        conn: psycopg.Connection,
        *,
        sod_exception_id: str | None,
        candidate_id: str,
        actor_id: str,
        act: str,
    ) -> None:
        """Permits a self-verification only against a recorded, still-valid exception.

        Without this the control has no exception path at all, and INZBC is one person holding
        every role. A rule that refuses outright would make verification impossible for the only
        operator there is, and a control that blocks all legitimate work gets switched off, which
        leaves the system worse than before. Recording the exception keeps the audit trail honest:
        it says one person carried this candidate end to end, and who authorised that.

        Checked inside the caller's transaction, under the same row lock, so an exception cannot
        be inserted between the check and the update.
        """
        if sod_exception_id is None:
            raise SelfVerificationError(
                f"{actor_id!r} {act} this candidate and may not also verify it. Separation of "
                "duties is what the verification record evidences; a candidate one person can "
                "carry from capture to verified evidences nothing. Cite an approved "
                "candidate_sod_exceptions row if a single operator is unavoidable."
            )

        # Joined through `users`, so an exception naming a deactivated account authorises
        # nothing. Same reasoning as `DecisionRepository._require_valid_exception`: `approved_by`
        # is a plain foreign key, and an approval from someone who has left is not an approval.
        exception = conn.execute(
            "select e.approved_by, e.review_date < current_date as lapsed, "
            "       u.active as approver_active "
            "from candidate_sod_exceptions e join users u on u.id = e.approved_by "
            "where e.id = %s and e.candidate_id = %s and e.actor_id = %s",
            (sod_exception_id, candidate_id, actor_id),
        ).fetchone()
        if exception is None:
            raise SelfVerificationError(
                f"exception {sod_exception_id!r} does not cover {actor_id!r} verifying candidate "
                f"{candidate_id!r}. An exception authorises one act, not a category."
            )
        if canonical_actor(exception["approved_by"]) == canonical_actor(actor_id):
            raise SelfVerificationError(
                f"exception {sod_exception_id!r} was approved by the same person it exempts. "
                "A self-approved exception is self-approval with an extra step."
            )
        if not exception["approver_active"]:
            raise SelfVerificationError(
                f"exception {sod_exception_id!r} was approved by an account that is no longer "
                "active. An approval from someone who has left is not a current approval."
            )
        if exception["lapsed"]:
            raise SelfVerificationError(
                f"exception {sod_exception_id!r} has passed its review date and has lapsed. "
                "A lapsed approval is not a current one."
            )

    def record_verification(
        self,
        candidate_id: str,
        verification: VerificationState,
        *,
        actor_id: str,
        reason: str,
        sod_exception_id: str | None = None,
    ) -> CandidateRecord:
        """Sets `verification`. Refuses (via `enforce_verification_gate`) a downgrade away from
        Verified/Partially Verified on a candidate whose *current* signal is High/Critical - the
        live read means this is never guessing, unlike the collector-side gate.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            current = self._get_locked(conn, candidate_id)
            current_signal = SignalStrength(current["signal"]) if current["signal"] else None
            enforce_verification_gate(current_signal, verification)

            # BR8, checked against the acts rather than the roles. Holding Reviewer says a person
            # may verify something; it cannot say whether they are verifying their own work, and
            # that is the whole of the control. `require_roles` is an OR over the roles held, and
            # the steady state after the placement is one person holding all of them, so a role
            # check alone let one principal capture, score and verify the same candidate end to
            # end. No role exempts anyone from this, including SIP Owner: an exemption that the
            # most senior person can grant themselves is not a control.
            #
            # Checked inside the same transaction as the row lock, so a concurrent capture or
            # score cannot slip in between the read and the update.
            provenance = conn.execute(
                "select captured_by, assessed_by from candidates where id = %s",
                (candidate_id,),
            ).fetchone()
            verifier = canonical_actor(actor_id)
            for column, act in (("captured_by", "captured"), ("assessed_by", "assessed")):
                performer = canonical_actor(provenance[column])
                if performer is not None and performer == verifier:
                    self._require_candidate_exception(
                        conn,
                        sod_exception_id=sod_exception_id,
                        candidate_id=candidate_id,
                        actor_id=actor_id,
                        act=act,
                    )
                    break

            row = conn.execute(
                f"update candidates set verification = %s, verified_by = %s where id = %s "
                f"returning {_SELECT_COLUMNS}",
                (verification.value, actor_id, candidate_id),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="candidate.verify",
                record_type="candidates",
                record_id=candidate_id,
                old_value=current["verification"],
                new_value=verification.value,
                reason=reason,
            )
            conn.commit()
        return _row_to_record(row)

    def record_score(
        self,
        candidate_id: str,
        *,
        nz_relevance: int | None | _Unset = UNSET,
        india_relevance: int | None | _Unset = UNSET,
        member_relevance: int | None | _Unset = UNSET,
        signal: SignalStrength | None | _Unset = UNSET,
        confidence: SourceConfidence | None | _Unset = UNSET,
        actor_id: str,
        reason: str,
    ) -> CandidateRecord:
        """Sets the scoring fields that were supplied, and leaves the rest as they are.

        Refuses setting a High/Critical `signal` on a candidate whose *current* verification is
        not Verified/Partially Verified - the gate this candidate would otherwise carry unenforced
        from capture straight through to a report.

        A field left `UNSET` is not written at all (#323). Passing `None` explicitly still clears
        the column, so "clear this" remains expressible; it just is no longer the same thing as
        saying nothing.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            current = self._get_locked(conn, candidate_id)
            current_verification = VerificationState(current["verification"])
            # Only gate when a signal is actually being set. An unsupplied signal changes nothing,
            # so the gate that guards *raising* a signal has nothing to guard.
            if not isinstance(signal, _Unset):
                enforce_verification_gate(signal, current_verification)

            # The other direction of BR8, and the one the first version missed. Guarding only
            # verification left a deterministic bypass: A captures, B verifies, then B scores.
            # Scoring after the fact makes B both the assessor and the verifier of the same
            # candidate, and no race is needed to do it. The separation has to hold whichever
            # order the acts happen in, so the assessor is checked against the recorded verifier
            # exactly as the verifier is checked against the assessor.
            provenance = conn.execute(
                "select verified_by from candidates where id = %s", (candidate_id,)
            ).fetchone()
            verifier = canonical_actor(provenance["verified_by"])
            if verifier is not None and verifier == canonical_actor(actor_id):
                raise SelfVerificationError(
                    f"{actor_id!r} verified this candidate and may not also score it. Scoring "
                    "after verifying makes one person both the assessor and the check on that "
                    "assessment, which is the same defect as verifying your own work."
                )

            # Column names are fixed literals from this dict, never caller input, so composing
            # the SET clause here cannot carry anything injectable. Values stay parameterised.
            supplied: dict[str, object] = {}
            for column, value in (
                ("nz_relevance", nz_relevance),
                ("india_relevance", india_relevance),
                ("member_relevance", member_relevance),
                ("signal", signal),
                ("confidence", confidence),
            ):
                if isinstance(value, _Unset):
                    continue
                supplied[column] = value.value if hasattr(value, "value") else value

            if not supplied:
                raise ValueError(
                    "record_score was called with no scoring fields; nothing to record. Use a "
                    "different command if the intent was only to note a reason."
                )

            assignments = ", ".join(f"{column} = %s" for column in supplied)
            row = conn.execute(
                f"update candidates set {assignments}, assessed_by = %s where id = %s "
                f"returning {_SELECT_COLUMNS}",
                (*supplied.values(), actor_id, candidate_id),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="candidate.score",
                record_type="candidates",
                record_id=candidate_id,
                old_value=current["signal"],
                # Reports what the signal is after this call: the new one when supplied, the
                # unchanged current one when it was not, rather than a null that would read as
                # "the signal was cleared".
                new_value=supplied.get("signal", current["signal"]),
                reason=reason,
            )
            conn.commit()
        return _row_to_record(row)

    def record_routing(
        self,
        candidate_id: str,
        *,
        proposed_routing: str | None,
        included: bool | None,
        actor_id: str,
        reason: str,
    ) -> CandidateRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            current = self._get_locked(conn, candidate_id)

            # REQ-G-02 applied where it decides something. The gate was enforced on scoring, so a
            # High or Critical signal could not be *set* on an unverified candidate, but nothing
            # checked it again at inclusion: a candidate scored High while verified, then moved
            # back to Unverified, could still be marked `included` and reach the brief. Inclusion
            # is the act that puts a claim in front of the CEO, so it is the last point where the
            # rule can still mean anything.
            #
            # Checked against the live row under the same lock, so a concurrent verification
            # change cannot slip between the read and the update.
            if included:
                current_signal = (
                    SignalStrength(current["signal"]) if current["signal"] else None
                )
                current_verification = (
                    VerificationState(current["verification"]) if current["verification"] else None
                )
                enforce_verification_gate(current_signal, current_verification)

            row = conn.execute(
                "update candidates set proposed_routing = %s, included = %s where id = %s "
                f"returning {_SELECT_COLUMNS}",
                (proposed_routing, included, candidate_id),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="candidate.route",
                record_type="candidates",
                record_id=candidate_id,
                old_value=current["proposed_routing"],
                new_value=proposed_routing,
                reason=reason,
            )
            conn.commit()
        return _row_to_record(row)

    def merge(
        self,
        candidate_id: str,
        duplicate_of: str,
        *,
        actor_id: str,
        reason: str,
    ) -> CandidateRecord:
        """Marks `candidate_id` as a duplicate of `duplicate_of` and excludes it
        (`included = false`) - a duplicate must not also count as a separate included finding.
        Refuses merging a candidate into itself, and refuses if `duplicate_of` does not exist
        (the foreign key would refuse it too, but a `KeyError` here tells the caller which id was
        bad, rather than a raw integrity-constraint error crossing the HTTP boundary).
        """
        if candidate_id == duplicate_of:
            raise ValueError(f"candidate {candidate_id!r} cannot be a duplicate of itself")
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            current = self._get_locked(conn, candidate_id)
            target = conn.execute(
                "select 1 from candidates where id = %s", (duplicate_of,)
            ).fetchone()
            if target is None:
                raise KeyError(f"no candidate {duplicate_of!r} to merge into")

            row = conn.execute(
                "update candidates set duplicate_of = %s, included = false where id = %s "
                f"returning {_SELECT_COLUMNS}",
                (duplicate_of, candidate_id),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="candidate.merge",
                record_type="candidates",
                record_id=candidate_id,
                old_value=current["duplicate_of"],
                new_value=duplicate_of,
                reason=reason,
            )
            conn.commit()
        return _row_to_record(row)
