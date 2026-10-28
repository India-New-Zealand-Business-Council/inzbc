"""No write path is enabled by the batch contract tests."""
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from services.api.import_contract import ImportBatchIn, require_consistent_batch

RUN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SOURCE = uuid.UUID("22222222-2222-2222-2222-222222222222")
DIGEST = "a" * 64

WINDOW_START = datetime(2026, 10, 27, 0, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 10, 28, 0, 0, tzinfo=UTC)
CAPTURED = {"https://example.org/one": (
    SOURCE, datetime(2026, 10, 27, 2, 0, tzinfo=UTC),
)}


def snapshot_args():
    return {
        "run_id": RUN_ID, "run_version": 4, "state": "Scanning",
        "existing_count": 0, "capture_digest": DIGEST,
        "locked_window_start": WINDOW_START,
        "locked_window_end": WINDOW_END,
        "captured_articles": CAPTURED,
    }



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
    lambda x: x["candidates"].append({**x["candidates"][0]}),
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
    args = snapshot_args()
    args.update(update)
    with pytest.raises(ValueError, match=message):
        require_consistent_batch(batch, **args)


def test_matching_snapshot_only_validates_and_does_not_write():
    batch = ImportBatchIn.model_validate(payload())
    assert require_consistent_batch(batch, **snapshot_args()) is None


@pytest.mark.parametrize(("change", "message"), [
    ({"locked_window_start": datetime(2026, 10, 29, tzinfo=UTC)},
     "invalid"),
    ({"locked_window_end": datetime(2026, 10, 27, 1, tzinfo=UTC)},
     "outside locked"),
    ({"locked_window_start": datetime(2026, 10, 27, 0, 0)},
     "timezone-aware"),
    ({"captured_articles": {}}, "evidence missing"),
    ({"captured_articles": {"https://example.org/one": (
        uuid.uuid4(), datetime(2026, 10, 27, 2, tzinfo=UTC))}},
     "does not match"),
])
def test_server_held_window_and_capture_are_required(change, message):
    batch = ImportBatchIn.model_validate(payload())
    args = snapshot_args()
    args.update(change)
    with pytest.raises(ValueError, match=message):
        require_consistent_batch(batch, **args)


def test_caller_true_flag_cannot_override_out_of_window_publication():
    data = payload()
    data["candidates"][0]["published_at"] = "2026-10-29T02:00:00+00:00"
    batch = ImportBatchIn.model_validate(data)
    with pytest.raises(ValueError, match="outside locked run window"):
        require_consistent_batch(batch, **snapshot_args())


def test_server_capture_timestamp_mismatch_fails_closed():
    data = payload()
    data["candidates"][0]["published_at"] = "2026-10-27T03:00:00+00:00"
    batch = ImportBatchIn.model_validate(data)
    with pytest.raises(ValueError, match="does not match"):
        require_consistent_batch(batch, **snapshot_args())
