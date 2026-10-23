"""Replay baseline for the SIP coordinator agent's audit log (#62).

Three measurements over a set of generated runs:

1. **Replay.** `replay_agent_audit` rebuilds each run from its audit log alone, with no model
   call. It must accept every genuine log and reconstruct the same final state and transition
   history.
2. **Re-execution.** The same scripted model outputs, fed to a fresh agent, must produce the same
   audit log (ignoring wall-clock timestamps). This checks the code adds no nondeterminism of its
   own; the model's choices are the only input that varies a run.
3. **Tamper detection.** Each genuine log is altered in one way at a time, and the replay must
   reject the altered copy. Mutations that touch a safety property (a gate, a source check, a
   verification, the brief) are reported separately from those that only touch metadata (actor
   names, timestamps, free-text reasons), because replay is designed to catch the first kind.

    uv run python -m apps.sip.core.eval.replay_fidelity            # print the summary
    uv run python -m apps.sip.core.eval.replay_fidelity --write    # also save the results
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from apps.sip.collector.source_register import MANDATORY_SOURCES
from apps.sip.core.agent_loop import (
    AgentOrchestrator,
    AgentRunAuditLog,
    parse_tool_proposal,
    replay_agent_audit,
)
from apps.sip.core.eval._fixtures import (
    MEASUREMENT_KEY,
    WINDOW,
    all_mandatory_outcomes,
    authorised_orchestrator,
    proposal,
    redaction_policy,
    score_output,
    scripted_gateway,
    source_lookup,
)
from apps.sip.core.orchestrator import CorruptHistory, HumanDecision, TransitionRecord
from apps.sip.pipeline.models import (
    Candidate,
    RunState,
    SignalStrength,
    VerificationState,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_RUNS = 200
DEFAULT_SEED = 20261024

# Proposals the generated runs slip in at random points. Each must be refused; the refusal is
# audited, so replay has to cope with refused records interleaved with accepted ones.
_NOISE = (
    proposal("advance_state", {"target_state": "Distributed"}),
    proposal("advance_state", {"target_state": "Awaiting CEO Decision"}),
    proposal("fetch_candidates", {}),
    proposal("lock_coverage_window", {"coverage_start_utc": WINDOW[0],
                                      "coverage_end_utc": WINDOW[0]}),
)


@dataclass(frozen=True)
class Script:
    """One generated run: the feed the collector returns and the model's outputs, in order."""

    run_id: str
    feed: tuple[dict, ...]
    steps: tuple[tuple[str, str | None], ...]  # (proposal, score output consumed by it, if any)


def generate(seed: int, index: int) -> Script:
    rng = random.Random(seed * 100_003 + index)
    run_id = f"RUN-REPLAY-{index:04d}"
    feed: list[dict] = []
    plans: list[tuple[str, SignalStrength, bool]] = []
    for number in range(rng.randint(0, 5)):
        verified = rng.random() < 0.4
        candidate_id = f"cand-{number}"
        item: dict[str, object] = {
            "id": candidate_id,
            "headline": f"Generated item {number}",
            "source_code": rng.choice(MANDATORY_SOURCES).source_id,
            "url": f"https://example.org/{run_id}/{number}",
            "summary": "Generated summary.",
            "published_at": "2026-07-28T01:00:00+00:00",
        }
        if verified:
            item["verification"] = VerificationState.VERIFIED
        feed.append(item)
        choices = [SignalStrength.LOW, SignalStrength.MEDIUM]
        if verified:
            choices += [SignalStrength.HIGH, SignalStrength.CRITICAL]
        plans.append((candidate_id, rng.choice(choices), rng.random() < 0.5))

    steps: list[tuple[str, str | None]] = [
        (proposal("lock_coverage_window",
                  {"coverage_start_utc": WINDOW[0], "coverage_end_utc": WINDOW[1]}), None),
        (proposal("advance_state", {"target_state": "Scanning"}), None),
        (proposal("record_source_outcome", {"outcomes": all_mandatory_outcomes()}), None),
        (proposal("fetch_candidates", {}), None),
        (proposal("advance_state", {"target_state": "Candidate Review"}), None),
    ]
    for candidate_id, signal, _include in plans:
        steps.append((proposal("score_candidate", {"candidate_id": candidate_id}),
                      score_output(signal.value, nz=rng.randint(0, 5), india=rng.randint(0, 5),
                                   member=rng.randint(0, 5))))
    for candidate_id, _signal, include in plans:
        steps.append((proposal("check_verification_gate",
                               {"candidate_id": candidate_id, "included": include}), None))
    included = sum(1 for _c, _s, include in plans if include)
    steps.append((proposal("draft_brief", {"summary": f"{included} item(s) selected."}), None))
    steps.append((proposal("advance_state", {"target_state": "QA In Progress"}), None))

    # Interleave refused proposals at random points (never after the run reaches QA).
    for _ in range(rng.randint(0, 3)):
        position = rng.randint(1, len(steps) - 1)
        steps.insert(position, (rng.choice(_NOISE), None))
    return Script(run_id=run_id, feed=tuple(feed), steps=tuple(steps))


def execute(script: Script, *, key: bytes | None = None) -> AgentOrchestrator:
    """Run a script through the agent's own tool path. Refused proposals stay in the audit."""
    outputs = [score for _text, score in script.steps if score is not None]
    agent = AgentOrchestrator(
        authorised_orchestrator(script.run_id, key=key),
        run_id=script.run_id,
        gateway=scripted_gateway(outputs),
        source_id_lookup=source_lookup(),
        collector_fetch=lambda _window: [dict(item) for item in script.feed],
    )
    for text, _score in script.steps:
        try:
            agent.execute_proposal(parse_tool_proposal(text))
        except Exception:  # noqa: BLE001, S112 - a refusal is part of the run being measured
            continue
    return agent


def _plain(value: object) -> object:
    """Tool arguments are stored as read-only mappings; unwrap them for comparison."""
    return dict(value) if isinstance(value, Mapping) else list(value)  # type: ignore[call-overload]


def normalised(audit: AgentRunAuditLog) -> dict:
    """The audit log with wall-clock timestamps removed, for comparing two executions."""
    return {
        "run_id": audit.run_id,
        "production_enabled": audit.production_enabled,
        "coverage_window": audit.coverage_window,
        "transitions": [(t.from_state.value, t.to_state.value, t.actor,
                         t.human_decision.approver if t.human_decision else None)
                        for t in audit.transitions],
        "tool_records": [(r.sequence, r.tool, json.dumps(r.arguments, sort_keys=True, default=_plain), r.reason,
                          r.state_before.value, r.state_after.value, r.outcome, r.detail)
                         for r in audit.tool_records],
        "source_checks": [c.model_dump(mode="json") for c in audit.source_checks],
        "candidates": [c.model_dump(mode="json") for c in audit.candidates],
        "brief": None if audit.brief_draft is None else (
            audit.brief_draft.summary, audit.brief_draft.included_candidate_ids,
            audit.brief_draft.no_material_new_signal, audit.brief_draft.content_sha256),
    }


# --- Tampering ----------------------------------------------------------------------------

Mutation = Callable[[AgentRunAuditLog], AgentRunAuditLog | None]


def _with(audit: AgentRunAuditLog, **changes: object) -> AgentRunAuditLog:
    return dataclasses.replace(audit, **changes)


def _forge_gate(audit: AgentRunAuditLog, decision: HumanDecision | None) -> AgentRunAuditLog:
    last = audit.transitions[-1]
    forged = TransitionRecord(from_state=last.to_state, to_state=RunState.AWAITING_CEO_DECISION,
                              actor="sip-agent", at=last.at + timedelta(seconds=1),
                              human_decision=decision)
    return _with(audit, transitions=(*audit.transitions, forged))


def _included_high(audit: AgentRunAuditLog) -> AgentRunAuditLog | None:
    for index, candidate in enumerate(audit.candidates):
        if candidate.included and candidate.signal in {SignalStrength.HIGH, SignalStrength.CRITICAL}:
            demoted = candidate.model_copy(update={"verification": VerificationState.UNVERIFIED})
            candidates = list(audit.candidates)
            candidates[index] = demoted
            return _with(audit, candidates=tuple(candidates))
    return None


def _score_out_of_range(audit: AgentRunAuditLog) -> AgentRunAuditLog | None:
    if not audit.candidates:
        return None
    candidates = list(audit.candidates)
    candidates[0] = Candidate.model_construct(**{**candidates[0].__dict__, "nz_relevance": 9})
    return _with(audit, candidates=tuple(candidates))


def _first_accepted_mutating(audit: AgentRunAuditLog) -> int | None:
    for index, record in enumerate(audit.tool_records):
        if record.outcome == "accepted" and record.state_before is not record.state_after:
            return index
    return None


def _record_crosses_gate(audit: AgentRunAuditLog) -> AgentRunAuditLog | None:
    index = _first_accepted_mutating(audit)
    if index is None:
        return None
    records = list(audit.tool_records)
    records[index] = dataclasses.replace(records[index], state_before=RunState.QA_IN_PROGRESS,
                                         state_after=RunState.AWAITING_CEO_DECISION)
    return _with(audit, tool_records=tuple(records))


def _refused_changes_state(audit: AgentRunAuditLog) -> AgentRunAuditLog | None:
    index = _first_accepted_mutating(audit)
    if index is None:
        return None
    records = list(audit.tool_records)
    records[index] = dataclasses.replace(records[index], outcome="refused")
    return _with(audit, tool_records=tuple(records))


def _drop_record(audit: AgentRunAuditLog) -> AgentRunAuditLog | None:
    index = _first_accepted_mutating(audit)
    if index is None:
        return None
    records = [dataclasses.replace(r, sequence=i) for i, r in
               enumerate(r for j, r in enumerate(audit.tool_records) if j != index)]
    return _with(audit, tool_records=tuple(records))


def _swap_transitions(audit: AgentRunAuditLog) -> AgentRunAuditLog | None:
    if len(audit.transitions) < 3:
        return None
    t = list(audit.transitions)
    t[1], t[2] = t[2], t[1]
    return _with(audit, transitions=tuple(t))


def _edit_text(field: str, value: object) -> Mutation:
    def mutate(audit: AgentRunAuditLog) -> AgentRunAuditLog | None:
        if not audit.tool_records:
            return None
        records = list(audit.tool_records)
        records[0] = dataclasses.replace(records[0], **{field: value})
        return _with(audit, tool_records=tuple(records))

    return mutate


def _edit_transition(field: str, value: object) -> Mutation:
    def mutate(audit: AgentRunAuditLog) -> AgentRunAuditLog | None:
        t = list(audit.transitions)
        t[-1] = dataclasses.replace(t[-1], **{field: value})
        return _with(audit, transitions=tuple(t))

    return mutate


def _fake_launch_approver(audit: AgentRunAuditLog) -> AgentRunAuditLog:
    t = list(audit.transitions)
    t[0] = dataclasses.replace(
        t[0], human_decision=HumanDecision(approver="Someone else", decision="Launch authorised")
    )
    return _with(audit, transitions=tuple(t))


# (name, safety_relevant, mutation). Safety-relevant mutations alter a gate, a source check, a
# verification, a score bound or the brief; replay exists to catch these. Metadata mutations
# alter who/when/why text that replay does not bind cryptographically.
MUTATIONS: tuple[tuple[str, bool, Mutation], ...] = (
    ("forge-qa-pass-no-human", True, lambda a: _forge_gate(a, None)),
    ("forge-qa-pass-with-human-decision", True,
     lambda a: _forge_gate(a, HumanDecision(approver="CEO", decision="QA pass"))),
    ("drop-last-transition", True, lambda a: _with(a, transitions=a.transitions[:-1])),
    ("swap-two-transitions", True, _swap_transitions),
    ("tool-record-claims-gate-crossing", True, _record_crosses_gate),
    ("refused-record-changed-state", True, _refused_changes_state),
    ("drop-accepted-tool-record", True, _drop_record),
    ("remove-a-source-check", True, lambda a: _with(a, source_checks=a.source_checks[:-1])),
    ("demote-included-high-to-unverified", True, _included_high),
    ("score-out-of-range", True, _score_out_of_range),
    ("rewrite-brief-summary", True, lambda a: _with(
        a, brief_draft=dataclasses.replace(a.brief_draft, summary="Rewritten summary."))),
    ("change-brief-included-ids", True, lambda a: _with(
        a, brief_draft=dataclasses.replace(a.brief_draft, included_candidate_ids=("ghost",)))),
    ("coverage-window-23h", True, lambda a: _with(
        a, coverage_window=(WINDOW[0], "2026-07-28T18:00:00+00:00"))),
    ("production-enabled-true", True, lambda a: _with(a, production_enabled=True)),
    ("rewrite-tool-reason", False, _edit_text("reason", "Edited after the fact.")),
    ("rewrite-tool-detail", False, _edit_text("detail", "Edited after the fact.")),
    ("rewrite-transition-actor", False, _edit_transition("actor", "someone-else")),
    ("shift-transition-timestamp", False, lambda a: _edit_transition(
        "at", a.transitions[-1].at + timedelta(days=3))(a)),
    ("rename-launch-approver", False, _fake_launch_approver),
)


def _reuse_launch_signature(audit: AgentRunAuditLog) -> AgentRunAuditLog:
    """Forge a QA pass carrying the genuine launch decision, signature and all."""
    launch = audit.transitions[0].human_decision
    return _forge_gate(audit, launch)


def _fabricated_signature(audit: AgentRunAuditLog) -> AgentRunAuditLog:
    return _forge_gate(audit, HumanDecision(approver="CEO", decision="QA pass",
                                            signature="0" * 64))


# Only meaningful once decisions are signed and logs sealed: attacks on the signatures and the
# seal themselves. `strip-seal` is handled in `_rejects` because it removes the seal, not a record.
SIGNED_ONLY: tuple[tuple[str, bool, Mutation], ...] = (
    ("reuse-launch-signature-for-qa-pass", True, _reuse_launch_signature),
    ("forged-decision-fabricated-signature", True, _fabricated_signature),
    ("strip-seal", True, lambda a: a),
)


def _rejects(
    audit_factory: Callable[[], AgentRunAuditLog | None],
    *,
    key: bytes | None = None,
    seal: str | None = None,
) -> bool | None:
    """True if replay rejects the mutated log, None if the mutation does not apply to this run.

    With `key`, the attacker is assumed not to hold it: the mutated log is replayed against the
    seal made for the genuine one, because a new seal cannot be computed without the key.
    """
    try:
        mutated = audit_factory()
    except (CorruptHistory, ValueError, TypeError):
        return True  # the log type itself refused to hold the tampered value
    if mutated is None:
        return None
    try:
        replay_agent_audit(mutated, source_id_lookup=source_lookup(), signing_key=key, seal=seal)
    except (CorruptHistory, ValueError, TypeError):
        return True
    return False


def run_measurement(
    runs: int = DEFAULT_RUNS, seed: int = DEFAULT_SEED, *, signed: bool = False
) -> dict[str, object]:
    """`signed=False` is the baseline; `signed=True` is the W6 change: signed decisions, sealed log."""
    key = MEASUREMENT_KEY if signed else None
    mutations = MUTATIONS + (SIGNED_ONLY if signed else ())
    replay_ok = 0
    reexecution_ok = 0
    final_states: dict[str, int] = {}
    tamper: dict[str, dict[str, object]] = {
        name: {"safety_relevant": relevant, "applied": 0, "detected": 0}
        for name, relevant, _ in mutations
    }
    with redaction_policy():
        for index in range(runs):
            script = generate(seed, index)
            agent = execute(script, key=key)
            audit = agent.audit_log()
            seal = agent.sealed_audit_log(key)[1] if key is not None else None
            final_states[agent.state.value] = final_states.get(agent.state.value, 0) + 1
            replayed = replay_agent_audit(audit, source_id_lookup=source_lookup(),
                                          signing_key=key, seal=seal)
            if replayed.state is agent.state and replayed.history == audit.transitions:
                replay_ok += 1
            if normalised(execute(script, key=key).audit_log()) == normalised(audit):
                reexecution_ok += 1
            for name, _relevant, mutation in mutations:
                if name == "strip-seal":
                    verdict = _rejects(lambda a=audit: a, key=key, seal=None)
                else:
                    verdict = _rejects(lambda m=mutation, a=audit: m(a), key=key, seal=seal)
                if verdict is None:
                    continue
                tamper[name]["applied"] += 1
                tamper[name]["detected"] += int(verdict)

    def rate(relevant: bool) -> tuple[int, int]:
        rows = [row for row in tamper.values() if row["safety_relevant"] is relevant]
        return sum(r["detected"] for r in rows), sum(r["applied"] for r in rows)

    safety_detected, safety_applied = rate(True)
    meta_detected, meta_applied = rate(False)
    return {
        "mode": "signed-and-sealed" if signed else "baseline-unsigned",
        "runs": runs,
        "seed": seed,
        "final_states": final_states,
        "replay_exact": replay_ok,
        "reexecution_identical": reexecution_ok,
        "tamper_safety_detected": safety_detected,
        "tamper_safety_applied": safety_applied,
        "tamper_metadata_detected": meta_detected,
        "tamper_metadata_applied": meta_applied,
        "tamper_by_mutation": tamper,
    }


def _summary(report: dict[str, object]) -> str:
    lines = [
        (f"mode {report['mode']}, runs {report['runs']} (seed {report['seed']}), "
         f"final states {report['final_states']}"),
        f"replayed exactly from the audit log: {report['replay_exact']}/{report['runs']}",
        f"re-execution gave an identical log: {report['reexecution_identical']}/{report['runs']}",
        (f"safety-relevant tampering detected: {report['tamper_safety_detected']}/"
         f"{report['tamper_safety_applied']}"),
        (f"metadata-only tampering detected:  {report['tamper_metadata_detected']}/"
         f"{report['tamper_metadata_applied']}"),
        "",
        f"{'mutation':<38} {'safety':>6} {'applied':>7} {'detected':>8}",
    ]
    for name, row in report["tamper_by_mutation"].items():  # type: ignore[union-attr]
        lines.append(f"{name:<38} {'yes' if row['safety_relevant'] else 'no':>6} "
                     f"{row['applied']:>7} {row['detected']:>8}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--signed", action="store_true",
                        help="measure with signed decisions and a sealed log (the W6 change)")
    parser.add_argument("--write", action="store_true", help="save the results file")
    args = parser.parse_args(argv)
    report = run_measurement(args.runs, args.seed, signed=args.signed)
    print(_summary(report))
    if args.write:
        RESULTS_DIR.mkdir(exist_ok=True)
        name = "replay-fidelity-signed.json" if args.signed else "replay-fidelity.json"
        out = RESULTS_DIR / name
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {out}")
    ok = report["replay_exact"] == report["reexecution_identical"] == report["runs"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
