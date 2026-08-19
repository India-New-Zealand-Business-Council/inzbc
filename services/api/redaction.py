"""Redaction ahead of every external model call (#37).

`docs/sip/README.md` makes this a non-negotiable: member, Board and confidential data must be
stripped before anything reaches a provider. `PROJECT-RULES.md` also says not to fill an unresolved
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


# A replacement is a literal token, never a template. `re.sub` expands `\1` and `\g<0>`, so a rule
# with `"replacement": "\\1"` would send the matched secret straight through while the audit trail
# recorded a successful redaction. False assurance is worse than no control, so backreference syntax
# is refused at load and every replacement is escaped before it reaches `re`.
_BACKREF = re.compile(r"\\[0-9gG]|\\g<")


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

        {"rules": [{"name": "member-email", "pattern": "...", "replacement": "[redacted]",
                    "example": "contact sunil@example.test about the brief"}]}

    Every rule carries an `example`: a sample of what it is meant to catch. The rule must actually
    redact something in it, or the policy does not load. See the check below for why.
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
        def _no_duplicates(pairs: list[tuple[str, object]]) -> dict:
            seen: dict[str, object] = {}
            for key, value in pairs:
                if key in seen:
                    raise RedactionPolicyError(
                        f"duplicate key {key!r} in the redaction policy. Last-key-wins would let a "
                        "reviewed rule be silently replaced by one nobody approved."
                    )
                seen[key] = value
            return seen

        document = json.loads(policy_file.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)
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
        example = entry.get("example")
        if not name or not pattern or not replacement or not example:
            raise RedactionPolicyError(
                f"rule {index} needs a name, a pattern, a replacement and an example; got {entry!r}"
            )
        if _BACKREF.search(replacement):
            raise RedactionPolicyError(
                f"rule {name!r} has a replacement containing backreference syntax. Replacements are "
                "literal text: a backreference would re-emit the matched value while the audit "
                "trail recorded a redaction."
            )
        try:
            compiled = re.compile(pattern)
        except re.error as error:
            raise RedactionPolicyError(f"rule {name!r} has an invalid pattern: {error}") from error
        if compiled.match(""):
            raise RedactionPolicyError(
                f"rule {name!r} matches the empty string, which would rewrite every position in the "
                "payload rather than redact anything."
            )
        # Every rule must prove, at load, that it removes something from its own example.
        #
        # Matching the empty string at position 0 was too narrow a check. A pure assertion such as
        # `(?=.*secret)` passes it, loads cleanly, and then redacts nothing: every match it produces
        # is zero-length, and `redact` skips those. The audit trail stays honest (the count is 0),
        # but the author believed they had shipped a control and had not. A typo in a pattern fails
        # the same silent way.
        #
        # Undecidable in general, so it is not inferred: the rule carries a sample of what it is
        # meant to catch, and a rule that cannot redact its own example does not load.
        if not any(m.end() > m.start() for m in compiled.finditer(example)):
            raise RedactionPolicyError(
                f"rule {name!r} does not redact anything in its own example {example!r}. A rule "
                "whose every match is zero-length loads cleanly and then removes nothing, so it "
                "must demonstrate on a sample that it works."
            )
        # Matching is not redacting. `"pattern": "sunil", "replacement": "sunil"` matches, so the
        # check above passes, and then substitution puts the value straight back and counts a
        # redaction. That is the backreference bug again by a different route: the payload leaves
        # unchanged while the audit trail says it was masked.
        if compiled.search(replacement):
            raise RedactionPolicyError(
                f"rule {name!r} has a replacement that its own pattern matches. The value would be "
                "re-emitted while the audit trail recorded a redaction, and the token would match "
                "on any later pass."
            )
        if redact(example, [RedactionRule(name=name, pattern=compiled,
                                          replacement=replacement)]).text == example:
            raise RedactionPolicyError(
                f"rule {name!r} leaves its own example {example!r} unchanged. Matching is not "
                "redacting: the rule must be shown to remove something, not merely to fire."
            )
        rules.append(RedactionRule(name=name, pattern=compiled, replacement=replacement))
    return rules


MAX_PAYLOAD_CHARS = 200_000


def redact(text: str, rules: list[RedactionRule] | None = None) -> RedactionResult:
    """Redacts `text` against every rule.

    Every rule matches the **original** text, not the previous rule's output. Chaining them was
    wrong in both directions: a rule whose input an earlier rule had already rewritten would stop
    matching and let the value through (`"Member ID:"` masked first, so `"Member ID: 123456"` no
    longer matched and the number survived), and a later rule matching an earlier rule's token
    could put the original value back.

    Matches are collected as spans and overlapping ones are merged, so the union is redacted. An
    overlap can therefore only ever remove more text, never less, and no rule can shrink another's
    coverage. Every contributing rule is counted.
    """
    active = load_policy() if rules is None else rules
    if not active:
        raise RedactionNotConfiguredError("no redaction rules loaded; refusing to send.")

    if len(text) > MAX_PAYLOAD_CHARS:
        # Bounded input is the only cheap defence available: Python's `re` has no match timeout,
        # so a pathological pattern is only survivable if the payload cannot grow without limit.
        # See docs/redaction-policy.md on why policy authorship is a trusted operation.
        raise RedactionPolicyError(
            f"payload is {len(text)} characters, over the {MAX_PAYLOAD_CHARS} limit; refusing to "
            "run redaction rules over an unbounded input."
        )

    spans: list[tuple[int, int, str, str]] = []
    for rule in active:
        for match in rule.pattern.finditer(text):
            if match.end() > match.start():
                spans.append((match.start(), match.end(), rule.name, rule.replacement))

    if not spans:
        return RedactionResult(text=text, counts={})

    order = {rule.name: index for index, rule in enumerate(active)}
    spans.sort(key=lambda s: (s[0], -s[1], order.get(s[2], 0)))

    # Overlapping matches are merged and the union is redacted. Picking one and discarding the rest
    # is what let a value survive: masking `Member ID:` first left `Member ID: 123456` no longer
    # matching the rule that would have removed the number, so the identifier stayed in the payload.
    # Redacting the union means an overlap can only ever remove more, never less.
    merged: list[tuple[int, int, str, list[str]]] = []
    for start, end, name, replacement in spans:
        if merged and start <= merged[-1][1]:
            prev_start, prev_end, prev_token, names = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end), prev_token, names + [name])
        else:
            merged.append((start, end, replacement, [name]))

    counts: dict[str, int] = {}
    out: list[str] = []
    cursor = 0
    for start, end, token, names in merged:
        out.append(text[cursor:start])
        out.append(token)
        # Every rule that contributed to the region is credited, so the audit trail shows which
        # categories were present rather than only the one whose token was used.
        for name in names:
            counts[name] = counts.get(name, 0) + 1
        cursor = end
    out.append(text[cursor:])
    return RedactionResult(text="".join(out), counts=counts)
