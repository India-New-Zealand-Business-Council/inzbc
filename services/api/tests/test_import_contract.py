"""No write path is enabled by the batch contract tests."""
from datetime import datetime, timezone
import uuid

import pytest
from pydantic import ValidationError

from services.api.import_contract import ImportBatchIn, require_consistent_batch

RUN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SOURCE = uuid.UUID("22222222-2222-2222-2222-222222222222")
DIGEST = "a" * 64


def payload():
    return {
        "run_id": str(RUN_ID),
        "articles_sha256": DIGEST,
        "expected_run_version": 4,
        "capture_source_count": 112,
        "candidates": [{
            "headline": "Synthetic trade announcement",
            "source_id": str(SOURCE),
            "url": "https://example.org/one",
            "published_at": "2026-10-27T02:00:00+00:00",
            "in_coverage_window": True,
        }],
    }


def test_digest_claim_is_stable_and_run_bound():
    a = ImportBatchIn.model_validate(payload())
    assert len(a.claim_key) == 64
    assert a.claim_key == ImportBatchIn.model_validate(payload()).claim_key
    b = payload()
    b["run_id"] = str(uuid.uuid4())
    assert ImportBatchIn.model_validate(b).claim_key != a.claim_key


@pytest.mark.parametrize("mutate", [
    lambda x: x.update(articles_sha256="A" * 64),
    lambda x: x.update(expected_run_version=-1),
    lambda x: x.update(candidates=[]),
    lambda x: x["candidates"][0].update(in_coverage_window=False),
    lambda x: x["candidates"][0].update(published_at="2026-10-27T02:00:00"),
    lambda x: x["candidates"][0].update(url="http://localhost/secret"),
    lambda x: x["candidates"][0].update(headline=" "),
    lambda x: x["candidates"].append(dict(x["candidates"][0])),
    lambda x: x.update(unknown_role_override=True),
])
def test_malformed_and_unsafe_envelopes_refused(mutate):
    data = payload()
    mutate(data)
    with pytest.raises(ValidationError):
        ImportBatchIn.model_validate(data)


@pytest.mark.parametrize(("update", "message"), [
    ({"run_version": 5}, "version changed"),
    ({"state": "Draft"}, "Scanning"),
    ({"existing_count": 1}, "existing candidates"),
    ({"capture_digest": "b" * 64}, "digest mismatch"),
    ({"run_id": uuid.uuid4()}, "run mismatch"),
])
def test_snapshot_guard_refuses_unreconciled_import(update, message):
    batch = ImportBatchIn.model_validate(payload())
    args = dict(run_id=RUN_ID, run_version=4, state="Scanning",
                existing_count=0, capture_digest=DIGEST)
    args.update(update)
    with pytest.raises(ValueError, match=message):
        require_consistent_batch(batch, **args)


def test_matching_snapshot_only_validates_and_does_not_write():
    batch = ImportBatchIn.model_validate(payload())
    assert require_consistent_batch(batch, run_id=RUN_ID, run_version=4,
        state="Scanning", existing_count=0, capture_digest=DIGEST) is None
