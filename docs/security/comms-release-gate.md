# Comms external-model release gate — #303

The synchronous and streaming drafting endpoints refuse model generation by default. Only the exact environment setting `COMMS_EXTERNAL_MODEL_ENABLED=true` enables drafting. All other values remain disabled.

**This is containment, not confidentiality validation.** Structured form fields and existing redaction do not identify every confidential name or relationship. This release switch does not resolve the remaining #303 exposure.

Before enabling, the INZBC privacy and security owners must approve the permitted input policy, complete an adversarial review of both endpoints and the staff UI, confirm provider processing and retention terms, and record who approved the release. Configure the existing gateway redaction policy separately. No publication, distribution or SIP production authorisation is implied.

Before merge, execute unit tests and end-to-end request tests for both routes, confirming disabled deployments never invoke the provider. Update any existing tests that depend on generation to set the opt-in explicitly. The issue remains open until the policy and technical protections are evidenced.
