"""Refuse prohibited data at the model boundary, instead of masking it on the way out (#223).

ADR-0006 makes data minimisation and boundary refusal the **primary** control, with regex
redaction as defence in depth. This module is the primary control.

**Why redaction cannot be it.** The policy matches formatted identifiers: emails, phone numbers,
tax and company numbers, cards. It cannot catch a person's name, job title or employer carried in
ordinary prose, and no set of regexes will. This passes through untouched:

    Delegation lead: Priya Sharma, Chief Executive, Koru Exports Ltd

Reviewing the output does not help either. Review happens after the payload has already reached the
provider, so publication review cannot undo a disclosure. The control for prose is not to send it.

**What this module can and cannot enforce, stated plainly.** The gateway receives a *string*. By
then the structure is gone, and no inspection of that string can recover where it came from. So
there are two halves, and they are enforceable to different degrees:

- `minimise()` is real enforcement. A caller names the fields it needs, everything else is dropped
  before assembly, and a nested container that survives the allowlist is refused rather than passed
  through. So a field nobody named cannot reach the text, at any depth.
- `PromptSource` is a **declaration**, not a verification. A caller states where its text came
  from, and prohibited origins are refused. A caller that declares the wrong thing is not caught.

The second is worth having anyway, for a reason worth being explicit about: it makes the question
unavoidable. `complete()` cannot be called without naming a source, so a new call site has to
confront "where did this text come from" at the moment it is written, rather than never. That is a
weaker guarantee than verification and a much stronger one than nothing.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any


class ProhibitedInputError(RuntimeError):
    """Refused at the boundary. The payload never reached a provider.

    Its own type rather than a generic error so a caller can report the real reason. Telling an
    operator "the model call failed" when the answer is "this data may not be sent" sends them to
    the wrong fix, and the wrong fix here is usually to retry.
    """


class PromptSource(str, Enum):
    """Where a prompt's text came from. Every `complete()` call names one.

    Deliberately a closed set. A free-text label would let a caller invent a category that happens
    to fall outside the refusal list, which is the same fail-open shape as a denylist.
    """

    # Permitted.
    PUBLIC_SOURCE = "public_source"
    """Published material: news articles, government statements, public statistics, tariff text."""

    STAFF_AUTHORED = "staff_authored"
    """Written by a staff member for this purpose, knowing it goes to a model."""

    MINIMISED_RECORD = "minimised_record"
    """Built through `minimise()`, so only allowlisted fields are present."""

    # Refused. Present in the enum rather than absent from it, so the refusal is a stated decision
    # a reader can find, and so a caller reaching for one of these gets a refusal naming the rule
    # rather than a NameError naming nothing.
    MEMBER_RECORD = "member_record"
    """A member or prospect record in raw form. ADR-0006 §1."""

    CRM_NOTE = "crm_note"
    """Free-text notes from member or CRM records. ADR-0006 §1, last bullet."""

    BOARD_MATERIAL = "board_material"
    """Non-public Board papers, minutes, deliberations, votes or attributed comments."""

    PRIVATE_MESSAGE = "private_message"
    """Private email or message bodies, and non-public commercial correspondence."""


# An allowlist, not a denylist. A new enum member is refused until someone adds it here
# deliberately, so the failure mode of forgetting is refusal rather than disclosure. A denylist
# would have the opposite default, and the thing being defaulted is a privacy breach.
PERMITTED_SOURCES = frozenset(
    {
        PromptSource.PUBLIC_SOURCE,
        PromptSource.STAFF_AUTHORED,
        PromptSource.MINIMISED_RECORD,
    }
)


def check_source(source: PromptSource) -> None:
    """Refuses a prohibited origin. Raises `ProhibitedInputError`, or returns.

    Called by the gateway before anything else, so a refusal costs no provider call, no API key and
    no redaction pass.

    **The type is checked, not assumed.** `PromptSource` subclasses `str` so its members are usable
    as plain values, and that has a sharp edge: `"public_source" in PERMITTED_SOURCES` is `True` by
    string equality, so a bare string would satisfy the membership test and skip the closed set
    entirely. A prohibited bare string was worse still, failing on `source.value` with an
    `AttributeError` that no caller catching `ProhibitedInputError` would see. Both are the same
    root cause: the set was trusted to enforce a type it does not enforce.
    """
    if not isinstance(source, PromptSource):
        raise ProhibitedInputError(
            f"source must be a PromptSource, not {type(source).__name__}. The set of origins is "
            "deliberately closed: a bare string would let a caller name a category nobody has "
            "classified, and one that happens to spell a permitted value would pass unexamined."
        )
    if source not in PERMITTED_SOURCES:
        raise ProhibitedInputError(
            f"{source.value} may not be sent to an external model (ADR-0006 §1). Configuring a "
            "redaction policy does not grant permission to send it: the policy matches formatted "
            "identifiers and cannot catch a name, job title or employer in prose. Build the prompt "
            "from an explicit field allowlist with minimise() and send it as MINIMISED_RECORD."
        )


def minimise(
    record: Mapping[str, Any],
    allowed: Iterable[str],
) -> dict[str, Any]:
    """Keeps only `allowed` fields. Everything else is dropped before the text is assembled.

    ADR-0006 §2: do not assemble a full record and then depend on a regex to remove the sensitive
    parts afterwards. A field nobody asked for cannot reach the prompt, whatever it contains and
    whatever shape it is in, which is the property regex redaction cannot offer.

    **An empty allowlist refuses**, rather than passing everything or returning nothing quietly.
    The likeliest way an allowlist ends up empty is a caller forgetting to name its fields, and
    the fail-open reading of that mistake sends the whole record.

    **A field named but absent is not an error.** The allowlist states what *may* be sent, not what
    must be present; a record legitimately missing an optional field should not fail the call.

    **A nested container is refused, not passed through.** This was the first version's real hole:
    the filter is one level deep, so allowlisting `sector` on
    `{"sector": {"name": "dairy", "contact": "Priya Sharma, Chief Executive"}}` kept the whole
    subtree, and the claim that a field nobody named cannot reach the prompt was false. Naming a
    key says nothing about what is underneath it.

    Refusing rather than recursing is deliberate. Filtering a subtree needs a nested allowlist, and
    inventing one here would be guessing at a shape the caller knows and this function does not.
    Flattening silently would be worse: it would keep the data and lose the audit of what was kept.
    The caller flattens and names the leaf fields it wants, which is what ADR-0006 §2 asks for.

    Returns a new dict. The input is never mutated, so a caller cannot minimise a record and then
    accidentally read the trimmed original from the same variable.
    """
    permitted = frozenset(allowed)
    if not permitted:
        raise ProhibitedInputError(
            "minimise() needs an explicit field allowlist. An empty one is almost always a caller "
            "that forgot to name its fields, and treating it as 'send everything' turns that slip "
            "into a disclosure."
        )

    kept = {key: value for key, value in record.items() if key in permitted}
    nested = sorted(
        key for key, value in kept.items() if isinstance(value, (Mapping, list, tuple, set))
    )
    if nested:
        raise ProhibitedInputError(
            f"cannot minimise nested field(s): {', '.join(nested)}. Allowlisting a key says "
            "nothing about what is underneath it, so keeping the subtree would send fields nobody "
            "named. Flatten the record and name the leaf fields you actually need."
        )
    return kept
