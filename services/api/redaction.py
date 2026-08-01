"""Redaction ahead of every external model call (#37).

`docs/sip/README.md` makes this a non-negotiable: member, Board and confidential data must be
stripped before anything reaches a provider. `CLAUDE.md` also says not to fill an unresolved
business rule with an assumption, and *what counts as confidential* is exactly that kind of rule.

So this module deliberately ships the mechanism without the policy. The policy is data: a list of
named rules loaded from `REDACTION_POLICY_PATH`. With no policy configured, `redact()` raises and
the gateway refuses the call. Absence blocks the send rather than silently permitting it, which is
the same shape as `decision_role_permissions` in ADR-0005: no row means nobody may act.

That ordering matters. Building the mechanism first means the eventual policy decision is a config
change rather than a code change, and #53 and #65 can build against a gateway that already enforces
redaction instead of waiting for a meeting.

The rules themselves are regexes with a replacement token. That is deliberately unclever: a rule
someone from INZBC has to be able to read and approve is worth more here than a smarter matcher
nobody can audit.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

POLICY_PATH_ENV = "REDACTION_POLICY_PATH"


class RedactionNotConfiguredError(RuntimeError):
    """Raised when a model call is attempted with no redaction policy loaded.

    Fail closed. An unconfigured policy is not an empty policy: it means nobody has decided what
    counts as confidential, and sending the payload anyway would make that decision by default.
    """


class RedactionPolicyError(ValueError):
    """Raised when a policy file exists but cannot be trusted to do its job."""


@dataclass(frozen=True)
class RedactionRule:
    """One named rule. `name` appears in the audit trail, never the matched text itself."""

    name: str
    pattern: re.Pattern[str]
    replacement: str


@dataclass(frozen=True)
class RedactionResult:
    """Redacted text plus which rules fired, for the audit log.

    `counts` records rule names and how many times each matched. It never carries the matched
    text: an audit trail that quotes the thing it redacted has not redacted it.
    """

    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def redacted(self) -> bool:
        return bool(self.counts)


def load_policy(path: str | Path | None = None) -> list[RedactionRule]:
    """Loads the policy from `path`, or from `REDACTION_POLICY_PATH`.

    Raises `RedactionNotConfiguredError` when neither is set or the file is missing, so a
    deployment that forgot to mount the policy fails loudly at the first model call rather than
    quietly sending everything.

    Expected shape:

        {"rules": [{"name": "member-email", "pattern": "...", "replacement": "[redacted]"}]}
    """
    raw_path = str(path) if path is not None else os.getenv(POLICY_PATH_ENV, "")
    if not raw_path:
        raise RedactionNotConfiguredError(
            f"{POLICY_PATH_ENV} is not set. Every external model call must be redacted first "
            "(docs/sip/README.md), and what counts as confidential is a business rule INZBC owns "
            "(issue #37). Nothing is sent until a policy is configured."
        )

    policy_file = Path(raw_path)
    if not policy_file.is_file():
        raise RedactionNotConfiguredError(
            f"redaction policy not found at {policy_file}. Refusing to send an unredacted payload."
        )

    try:
        document = json.loads(policy_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RedactionPolicyError(f"redaction policy at {policy_file} is not valid JSON") from error

    entries = document.get("rules")
    if not isinstance(entries, list) or not entries:
        raise RedactionPolicyError(
            f"redaction policy at {policy_file} declares no rules. An empty policy is treated as a "
            "mistake, not as a decision that nothing is confidential."
        )

    rules: list[RedactionRule] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise RedactionPolicyError(f"rule {index} is not an object")
        name = entry.get("name")
        pattern = entry.get("pattern")
        replacement = entry.get("replacement")
        if not name or not pattern or not replacement:
            raise RedactionPolicyError(
                f"rule {index} needs a name, a pattern and a replacement; got {entry!r}"
            )
        try:
            compiled = re.compile(pattern)
        except re.error as error:
            raise RedactionPolicyError(f"rule {name!r} has an invalid pattern: {error}") from error
        rules.append(RedactionRule(name=name, pattern=compiled, replacement=replacement))
    return rules


def redact(text: str, rules: list[RedactionRule] | None = None) -> RedactionResult:
    """Applies every rule to `text`, in order.

    Rules are applied in the order the policy lists them, so a broader rule placed later cannot
    undo a narrower one placed earlier. Every rule runs; there is no short-circuit, because two
    categories can appear in the same payload.
    """
    active = load_policy() if rules is None else rules
    if not active:
        raise RedactionNotConfiguredError("no redaction rules loaded; refusing to send.")

    counts: dict[str, int] = {}
    result = text
    for rule in active:
        result, hits = rule.pattern.subn(rule.replacement, result)
        if hits:
            counts[rule.name] = counts.get(rule.name, 0) + hits
    return RedactionResult(text=result, counts=counts)
