"""Content-free model usage metadata, optionally persisted to the existing audit log."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass

import psycopg

from services.api.audit import record_audit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelUsage:
    provider: str
    model: str
    duration_seconds: float
    attempts: int
    succeeded: bool
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: str | None = None
    cost_basis: str = "unknown"


def record_usage(usage: ModelUsage) -> None:
    """Never receives prompt/output text, credentials, source URLs or redacted values.

    Local operation without DATABASE_URL logs metadata only. With a datastore configured,
    persistence errors propagate: callers must not silently return an unaudited result.
    """
    metadata = asdict(usage)
    logger.info("model.call", extra={"model_usage": metadata})
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        with psycopg.connect(dsn) as conn:
            record_audit(conn, action="model.call", new_value=json.dumps(metadata))
