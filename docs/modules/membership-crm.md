# Module — Membership / CRM

Owner: Bhanu + INZBC · Status: planned (decision-gated) · System of record: **Member Jungle (provisional)**.

## Purpose
The member and organisation register and its business rules. This is the highest-risk module: it
touches payments, consent, and legal (Incorporated Societies) obligations. **Do not rebuild it on
Wix before the retain/integrate/replace assessment.**

## Foundation decision (before any build)
Retain Member Jungle · integrate it · or replace with Wix Pricing Plans + a new CRM (brief §4).
Recommended first release: Option A or B (keep Member Jungle as system of record).

## Records
Current + former members, join/cessation dates, contact details, consent evidence,
organisation↔individual relationships, status + renewal history, corrections + audit.

## Business rules INZBC must approve (brief §10.4)
Categories + names, fees/GST, application questions + approval authority, eligibility, renewal
model, grace period, failed-payment process, refund/cancellation, suspension/termination, corporate
seats, billing rules, benefits by category, directory fields + consent, former-member retention,
manual-payment exceptions, invoice/receipt/accounting reconciliation.

## Legal / privacy
Incorporated Societies Act member-register requirements (join + cessation dates, retention). PIA
before any migration. Member Jungle hosts primary data in Australia → cross-border assessment.

## Dependencies
The four foundation decisions; INZBC business rules + legal docs; payment provider.

## Definition of done
Business rules implemented; legal register fields supported; application/approval/renewal/expiry/
cessation tested; corporate membership tested; payments/invoices/GST/refunds/reconciliation tested;
migration reconciled to source totals; access/correction workflow tested.
