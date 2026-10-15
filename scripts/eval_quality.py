"""Validate the synthetic quality corpus, or run its bounded live model regression gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.sip.core.quality import CRITERIA, judge_brief, quality_prompt_fingerprint
from services.api.model_gateway import ModelGateway
from services.api.prompt_boundary import PromptSource

GOLDEN = Path(__file__).resolve().parents[1] / "apps/sip/core/tests/data/quality-golden.json"


def load_golden(path: Path = GOLDEN) -> dict:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    cases = corpus["cases"]
    if corpus["schema_version"] != 1 or not 1 <= len(cases) <= 20:
        raise ValueError("unsupported or unbounded quality corpus")
    if corpus["rubric_sha256"] != quality_prompt_fingerprint():
        raise ValueError("rubric changed: review golden labels and record the new fingerprint")
    ids = [case["id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate quality case ids")
    from apps.sip.core.quality import build_quality_prompt

    for case in cases:
        build_quality_prompt(case["brief"], case["evidence"])
        if not case["minimum"] and not case["maximum"]:
            raise ValueError("a golden case must assert a quality outcome")
        for bounds in (case["minimum"], case["maximum"]):
            if any(key not in CRITERIA or type(value) is not int or not 0 <= value <= 5
                   for key, value in bounds.items()):
                raise ValueError("invalid golden criterion range")
        if any(value > case["maximum"].get(key, 5) for key, value in case["minimum"].items()):
            raise ValueError("contradictory golden ranges")
    return corpus


def evaluate(gateway: ModelGateway, path: Path = GOLDEN) -> dict:
    corpus = load_golden(path)
    failures = []
    results = []
    for case in corpus["cases"]:
        verdict = judge_brief(gateway, brief=case["brief"], evidence=case["evidence"],
                              source=PromptSource.PUBLIC_SOURCE)
        scores = {criterion: getattr(verdict, criterion).score for criterion in CRITERIA}
        for criterion, minimum in case["minimum"].items():
            if scores[criterion] < minimum:
                failures.append({"case": case["id"], "criterion": criterion, "expected_min": minimum})
        for criterion, maximum in case["maximum"].items():
            if scores[criterion] > maximum:
                failures.append({"case": case["id"], "criterion": criterion, "expected_max": maximum})
        results.append({"case": case["id"], "scores": scores,
                        "needs_revision": verdict.needs_revision})
    return {"mode": "live-synthetic-quality", "model": gateway.model,
            "rubric_sha256": corpus["rubric_sha256"], "results": results, "failures": failures}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="make at most 20 gateway calls")
    parser.add_argument("--report", type=Path, help="write scores/metadata, never model prose")
    args = parser.parse_args(argv)
    try:
        if args.live:
            report = evaluate(ModelGateway())
        else:
            corpus = load_golden()
            report = {"mode": "fixture-validation-only", "cases": len(corpus["cases"]),
                      "rubric_sha256": corpus["rubric_sha256"], "failures": []}
    except Exception as error:  # noqa: BLE001 - CLI must fail without echoing provider payloads
        # Provider exceptions can contain request contents. Report the type, not that contents.
        report = {"mode": "failed", "failures": [{"error_type": type(error).__name__}]}
    rendered = json.dumps(report, indent=2) + "\n"
    print(rendered, end="")
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    return int(bool(report["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
