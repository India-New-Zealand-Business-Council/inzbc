# apps/sip/collector — integration with the collection agent

Owner: Roshan. Meant to map the `daily-india-nz-news-agent` repo's output onto
`apps/sip/pipeline`'s `Candidate`/`SourceCheck` models, then write it into a run via
`apps/sip/pipeline/client.py`.

**Intentionally empty beyond this README.** Two things block writing the actual mapping code:

1. **`daily-india-nz-news-agent`'s real output schema is unknown here.** It's a separate repo,
   not available in this environment. Guessing its field names/format instead of reading them
   would mean this module needs a rewrite the moment someone actually checks — not worth doing.
2. **Collection-engine secrets aren't supplied yet** (tracked in `docs/workstreams/roshan.md`'s
   blocked list) — nothing here could run against a real feed even with the mapping written.

Once both are available: read the agent's actual output shape, write a
`map_agent_output_to_candidate()` function against it (targeting `apps.sip.pipeline.models.Candidate`),
and wire it to `apps.sip.pipeline.client.SipPipelineClient.create_candidate`. Do not build this
against an assumed schema in the meantime.
