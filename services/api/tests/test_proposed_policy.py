"""The proposed policy file must stay loadable and keep doing what it claims.

`config/redaction-policy.proposed.json` is a starting point for INZBC's decision, not the approved
policy, and nothing loads it by default. It is still committed, so it can still rot: a rule edited
in a hurry can stop matching and nothing would say so.

Two failure directions matter and they pull against each other. Under-redaction sends member data
to a provider. Over-redaction quietly destroys the trade content the digest exists to discuss, and
a brief with its tariff line masked is useless in a way nobody notices until a member reads it. The
samples below hold both ends still.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.api.redaction import load_policy, redact

POLICY = Path(__file__).resolve().parents[3] / "config" / "redaction-policy.proposed.json"


@pytest.fixture(scope="module")
def rules():
    return load_policy(POLICY)


def test_the_proposed_policy_loads(rules):
    """Also asserts every rule redacts its own example, since load_policy enforces that."""
    assert len(rules) >= 10


# Real INZBC subject matter. Numbers here are figures the corpus already carries, and a rule that
# eats one of them has broken the product to protect data that was never personal.
@pytest.mark.parametrize(
    "text",
    [
        "Wool tariffs fall from 5% to zero over 7 years under HS code 5101.11.00.",
        "Two-way trade reached NZ$3.95 billion in the year ended December 2025.",
        "The 2023 Census recorded 292,092 people in the Indian ethnic group.",
        "FTA signed 27 April 2026; negotiations concluded 22 December 2025.",
        "Annex 2A schedule, tariff line 0402.21.99, staged over 10 years.",
        "INZBC was founded in 1988 and represents its member businesses.",
    ],
)
def test_trade_content_survives_untouched(rules, text):
    result = redact(text, rules)
    assert result.text == text, f"over-redacted: {result.counts}"


@pytest.mark.parametrize(
    ("text", "must_not_survive"),
    [
        ("Contact sunil@example.test about renewal.", "sunil@example.test"),
        ("Call the office on 021 555 0199 tomorrow.", "021 555 0199"),
        ("The Mumbai contact is +91 98765 43210.", "98765 43210"),
        ("Member ID: 123456 renewed in June.", "123456"),
        ("Paid by card 4111 1111 1111 1111 last month.", "4111 1111 1111 1111"),
        ("Their PAN is AAAPZ1234C on file.", "AAAPZ1234C"),
        ("GSTIN 27AAAAA0000A1Z5 on the tax invoice.", "27AAAAA0000A1Z5"),
        ("Deposit to 01-0123-0123456-00 by Friday.", "01-0123-0123456-00"),
        ("IRD number 123-456-789 on the invoice.", "123-456-789"),
        ("The key is sk-abcdefghijklmnopqrstuvwx, do not share.", "sk-abcdefghijklmnopqrstuvwx"),
        ("Set api_key=abc123def456 in the environment.", "abc123def456"),
    ],
)
def test_personal_and_secret_data_does_not_survive(rules, text, must_not_survive):
    result = redact(text, rules)
    assert must_not_survive not in result.text
    assert result.counts, "nothing was recorded as redacted"


def test_the_audit_trail_never_quotes_what_it_removed(rules):
    """A trail that repeats the value it masked has not masked it."""
    result = redact("email sunil@example.test and call 021 555 0199", rules)

    assert "sunil@example.test" not in str(result.counts)
    assert "021 555 0199" not in str(result.counts)
