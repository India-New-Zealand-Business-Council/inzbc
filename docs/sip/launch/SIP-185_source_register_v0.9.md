# SIP-185 Production Source Register (v0.9 Review Draft)

Source worklist for each run. Reconcile with the DB "Source Library" sheet before Day 1.
Layers follow SIP-050 (Official > Institutional > Sector > Media > discovery).

## Mandatory sources (must have an outcome every run)

### Official (Layer 1)
- NZ: MFAT, Beehive / ministerial releases, NZ Parliament, NZ Customs, RBNZ, Stats NZ, NZTE.
- India: Ministry of Commerce & Industry / PIB, Department of Commerce, MEA, PMIndia, RBI, DGFT.
- Bilateral: NZ-India FTA official pages, High Commission releases (both directions).

### NZ media (mandatory scan)
NZ Herald, RNZ, 1News, Stuff, Newsroom, BusinessDesk, Newstalk ZB, Rural News, Farmers Weekly,
relevant NZ Indian media.

### Controlled-access mandatory (known limitations)
- **Stuff** and **The Hindu BusinessLine** remain mandatory. Direct access is limited. Follow
  the full fallback sequence; a direct-access failure is not evidence that no item exists.

## Selective / triggered sources
Sector and specialist sources loaded when a relevant trigger appears (dairy, wool, agritech,
education, tech/AI, aviation, energy, manufacturing, investment, geopolitics).

## Standing monitoring sources
- **ACT-009** — India forced-labour import-compliance framework (weekly + trigger).
- **WL-006** — India Wool Sector watch (weekly; escalate only verified NZ-specific items).

## Fallback sequence (per source, in order)
1. Direct access
2. Search within the source
3. Indexed site search
4. Recognised news / document index
5. RSS or approved feed
6. Controlled keyword search
7. Secondary discovery source
8. Primary-source verification before material use

## When verified content cannot be accessed
- Record outcome `Inaccessible`; retain every fallback attempt and the reason.
- Do not rely on a headline/snippet for High or Critical claims.
- Retest weekly. Keep the source mandatory. Never silently omit it.

## Source outcome codes
Canonical list, mirrored in `docs/sip/SIP_Reference_Config.json` (`source_outcomes`) — this is
the list SIP-184 §4 requires an entry from for every mandatory source, and the one SIP-188 checks
for blanks:

**Included · Context · Suppressed · Inaccessible · Excluded · No Qualifying Item**

- `Excluded` takes a reason from `source_outcome_excluded_reasons` in the reference config —
  **Freshness · Relevance · Confidence** — recorded alongside the code, not as a separate
  top-level outcome. (Previously the reference config listed these as three separate codes,
  `Excluded: Freshness` etc., which didn't match this document; reconciled 22 Jul 2026 — the
  config now uses the same six codes as this document, plus the reason as a sub-field.)
- Operational extras (`source_outcome_extras` in the config) — **Duplicate · Not Applicable ·
  Verification Failed · Outside Coverage Window** — record on a source when applicable, in
  addition to one of the six core codes.
- **`No Material New Signal` is not a per-source outcome code** — it's the day-level conclusion
  in SIP-184 §9 / SIP-186 §11, recorded once for the run when every source came back with
  nothing qualifying. A single source with nothing to report still gets `No Qualifying Item`.
