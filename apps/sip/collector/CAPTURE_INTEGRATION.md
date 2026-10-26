# Review-only collector capture verification (#55)

`apps.sip.collector.capture_manifest` validates the exact JSON export contract introduced by `daily-india-nz-news-agent` PR #15, which is stacked on its source-freshness PR #14. This module is **offline and read-only**. It never calls an external URL, creates a SIP run, captures candidates or supplies SIP-185 source checks.

Run `uv run python -m apps.sip.collector.capture_manifest --capture /secure/path/YYYY-MM-DD-sip-capture.json` to check source-health outcomes, article shape, public HTTP(S) URLs, timestamps, bounded file size, recorded counts and the exporter checksum. It prints a machine-readable report with all production, 112-source and locked-window verification flags explicitly `false`. Do not commit real data or paste private capture manifests into issues.

The exporter uses a **rolling** news window, whereas the authorised SIP-184 process requires a locked 07:00-to-07:00 Pacific/Auckland window. That timezone-local day may span 23 or 25 elapsed hours around DST changes. This validator therefore does **not** promote the export to production or infer `in_coverage_window` from the fetch times. When an authorised operator later captures candidates, the existing `ingest_articles` mapping should be given the locked window returned by the actual run API, and the operator must investigate all out-of-window/unknown-time articles and partial source health.

Even a green manifest check is *not* evidence of an SIP-191 written authority, a gateway provenance signature, a successful collector run, 112 mandatory SIP-185 outcomes, human QA, CEO ruling or a distribution record. The manifest checksum detects modified articles but is not an authenticated source signature. Source health does not equate to SIP-185 included/excluded outcomes. The existing authenticated `SipPipelineClient`, analyst-confirmed source-outcome adapter, and decision/audit controls remain authoritative.

No capture export has been run against live sources as part of this PR; tests are synthetic. The live production run and operator sign-off remain #55.
