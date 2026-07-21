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
Included · Context · Suppressed · Inaccessible · Excluded · No Qualifying Item
(plus, if used operationally: No Material New Signal · Duplicate · Not Applicable ·
Verification Failed · Outside Coverage Window).
