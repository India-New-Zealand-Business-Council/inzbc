"""HTTP client for the "Pipeline (Roshan) — data in" endpoints in schemas/api-contract.md.

No server exists yet (services/api is still a stub) — this client has nothing to talk to until
Bhanu's API is live. It exists so the pipeline/collector code can be written and tested (locally,
against models.py) ahead of that, and pointed at a real base_url the moment one exists.

Deliberately thin: no retry/backoff policy, no business logic, no assumptions about how the
server behaves beyond what schemas/api-contract.md states. Add those once there's a real server
to observe.
"""

from __future__ import annotations

from typing import Any

import requests
from pydantic import BaseModel

from .models import Candidate, Run, SourceCheck


class SipApiError(RuntimeError):
    """Raised on a non-2xx response. Wraps the server's error body where available."""

    def __init__(self, status_code: int, body: Any):
        super().__init__(f"SIP API error {status_code}: {body}")
        self.status_code = status_code
        self.body = body


class SipPipelineClient:
    """Bearer-token REST client for the pipeline endpoints. One instance per run/session."""

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {token}"})
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._session.request(
            method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs
        )
        if not response.ok:
            raise SipApiError(response.status_code, _safe_json(response))
        return _safe_json(response)

    # ---------- runs ----------

    def create_run(self, run: Run) -> dict:
        """POSTs the run-creation fields only.

        `Run` also carries server-controlled fields (`id`, `state`, `version`,
        `production_enabled`, `coverage_timezone`) that `services/api/runs.py`'s `CreateRunIn`
        deliberately does not accept - `production_enabled` in particular is never client-settable
        at creation (the server always creates `False`, per the SIP non-negotiable). Sending the
        full `Run.model_dump()` 422s against that `extra="forbid"` model the moment a caller
        supplies any `Run` field with a non-None default (e.g. `coverage_timezone`), which is
        every caller - `Run()` sets it by default. Caught by actually running #55's dry run
        against a real server, not by the fake-client tests, which don't validate extra fields.
        """
        payload = {
            "run_number": run.run_number,
            "prompt_version": run.prompt_version,
            "coverage_start_utc": run.coverage_start_utc,
            "coverage_end_utc": run.coverage_end_utc,
            "initiated_by": run.initiated_by,
        }
        return self._request("POST", "/api/runs", json=payload)

    def list_runs(self) -> list[dict]:
        return self._request("GET", "/api/runs")

    def get_run(self, run_id: str) -> dict:
        return self._request("GET", f"/api/runs/{run_id}")

    def start_run(self, run_id: str) -> dict:
        return self._request("POST", f"/api/runs/{run_id}/start")

    def pause_run(self, run_id: str) -> dict:
        return self._request("POST", f"/api/runs/{run_id}/pause")

    def resume_run(self, run_id: str) -> dict:
        return self._request("POST", f"/api/runs/{run_id}/resume")

    def complete_run(self, run_id: str) -> dict:
        return self._request("POST", f"/api/runs/{run_id}/complete")

    # ---------- source library ----------

    def get_source_library(self) -> list[dict]:
        """Returns every `source_library` row as `{"id", "sip185_code", "name"}` (see
        `schemas/api-contract.md`). Feed this straight into
        `apps.sip.collector.source_lookup.build_source_lookups`.
        """
        return self._request("GET", "/api/source-library")

    # ---------- source checks ----------

    def list_source_checks(self, run_id: str) -> list[dict]:
        return self._request("GET", f"/api/runs/{run_id}/source-checks")

    def record_source_check(self, run_id: str, source_check: SourceCheck) -> dict:
        """`run_id` is in the URL, not the body - `RecordSourceCheckIn`
        (`services/api/source_checks.py`) doesn't accept it (`extra="forbid"`), same shape as
        `create_run`'s fix. `source_check.run_id` must still be set for callers building the
        `SourceCheck` model directly (it mirrors the `source_checks` table), so it's dropped here
        rather than removed from the model.
        """
        payload = _model_json(source_check)
        payload.pop("run_id", None)
        return self._request(
            "POST",
            f"/api/runs/{run_id}/source-checks",
            json=payload,
        )

    # ---------- candidates ----------

    def list_candidates(self, run_id: str) -> list[dict]:
        return self._request("GET", "/api/candidates", params={"run": run_id})

    def create_candidate(self, candidate: Candidate, actor_id: str) -> dict:
        """POSTs the capture fields `CaptureCandidateIn` (`services/api/candidates.py`) accepts,
        plus `actor_id` - not a `Candidate`/`candidates`-table field at all, it's audit-only
        (`services/api/candidate_persistence.py`'s `capture()` passes it straight to
        `record_audit`, never to the INSERT), the same caller-supplied-pending-real-session-auth
        shape as `create_run`'s `initiated_by`.

        Whitelisted the same way `create_run` is, not `_model_json(candidate)` verbatim:
        `Candidate.verification` defaults to `Unverified` (not `None`), so it survives
        `exclude_none=True` and 422s against `CaptureCandidateIn`'s `extra="forbid"` - the same
        bug class as `create_run`'s `coverage_timezone`, caught the same way, by actually running
        #55's dry run against a live server rather than trusting the fake-client tests.
        """
        payload = {
            "run_id": candidate.run_id,
            "headline": candidate.headline,
            "source_id": candidate.source_id,
            "url": candidate.url,
            "summary": candidate.summary,
            "published_at": candidate.published_at,
            "in_coverage_window": candidate.in_coverage_window,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        payload["actor_id"] = actor_id
        return self._request("POST", "/api/candidates", json=payload)

    def patch_candidate(self, candidate_id: str, fields: dict) -> dict:
        return self._request("PATCH", f"/api/candidates/{candidate_id}", json=fields)

    def verify_candidate(self, candidate_id: str, payload: dict) -> dict:
        return self._request("POST", f"/api/candidates/{candidate_id}/verify", json=payload)

    def score_candidate(self, candidate_id: str, payload: dict) -> dict:
        return self._request("POST", f"/api/candidates/{candidate_id}/score", json=payload)

    def route_candidate(self, candidate_id: str, payload: dict) -> dict:
        return self._request("POST", f"/api/candidates/{candidate_id}/route", json=payload)

    def merge_candidate(self, candidate_id: str, payload: dict) -> dict:
        return self._request("POST", f"/api/candidates/{candidate_id}/merge", json=payload)


def _safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _model_json(model: BaseModel) -> dict:
    """Pydantic model -> JSON-safe dict, dropping unset (None) fields, enums as plain strings."""
    return model.model_dump(mode="json", exclude_none=True)
