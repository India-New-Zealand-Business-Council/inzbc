# SIP confirmed-outcome staging adapter (#344)

`source_outcome_adapter.prepare_confirmed_source_checks` validates human-confirmed, run-scoped source outcomes against the SIP-185 source register and `SourceIdLookup`. It returns Pydantic `SourceCheck` objects; it **does not perform HTTP requests, write to a database, infer outcomes from fetch-health, authorize a run or certify mandatory coverage**.

Example (using an explicitly confirmed observation):

```python
checks = prepare_confirmed_source_checks(run_id, observations, id_lookup)
# Only an authorised caller using the established session + CSRF flow may later call:
# for check in checks:
#     client.record_source_check(run_id, check)
```

Each observation requires an explicit human checker, evidence reference, matching run ID and controlled `SourceOutcome`. The adapter fails for unknown SIP-185 codes, duplicate codes, missing source-library IDs, incorrect keyspaces, unsupported fallback steps and missing evidence. Failure leaves the caller without any checks to submit; it never interprets news-agent `ok` or `no_recent` as `No Qualifying Item`.

**Not yet integrated:** a collector evidence envelope that proves the run's locked coverage window and source-fetch semantics, authorization of an automatic submission path, the UI/REST contract, and the permitted mapping from collector observations to human-reviewed SIP-185 outcomes. Bhanu's approval of that wider integration should be recorded in #344 / PR #443 before extending this staging boundary. This helper is not a substitute for the 112-source Critical-stop gate or a basis for running #55 without SIP-191 authorization.
