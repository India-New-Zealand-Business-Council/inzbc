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
        # Found by review: `payment-card` accepted any 13 to 19 digits, so a product GTIN was
        # masked as a card. Trade content is full of long digit strings.
        "The tariff schedule identifies product GTIN 9401234567894.",
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
        ("The key is sk-XXXXXXXXXXXXXXXXXXXXXXXX, do not share.", "sk-XXXXXXXXXXXXXXXXXXXXXXXX"),
        ("Set api_key=REPLACE_ME_NOT_A_REAL_VALUE in the env.", "REPLACE_ME_NOT_A_REAL_VALUE"),
        # A full-width @ is a homoglyph, not a typo, and defeated the plain address rule.
        ("Contact sunil\uff20example.test about renewal.", "sunil\uff20example.test"),
        # A number split across a line break is still a number.
        ("call the office on 021 555\n0199 tomorrow", "021 555\n0199"),
        ("NZ Companies Office number 1234567.", "1234567"),
        ("Delegate born 14/08/1986 in Auckland.", "14/08/1986"),
        ("Work visa NZV123456 expires in March.", "NZV123456"),
        ("Background at https://www.linkedin.com/in/example-person here.", "example-person"),
    ],
)
def test_personal_and_secret_data_does_not_survive(rules, text, must_not_survive):
    result = redact(text, rules)
    assert must_not_survive not in result.text
    assert result.counts, "nothing was recorded as redacted"


def test_the_nzbn_keeps_its_own_label(rules):
    """A broad rule winning an overlap made the audit trail less precise than it should be.

    `payment-card` used to match any long digit run, so an NZBN was reported as a card. The data
    was removed either way, but an audit trail that misnames what it found is harder to trust.
    """
    result = redact("registered as NZBN 9429000000000", rules)

    assert "9429000000000" not in result.text
    assert "nzbn" in result.counts


def test_a_rule_whose_replacement_it_would_match_is_refused(tmp_path, monkeypatch):
    """Matching is not redacting.

    `{"pattern": "sunil", "replacement": "sunil"}` fires, satisfies the example check, and then
    substitution puts the value straight back while the count records a redaction. That is the
    backreference bug by another route.
    """
    import json

    from services.api.redaction import POLICY_PATH_ENV, RedactionPolicyError

    path = tmp_path / "p.json"
    path.write_text(json.dumps({"rules": [
        {"name": "email", "pattern": "sunil", "replacement": "sunil", "example": "mail sunil now"},
    ]}), encoding="utf-8")
    monkeypatch.setenv(POLICY_PATH_ENV, str(path))

    with pytest.raises(RedactionPolicyError, match="pattern matches"):
        load_policy(path)


def test_the_audit_trail_never_quotes_what_it_removed(rules):
    """A trail that repeats the value it masked has not masked it."""
    result = redact("email sunil@example.test and call 021 555 0199", rules)

    assert "sunil@example.test" not in str(result.counts)
    assert "021 555 0199" not in str(result.counts)
