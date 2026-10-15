"""Batch-replay the synthetic SIP-050 contract corpus without a provider or database."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apps.sip.core.scoring import (
    ScoringParseError,
    build_scoring_prompt,
    score_candidate,
)
from services.api.model_gateway import GatewayResult
from services.api.prompt_boundary import PromptSource

FIXTURES = (Path(__file__).resolve().parents[1] / "apps" / "sip" / "core" / "tests"
            / "data" / "scoring-regression.json")


class ReplayGateway:
    def __init__(self, output: str) -> None:
        self.output = output

    def complete(self, prompt: str, *, source: PromptSource) -> GatewayResult:
        if source is not PromptSource.PUBLIC_SOURCE:
            raise ValueError("scoring changed its declared source")
        return GatewayResult(self.output, "offline-replay", 0)


def evaluate(path: Path = FIXTURES) -> dict:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    if corpus["schema_version"] != 1 or not corpus["cases"]:
        raise ValueError("unsupported or empty scoring corpus")
    ids = [case["id"] for case in corpus["cases"]]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate scoring case ids")
    failures = []
    prompt = build_scoring_prompt(**corpus["candidate"])
    if hashlib.sha256(prompt.encode()).hexdigest() != corpus["prompt_sha256"]:
        failures.append({"id": "prompt-baseline", "error": "rendered prompt changed"})
    accepted = refused = 0
    for case in corpus["cases"]:
        candidate = corpus["candidate"] | case.get("candidate_overrides", {})
        try:
            result = score_candidate(ReplayGateway(case["output"]), **candidate)
        except ScoringParseError:
            refused += 1
            if case["expected"] != "refused":
                failures.append({"id": case["id"], "error": "expected acceptance"})
        else:
            accepted += 1
            if (case["expected"] != "accepted"
                    or result.model_dump(mode="json") != case["recommendation"]):
                failures.append({"id": case["id"], "error": "recommendation drift"})
    return {"mode": "synthetic-offline-replay", "cases": len(ids), "accepted": accepted,
            "refused": refused, "failures": failures}


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    return int(bool(result["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
