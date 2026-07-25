# SIP Backup & Restore Procedure (v0.9 Review Draft)

Closes the §18 backup gate for the controlled launch. Manual, no secrets, no automation. Protects
the **Intelligence Database workbook** and the daily evidence pack. A tested backup must be
retrieved and opened successfully **before Day 1**, or it is a Critical stop.

Pattern: 3-2-1-1-0 — 3 copies, 2 media, 1 off-site, 1 immutable (dated, never edited), 0 verified
errors (checksum + restore test).

## Copies
1. **Working copy** — the live DB workbook on the operator's machine.
2. **Off-site cloud** — OneDrive (via `sunil@inzbc.org`) or Google Drive. INZBC-owned account.
3. **Immutable dated copy** — `SIP-IntelligenceDatabase_YYYY-MM-DD.xlsx`, never edited after upload.
   Cloud version history provides rollback.

## Daily routine (each launch day)
1. Close the workbook. Copy it to the cloud folder as the dated file.
2. Record the SHA256 (see script). Note the backup in the run record.
3. Keep the immutable dated copies; do not overwrite prior days.

## Restore test (before Day 1 — the Critical gate)
1. Download the latest cloud copy to a temp folder (a **fresh** download, not the working file).
2. **Open it in Excel** — confirm all sheets load and the records are present.
3. Run `scripts/verify-backup.ps1` to confirm the downloaded copy's SHA256 matches the source and
   the file is non-empty.
4. Record: location, timestamp, owner, version, checksum, restore result, who tested.
5. If the download will not open or the checksum differs → **Critical stop**; do not start Day 1.

## Verify script
The script lives in the collection-engine repository (`daily-india-nz-news-agent`), because that is
the machine the operator runs the daily job from: `scripts/verify-backup.ps1` there.

```powershell
scripts\verify-backup.ps1 -Source "C:\path\SIP Intelligence Database v1.9.xlsx" `
                          -BackupCopy "C:\temp\downloaded-copy.xlsx"
```
Appends a row to `backup-log.csv` and prints PASS/FAIL. PASS = SHA256 matches and file is non-empty.

## Backup log (record every backup + restore test)
| timestamp | owner | source | backup location | version | sha256 | restore result |
|-----------|-------|--------|-----------------|---------|--------|----------------|

## Recovery objectives (INZBC to confirm)
- Max acceptable data loss: __ (e.g. 1 day). Max acceptable outage: __ .
- Restore owner: __ . Manual fallback if the cloud is unavailable: __ .
