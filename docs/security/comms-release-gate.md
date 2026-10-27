# Comms external-model release gate — #303

The synchronous and streaming drafting endpoints refuse model generation by default. Only the exact environment setting `COMMS_EXTERNAL_MODEL_ENABLED=true` enables drafting. All other values remain disabled.

**This is containment, not confidentiality validation.** Structured form fields and existing redaction do not identify every confidential name or relationship. This release switch does not resolve the remaining #303 exposure.

Before enabling, the INZBC privacy and security owners must approve the permitted input policy, complete an adversarial review of both endpoints and the staff UI, confirm provider processing and retention terms, and record who approved the release. Configure the existing gateway redaction policy separately. No publication, distribution or SIP production authorisation is implied.

Tests: `services/api/tests/test_comms_release_gate.py` checks that only the exact value `true` opens the gate, and `services/api/tests/test_comms_api.py` checks that both routes return 503 without calling the provider when it is unset or set to another value (and, when unset, that no draft is stored). The existing endpoint tests opt in explicitly. The issue remains open until the policy and technical protections are evidenced.
