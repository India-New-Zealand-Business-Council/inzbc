"""INZBC Information Standard - structured mirror of docs/information-standard.md.

Approved wording (Sunil Kaushal, CEO, 24 Jul 2026). Update the doc first, then mirror here -
the doc is the controlling reference, same relationship corpus.py has to
docs/fta-source-corpus.md.
"""

from __future__ import annotations

from enum import Enum

AI_INFORMATION_STANDARD = (
    "This response has been prepared using official government publications and trusted "
    "industry sources maintained by the India New Zealand Business Council (INZBC). While "
    "every effort is made to provide accurate and current information, regulatory requirements "
    "and commercial conditions can change. This response is intended as general business "
    "guidance and should not be relied upon as legal, taxation, customs, immigration or "
    "financial advice. Where an answer cannot be verified from authoritative sources, INZBC "
    "will indicate this rather than speculate. For advice specific to your business or "
    "transaction, please contact INZBC or an appropriately qualified professional adviser."
)


class Confidence(str, Enum):
    """Information Confidence Standard rating carried by every AI response."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    ACTION_REQUIRED = "Action Required"

    @property
    def meaning(self) -> str:
        return _MEANINGS[self]


_MEANINGS: dict[Confidence, str] = {
    Confidence.HIGH: "Verified using official government or treaty sources.",
    Confidence.MEDIUM: (
        "Verified using reputable industry or recognised secondary sources; users should "
        "confirm current requirements."
    ),
    Confidence.LOW: (
        "Limited authoritative information is available; the response is based on the best "
        "available evidence and should be independently verified."
    ),
    Confidence.ACTION_REQUIRED: (
        "INZBC recommends contacting the relevant government agency or seeking professional "
        "advice before proceeding."
    ),
}
