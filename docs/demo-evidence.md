# Demo recording evidence — issue #135

An existing local recording made on 10 September 2026 was inspected on 16 October.
It is historical demonstration evidence, not a fresh production run, current test-count
certification, client acceptance session or production authorization.

| Artifact in `scripts/demo-recording/` | Verification |
|---|---|
| `inzbc-demo.webm` | Decodes as VP8, 1280 × 720, 141.44 seconds, 6,747,129 bytes |
| `inzbc-demo.vtt` | WebVTT caption track present |
| `demo-10.png` | Extracted/inspected overview frame |
| `demo-50.png` | Extracted/inspected Brief Builder frame with clearly tagged `[SEED]` candidates |
| `demo-105.png` | Extracted/inspected FTA Explainer frame |

The recording walks the overview, runs/candidates, Brief Builder, QA/CEO refusal states,
distribution, FTA Explainer, Comms and Member Portal. Frame inspection confirms rendered UI
and captions, rather than an empty recording or script alone. Counts and copy are those visible
in September; do not quote them as the current implementation baseline.

SHA-256 of the recording:
`eecc0cbd582267bf1d3f0e779ab44bf86defb01848b331b7790f1aa5fa666319`

SHA-256 of the caption track:
`e69333052d6ee2f61a918bc9f3132f49769cebe52593d3a10ac7621f3fed1f4f`

The artifacts remain local and gitignored under the existing generated-output rule. This index
is the shared evidence record; it does not imply that a GitHub reader can download the local
video. Preserve/export these artifacts with the handover pack before deleting the local checkout.
They survive teardown of the backend/demo environment because playback needs no running service.
Reproducing a new walkthrough uses `scripts/record_demo.mjs` against a prepared seeded instance.
