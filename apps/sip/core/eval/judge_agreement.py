"""Judge-versus-human agreement for the advisory brief-quality judge (#64).

The judge scores a draft brief on four criteria and computes `needs_revision` (any score under
3). It only advises: it cannot approve, verify or change a run. The question here is how often
its advice matches a person's.

Two kinds of label are compared, and kept apart:

- **Golden-set labels** (`apps/sip/core/tests/data/quality-golden.json`). Hand-authored synthetic
  cases with expected score bounds. A case with any maximum below 3 is expected to need revision,
  and a case whose minimums are all 3 or more is expected not to. These were written as test
  labels, not recorded QA decisions, so agreement with them measures the judge against the
  rubric author, not against an independent reviewer.
- **Human QA reviewer labels** (optional `human-qa-labels.csv`: `case_id,needs_revision,
  reviewer,date`). An independent reviewer's verdict on the same cases. Until that file exists,
  the judge-versus-reviewer number is reported as not yet measured, never estimated.

The judge needs a live model. Without `--live` no call is made and nothing is invented:

    uv run python -m apps.sip.core.eval.judge_agreement --live --write   # needs model credentials
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from apps.sip.core.quality import CRITERIA, judge_brief
from scripts.eval_quality import GOLDEN, load_golden
from services.api.model_gateway import ModelGateway
from services.api.prompt_boundary import PromptSource

RESULTS_DIR = Path(__file__).resolve().parent / "results"
HUMAN_LABELS = Path(__file__).resolve().parent / "human-qa-labels.csv"


def expected_needs_revision(case: dict) -> bool | None:
    """The golden case's implied verdict, or None if its bounds do not decide one."""
    if any(value < 3 for value in case["maximum"].values()):
        return True
    if case["minimum"] and all(case["minimum"].get(c, 0) >= 3 for c in CRITERIA):
        return False
    return None


def load_human_labels(path: Path = HUMAN_LABELS) -> dict[str, bool]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labels: dict[str, bool] = {}
    for row in rows:
        value = row["needs_revision"].strip().lower()
        if value not in {"true", "false"} or not row.get("reviewer", "").strip():
            raise ValueError(f"invalid human label row for {row.get('case_id')!r}")
        labels[row["case_id"].strip()] = value == "true"
    return labels


def cohen_kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    """Agreement beyond chance for two binary raters; None when it is undefined."""
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    p_a = sum(a for a, _ in pairs) / n
    p_b = sum(b for _, b in pairs) / n
    expected = p_a * p_b + (1 - p_a) * (1 - p_b)
    if expected == 1:
        return None
    return round((observed - expected) / (1 - expected), 4)


def agreement(judged: dict[str, dict[str, int]], corpus: dict, labels: dict[str, bool]) -> dict:
    """Compare judge scores with golden bounds, golden verdicts and any human verdicts."""
    bound_checks = bound_hits = 0
    golden_pairs: list[tuple[bool, bool]] = []
    human_pairs: list[tuple[bool, bool]] = []
    per_case = []
    for case in corpus["cases"]:
        scores = judged[case["id"]]
        judge_verdict = any(scores[c] < 3 for c in CRITERIA)
        within = []
        for criterion, minimum in case["minimum"].items():
            within.append(scores[criterion] >= minimum)
        for criterion, maximum in case["maximum"].items():
            within.append(scores[criterion] <= maximum)
        bound_checks += len(within)
        bound_hits += sum(within)
        golden = expected_needs_revision(case)
        if golden is not None:
            golden_pairs.append((judge_verdict, golden))
        human = labels.get(case["id"])
        if human is not None:
            human_pairs.append((judge_verdict, human))
        per_case.append({"case": case["id"], "scores": scores, "judge_needs_revision": judge_verdict,
                         "golden_needs_revision": golden, "human_needs_revision": human,
                         "bounds_met": f"{sum(within)}/{len(within)}"})

    def rate(pairs: list[tuple[bool, bool]]) -> float | None:
        return round(sum(a == b for a, b in pairs) / len(pairs), 4) if pairs else None

    return {
        "criterion_bounds_met": f"{bound_hits}/{bound_checks}",
        "golden_verdict_agreement": rate(golden_pairs),
        "golden_verdict_cases": len(golden_pairs),
        "golden_verdict_kappa": cohen_kappa(golden_pairs),
        "human_verdict_agreement": rate(human_pairs),
        "human_verdict_cases": len(human_pairs),
        "human_verdict_kappa": cohen_kappa(human_pairs),
        "per_case": per_case,
    }


def judge_golden(gateway: ModelGateway, corpus: dict) -> dict[str, dict[str, int]]:
    judged = {}
    for case in corpus["cases"]:
        verdict = judge_brief(gateway, brief=case["brief"], evidence=case["evidence"],
                              source=PromptSource.PUBLIC_SOURCE)
        judged[case["id"]] = {c: getattr(verdict, c).score for c in CRITERIA}
    return judged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="call the judge model (8 calls)")
    parser.add_argument("--write", action="store_true", help="save results/judge-agreement.json")
    args = parser.parse_args(argv)
    corpus = load_golden(GOLDEN)
    labels = load_human_labels()
    if not args.live:
        report = {"status": "not-run", "reason": "the judge needs a live model; pass --live",
                  "golden_cases": len(corpus["cases"]),
                  "golden_cases_with_a_verdict": sum(
                      expected_needs_revision(c) is not None for c in corpus["cases"]),
                  "human_labelled_cases": len(labels)}
    else:
        try:
            gateway = ModelGateway()
            judged = judge_golden(gateway, corpus)
        except Exception as error:  # noqa: BLE001 - never echo provider payloads
            report = {"status": "failed", "error_type": type(error).__name__}
        else:
            report = {"status": "measured", "model": gateway.model,
                      "rubric_sha256": corpus["rubric_sha256"],
                      **agreement(judged, corpus, labels)}
    rendered = json.dumps(report, indent=2) + "\n"
    print(rendered, end="")
    if args.write:
        RESULTS_DIR.mkdir(exist_ok=True)
        (RESULTS_DIR / "judge-agreement.json").write_text(rendered, encoding="utf-8")
    return 0 if report["status"] in {"measured", "not-run"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
