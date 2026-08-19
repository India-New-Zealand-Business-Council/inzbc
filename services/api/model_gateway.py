"""Model gateway: the single server-side path for every model call on the platform.

SIP's spec (docs/sip/README.md non-negotiables) requires all model calls server-side with keys
never reaching a browser; this module is where that happens. SIP scoring, the Comms Assistant
and the FTA layer call through here rather than constructing their own clients, so provider,
model, timeout and retry policy are decided once.

Provider today is OpenAI with `gpt-4.1-mini` - the same account and model the
daily-india-nz-news-agent has been running the daily brief on (see that repo's agent.py), so
the platform builds on keys that already exist rather than waiting on new access. The provider
is configuration, not architecture: swapping models/providers means changing env values, not
call sites.

Two controls sit here, in this order.

**Boundary refusal (#223).** Every call names a `PromptSource`, and a prohibited origin is refused
before a policy is read or a key is looked up. Per ADR-0006 this is the *primary* control: regex
redaction cannot catch a name, job title or employer in ordinary prose, so the answer for that data
is not to send it. See `prompt_boundary.py` for what this does and does not enforce.

**Redaction (#37).** Every prompt is then redacted before it reaches a provider. Both live in the
gateway rather than in each caller for the same reason the client does: a control that every caller
has to remember is a control that one caller will forget. With no policy configured the call is
refused, so a deployment that has not decided what counts as confidential sends nothing at all.

Configuration (environment):
- OPENAI_API_KEY          - required for live calls; absent -> GatewayNotConfiguredError.
- SIP_MODEL_NAME          - optional, defaults to gpt-4.1-mini.
- REDACTION_POLICY_PATH   - required; absent -> RedactionNotConfiguredError. See redaction.py.

No key, endpoint or model name is ever hardcoded beyond that default.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from services.api.prompt_boundary import PromptSource, check_source
from services.api.redaction import redact

DEFAULT_MODEL = "gpt-4.1-mini"
_RETRYABLE_ATTEMPTS = 2  # one retry on a transient failure, then surface the error
_RETRY_DELAY_SECONDS = 2.0


class GatewayNotConfiguredError(RuntimeError):
    """No API key available. Raised at call time so a misconfigured deployment fails loudly
    instead of silently producing nothing - never substitute a canned response.
    """


class GatewayCallError(RuntimeError):
    """The provider call failed after retries. Callers treat this as "no recommendation", not
    as an empty answer.
    """


@dataclass(frozen=True)
class GatewayResult:
    """A completed call: the text plus enough metadata for the audit trail."""

    text: str
    model: str
    duration_seconds: float
    # Which redaction rules fired, by name and count. Never the matched text: an audit trail that
    # quotes what it redacted has not redacted it. Empty means the policy ran and matched nothing,
    # which is different from redaction not having run, because an unredacted call cannot happen.
    redaction_counts: dict[str, int] = field(default_factory=dict)


class ModelGateway:
    """Thin, injectable wrapper over the provider client.

    `client` is anything exposing the OpenAI Responses API shape used by the news agent
    (`client.responses.create(model=..., input=...)` returning an object with `output_text`).
    Tests inject a fake; production omits it and the gateway builds a real client from the
    environment on first use.
    """

    def __init__(self, client: object | None = None, model: str | None = None) -> None:
        self._client = client
        self.model = model or os.getenv("SIP_MODEL_NAME", DEFAULT_MODEL)

    def _ensure_client(self) -> object:
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise GatewayNotConfiguredError(
                    "OPENAI_API_KEY is not set - the gateway will not fabricate a response. "
                    "Copy the key the daily-india-nz-news-agent already uses into this "
                    "repo's secrets (see docs/sip/README.md)."
                )
            from openai import OpenAI  # imported lazily so tests never need the package

            self._client = OpenAI(api_key=api_key)
        return self._client

    def complete(self, prompt: str, *, source: PromptSource) -> GatewayResult:
        """One prompt in, text out, with a single retry on a transient provider failure.

        `source` names where the text came from, and a prohibited origin is refused before
        anything else happens (#223, ADR-0006 §1). It is keyword-only and has **no default**: a
        default would be the value every caller ends up with, including the one that never thought
        about it, and the whole point is that a new call site cannot be written without answering
        the question.

        This is a declaration rather than a verification, and the docstring says so rather than
        implying more. By the time text reaches here the structure is gone, so nothing about the
        string reveals its origin and a caller that declares the wrong source is not caught. What
        it does buy is that the question is unavoidable and the answer is reviewable in the diff.
        The enforceable half is `minimise()`, applied before assembly.

        The prompt is then redacted, against the policy at `REDACTION_POLICY_PATH`. Refusal,
        redaction and `_ensure_client` run in that order, so a prohibited payload is refused
        without consulting a policy or a key, and a missing policy is reported even on a machine
        with no API key. Nothing unredacted can leave the process while either is being argued
        about.

        There is deliberately no way for a caller to supply its own rules. An earlier version took
        an injectable rule set so tests need not write a policy file; that made "redaction is
        configured" mean only "a non-empty list was passed", and a list of rules matching nothing
        would have sailed through with an empty audit trail. Tests now point
        `REDACTION_POLICY_PATH` at a real file, the same way production does.
        """
        check_source(source)
        redaction = redact(prompt)
        client = self._ensure_client()
        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(_RETRYABLE_ATTEMPTS):
            try:
                response = client.responses.create(model=self.model, input=redaction.text)
                return GatewayResult(
                    text=response.output_text,
                    model=self.model,
                    duration_seconds=time.monotonic() - started,
                    redaction_counts=dict(redaction.counts),
                )
            except GatewayNotConfiguredError:
                raise
            # noqa rather than a narrower except: the whole point is that provider and network
            # error types differ by SDK version, so naming them would silently stop retrying
            # when a dependency bump renames one.
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt + 1 < _RETRYABLE_ATTEMPTS:
                    time.sleep(_RETRY_DELAY_SECONDS)
        raise GatewayCallError(f"model call failed after {_RETRYABLE_ATTEMPTS} attempts") from last_error
