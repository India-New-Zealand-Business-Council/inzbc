# INZBC AI Operating System (AIOS)

## Proposal, Governance, Architecture and Delivery Plan

**Version:** 1.0 Research-Reviewed Draft  
**Date:** 22 July 2026  
**Organisation:** India New Zealand Business Council Incorporated  
**Programme owner:** INZBC  
**Delivery team:** Bhanu, Roshan and Paras  
**Immediate operational priority:** SIP controlled production launch, 27 to 31 July 2026

---

## Executive decision

This programme is strategically sound and should proceed, subject to the decision gates in this document.

The original proposal had the correct high-level components, separation of public and internal systems, human approval controls, phased delivery and three-person work split. It was not yet implementation-ready because it did not fully define:

1. The current Member Jungle system and whether INZBC will retain, integrate or replace it.
2. The legal, membership, payment, privacy and data-retention rules that the new system must enforce.
3. The system of record for each data type.
4. INZBC ownership, decision rights and approval roles.
5. Acceptance criteria, operational support, licensing, migration, incident response and handover.
6. The exact information, access, content and approvals that INZBC must provide.

### Approval recommendation

- **Phase 0, SIP controlled launch:** Proceed under the approved controlled launch documents and manual controls.
- **Phase 1, assessment and foundation:** Approve in principle, subject to the four foundation decisions below.
- **Phase 2, core build:** Start only after the Phase 1 gate is signed.
- **Phases 3 and 4:** Require a separate approved business case, cost estimate, licence plan and operating model.

### Four foundation decisions required before core build

1. **Membership platform:** Retain Member Jungle, integrate it with Wix, or replace it with Wix Pricing Plans and a new member database.
2. **Internal platform:** Microsoft 365 and Power Platform, or a repo-hosted application and database.
3. **Identity model:** Which identity service controls public members, staff, board members, administrators and service accounts.
4. **Budget and ownership:** Approved scope, licence budget, hosting budget, support model and named INZBC owners.

---

## 1. Purpose

AIOS will give INZBC one governed operating environment for:

- public communications and organisational credibility
- membership applications, approvals, renewals and member services
- events, delegations, sponsorships and trade-service requests
- controlled strategic intelligence through SIP
- sourced FTA information and sector guidance
- staff-assisted communications
- board and executive reporting

The programme must reduce manual work without reducing human control, institutional accountability or source quality.

---

## 2. Scope boundaries

### In scope

1. INZBC public website.
2. INZBC member portal.
3. SIP controlled production platform and collection engine.
4. FTA Implementation Centre and FTA Opportunity Explainer.
5. Staff-only AI Communications Assistant.
6. Membership, sponsor and trade-services records.
7. Events, delegations, introductions and engagement records.
8. Executive and board dashboards.
9. Integration, security, audit, backup, documentation and handover.

### Out of scope

- Waitakere Indian Association
- Kiwi Indians and kiwiindians.nz
- WAIP
- personal website and personal Executive Command Centre
- political systems, contacts and communications
- any other organisation's records, accounts, consent or brand assets

No data may be copied between these organisations unless there is a documented lawful purpose, the correct authority, an approved data-sharing rule and any required consent.

---

## 3. Operating principles

1. **INZBC owns the system.** Domains, repositories, cloud tenants, payment accounts, production data, API accounts and recovery methods must be controlled through INZBC-owned accounts.
2. **One system of record per data type.** The same member, payment or approval record must not be independently maintained in several systems.
3. **Public systems present approved information.** Internal applications perform controlled work and hold restricted records.
4. **Humans approve high-impact actions.** AI must not publish, email, approve membership, change controlled records or make material stakeholder decisions without human approval.
5. **Least privilege applies.** Each person receives only the access needed for their role.
6. **Privacy starts at collection.** INZBC collects only information needed for a defined lawful purpose.
7. **Every material action is traceable.** Approvals, edits, exports, publications, source decisions and system changes must be logged.
8. **Portability is required.** INZBC must be able to export its data, content, prompts, configurations and audit evidence in usable formats.
9. **No personal ownership dependency.** The system must continue if any developer, officer, contractor or staff member leaves.
10. **Build only after decisions.** No team member may fill an unresolved business rule with a technical assumption.

---

## 4. Current-state finding and membership decision

The current INZBC website sends membership applicants to Member Jungle. Member Jungle already provides membership records, approvals, renewals, online payments, invoices, event functions, restricted documents, exports and audit logs.

The original proposal assumed Wix Members Area and Wix Pricing Plans would become the member platform. Building that approach before reviewing Member Jungle could create:

- duplicate member profiles
- duplicate logins
- conflicting membership status
- payment and invoice reconciliation problems
- repeated consent collection
- uncertain ownership of the member register
- increased licence and support cost
- a risky data migration with limited benefit

### Recommended interim position

For Phase 1, treat Member Jungle as the provisional membership system of record until INZBC completes a retain, integrate or replace assessment.

### Required assessment

Compare the following options:

| Option | Description | Main benefit | Main risk |
|---|---|---|---|
| A | Retain Member Jungle and link it from the rebuilt Wix site | Lowest migration risk and keeps existing membership functions | Two branded environments and separate login experience |
| B | Retain Member Jungle as system of record and integrate selected data with Wix and M365 | Preserves current operations while improving reporting and user experience | Integration effort and cross-border data controls |
| C | Replace Member Jungle with Wix Pricing Plans plus an internal CRM | Greater presentation control inside Wix | High migration, payment, renewal, consent and support risk |
| D | Replace Member Jungle with a dedicated CRM or association platform | Stronger long-term enterprise model | Highest cost, procurement and implementation effort |

### Preliminary recommendation

Use **Option A or B for the first release**. Do not replace Member Jungle during the SIP launch or website rebuild unless the assessment proves a clear operational, financial and privacy benefit.

---

## 5. Target architecture

### 5.1 Public Wix site

The Wix site is the public publishing and conversion layer.

Public pages should include:

- Home
- About and history
- Constitution and governance information approved for publication
- Board, executive team and chapters
- Sponsors and strategic partners
- Events and registrations
- News, media and approved intelligence digests
- FTA Centre public overview
- Sector reports and publications
- Membership benefits and join pathway
- Trade services and market-entry support
- Delegations and opportunity notices
- Contact, privacy, terms, accessibility and complaints

Use Wix CMS, dynamic pages, forms, events, search, analytics and structured data where appropriate.

### 5.2 Member experience

The member experience must be based on the selected membership-platform decision.

It should provide:

- membership status and renewal
- organisation and contact details
- invoices and receipts
- member-only reports and FTA briefings
- event recordings and presentations
- delegation and trade opportunity notices
- market-entry request forms
- introduction request forms
- member discounts and sponsor benefits
- consent and directory preferences

### 5.3 Internal operating environment

The internal environment is not public and must use stronger access controls.

It includes:

- SIP production application
- SIP source, candidate, verification, QA, approval and publication records
- sponsor pipeline and benefit-delivery records
- trade-service requests and introductions
- delegation pipeline
- membership exception and approval workflows
- content approval workflow
- AI Communications Assistant
- dashboards and board reports
- system administration and audit

### 5.4 Collection and scheduled jobs

The existing `daily-india-nz-news-agent` remains the SIP collection engine.

GitHub Actions may run scheduled collection jobs, but scheduled workflows can be delayed or dropped under high load. The design must include:

- a non-zero-minute schedule where possible
- start, completion and output monitoring
- missed-run detection
- retry or controlled manual rerun
- failure notification
- duplicate-run protection
- source-window protection
- daily evidence retained in the SIP tracker

### 5.5 AI services

Use separate controlled AI workspaces for:

- SIP analysis
- FTA explanation
- communications drafting

Each workspace must have:

- approved purpose
- approved data classification
- provider and model record
- version-controlled prompt
- test set
- known limitations
- prohibited input rules
- output review requirement
- audit and retention rule
- shutdown owner

---

## 6. System-of-record map

INZBC must approve this map before data integration begins.

| Data type | Proposed system of record | Public copy allowed | Owner |
|---|---|---|---|
| Legal entity and constitution | INZBC controlled document library | Approved documents only | Board Secretary |
| Current and former member register | Member Jungle provisionally, pending decision | Directory opt-in fields only | Membership owner |
| Membership applications and approval | Membership platform | Status only to applicant | Membership approver |
| Payments, invoices, refunds and GST | Payment and membership platform, reconciled to accounting | No | Treasurer |
| Sponsor contracts and benefits | Internal CRM | Approved sponsor profile only | Sponsorship owner |
| Trade-service requests and introductions | Internal CRM | No | CEO or delegate |
| Event master record | Selected event platform | Event details and registration | Events owner |
| SIP intelligence and source evidence | SIP database and controlled document repository | Approved digest only | SIP production owner |
| FTA corpus and source snapshots | FTA knowledge repository | Approved sourced guidance | FTA content owner |
| Website content | Wix CMS, with controlled source documents | Yes | Website content owner |
| AI prompts, tests and evaluations | Git repository and AI governance register | No | AI service owner |
| Audit and incident records | Internal security and audit repository | No | Security owner |

No integration may write to a system of record unless the API contract, validation, permissions and audit behaviour are approved.

---

## 7. Identity and role model

The proposal must distinguish between four different concepts:

1. **Member category:** Individual, corporate, partner or other approved membership type.
2. **Commercial entitlement:** What a paid plan or sponsorship provides.
3. **Portal access:** Which content a person can view.
4. **Administrative authority:** What a staff member, board member or contractor can change.

These must not be treated as one Wix role list.

### Public and member identities

- Every member user has an individual login.
- Corporate membership must define the organisation record, primary contact, billing contact, authorised seats and seat-transfer rules.
- Directory publication must be opt-in and field-specific.
- Expired, suspended and former members must have defined portal access rules.

### Staff and administrator identities

- Staff, board and contractors use named accounts.
- Shared administrator accounts are prohibited except an approved emergency recovery account.
- MFA is mandatory.
- Privileged access must be reviewed at least quarterly and immediately when roles change.
- Contractor access must have an expiry date.
- Service accounts must have a named business owner and secret-rotation rule.

### Separation of duties for SIP

At minimum:

- Analyst captures and assesses candidates.
- Reviewer checks sources, reasoning and classifications.
- Approver authorises release.
- Administrator manages configuration but does not approve their own substantive output.

---

## 8. Delivery workstreams

### Bhanu: Technical lead, foundation, security and integration

Owns:

- target architecture
- system-of-record contracts
- data model and migrations
- API and webhook contracts
- authentication and role-based access control
- audit, state machine and disabled control flags
- secrets and environment management
- SIP application core
- deployment and monitoring
- backup and restoration
- code review and integration

### Roshan: Intelligence, sources, data and FTA

Owns:

- SIP collection integration
- source register and source outcomes
- candidate capture and verification logic
- FTA source corpus
- FTA knowledge model
- FTA Explainer service
- source freshness and citation controls
- data quality tests

### Paras: Public site, member experience and user interface

Owns:

- Wix public site
- approved member-portal experience
- CMS collections and dynamic pages
- forms and event experience
- SIP review, approval and register interface
- executive dashboard interface
- Communications Assistant interface
- accessibility and responsive design implementation

### INZBC responsibilities

INZBC owns:

- business rules
- content accuracy
- legal and privacy decisions
- membership and payment rules
- source and publication authority
- budget and licences
- acceptance testing
- production approval
- operational staffing
- post-handover administration

Developers advise and implement. They do not set INZBC policy.

---

## 9. Delivery phases and gates

### Phase 0: SIP controlled launch, 27 to 31 July 2026

**Purpose:** Run five controlled internal production days using the approved SIP launch pack, workbook, source register and human approval.

**Exit evidence:**

- all five daily runs recorded
- source outcomes recorded
- exceptions recorded and resolved or carried forward
- QA completed each day
- launch conditions assessed
- no unauthorised external publication or email
- final launch review approved

### Phase 1: Assessment and foundation

**Deliverables:**

- current-state system and data inventory
- Member Jungle assessment
- approved target architecture
- system-of-record map
- identity and role model
- privacy impact assessment
- data classification and retention schedule
- threat and risk assessment
- API and webhook contracts
- account and licence register
- environments and deployment plan
- content inventory
- migration plan
- acceptance test plan

**Gate:** Signed by INZBC Executive Sponsor, Finance Owner, Privacy Owner and Technical Lead.

### Phase 2: Core systems

**Deliverables:**

- rebuilt public website
- selected member experience
- SIP structured production application
- approved internal data store
- core audit and reporting
- backup and monitoring
- operational documentation

**Gate:** Privacy, security, accessibility, data, UAT and recovery tests passed.

### Phase 3: Activation

**Deliverables:**

- FTA Centre and Explainer
- sponsor and trade-services CRM
- delegation and introduction workflows
- AI Communications Assistant
- advanced member resources

**Gate:** Content governance, AI evaluation and business-owner acceptance passed.

### Phase 4: Automation and reporting

**Deliverables:**

- renewal and engagement automation
- sponsor benefit tracking
- SIP monitoring and exception dashboards
- board scorecards
- advanced analytics
- operational service reviews

**Gate:** Automation controls, failure handling, support and audit tests passed.

---

## 10. What INZBC must provide and approve

This is the required INZBC input pack. It replaces the shorter list in the original proposal.

### 10.1 Governance and authority

INZBC must provide:

- Board approval or delegated executive approval for the programme.
- Named Executive Sponsor.
- Named Product Owner or Programme Owner.
- Named Finance and Payment Owner.
- Named Privacy Officer or privacy decision owner.
- Named Security and Incident Owner.
- Named Membership Owner and membership approver.
- Named SIP Production Owner, Reviewer and Approver.
- Named FTA Content Owner.
- Named Website and Communications Content Owner.
- Named post-handover System Administrator.
- A decision register showing who may approve scope, budget, production release and external publication.

### 10.2 Legal and constitutional documents

INZBC must provide:

- current certificate or evidence of legal registration
- current constitution
- registered office and contact-person details
- membership approval and cessation rules
- board and officer authority rules
- dispute and complaints process
- financial approval limits
- current policies relevant to privacy, communications, records, conflicts and procurement

Before membership automation is built, INZBC must confirm that the system rules match the current constitution and the Incorporated Societies Act obligations that apply to INZBC.

### 10.3 Account and asset ownership

INZBC must provide or create organisation-controlled access for:

- Wix account and site
- domain registrar and DNS
- Cloudflare, if used
- Microsoft 365 tenant and SharePoint
- GitHub organisation and repositories
- Member Jungle administration
- payment provider
- accounting system
- analytics and Search Console
- newsletter and email platform
- AI provider and API accounts
- hosting and database accounts
- backup destination
- password manager and emergency recovery method

All production owners, billing contacts and recovery contacts must be INZBC-controlled addresses. Personal email addresses must not be the sole owner of any production asset.

### 10.4 Membership business rules

INZBC must approve:

- membership categories and exact names
- fees, GST treatment and service charges
- application questions
- approval authority and target turnaround
- eligibility rules
- annual or rolling renewal model
- start and expiry dates
- grace period
- failed-payment process
- refund and cancellation rules
- suspension and termination rules
- corporate membership seats
- billing and primary contact rules
- member benefits by category
- event-discount rules
- member directory fields and consent
- former-member retention and access
- manual payment and exception process
- invoice, receipt and accounting reconciliation process

### 10.5 Current member and contact data

INZBC must provide an inventory of:

- Member Jungle members and membership history
- former members required for legal records
- member applications in progress
- payment and invoice history required for migration or reference
- newsletter subscribers
- event attendees
- sponsors and partner contacts
- stakeholder and government contacts
- trade-service enquiries
- delegations and introductions
- website form submissions
- any spreadsheets or contact lists held by staff or board members

For each dataset, record:

- owner
- purpose
- source
- fields
- number of records
- consent status
- quality issues
- duplicates
- sensitive fields
- overseas storage or processing
- retention rule
- proposed system of record
- migration or deletion decision

### 10.6 Content and brand pack

INZBC must provide:

- current logo files and usage rules
- colour and typography rules
- approved positioning and key messages
- membership benefit copy
- current board and executive details
- chapter details
- patron and sponsor details
- sponsorship tiers and benefits
- event archive
- publications and reports
- media releases
- testimonials approved for use
- photographs with confirmed usage rights
- contact details and office addresses
- social channels
- SEO priorities and target audiences
- required legal notices

Each content area must have an owner and review date.

### 10.7 SIP inputs and approvals

INZBC must provide or approve:

- final controlled SIP document set
- current SIP Master Register
- Intelligence Database
- Production Source Register
- source access accounts and subscriptions
- publication and distribution rules
- daily production roles and substitutes
- escalation contacts
- acceptable output formats
- member alert thresholds
- CEO action thresholds
- retention and archive rules
- normal production start authority

### 10.8 FTA Centre inputs

INZBC must provide or approve:

- official source hierarchy
- sectors in scope
- target user groups
- terminology and disclaimer
- legal and technical review process
- update frequency
- change-alert rules
- ownership of tariff, rules-of-origin and sector content
- correction and withdrawal process
- public, member-only and internal content classifications

### 10.9 Communications Assistant inputs

INZBC must provide or approve:

- approved voice and style guidance
- channel rules for email, website and social media
- stakeholder sensitivity rules
- prohibited topics and data
- approval matrix
- approved templates
- test scenarios
- publication and send controls
- record-keeping requirements

### 10.10 Finance, licences and procurement

INZBC must approve a total cost model covering:

- Wix plan and apps
- Member Jungle current and future cost
- payment transaction and service fees
- Microsoft 365 licences
- Power Apps and Power Automate licences
- GitHub Team
- hosting, database and monitoring
- AI subscription and API use
- domain and DNS
- backup storage
- security tools
- development support
- post-handover maintenance
- contingency

Do not assume standard Microsoft 365 rights cover every Power App or connector. Premium components, custom connectors and managed environments can require additional licences.

### 10.11 Testing and sign-off resources

INZBC must nominate users for:

- public website content review
- membership application and renewal tests
- corporate membership tests
- payment, invoice, refund and reconciliation tests
- portal access tests
- SIP analyst, reviewer and approver tests
- FTA content accuracy tests
- accessibility tests
- mobile and browser tests
- privacy and consent tests
- backup restoration test
- incident-response exercise

---

## 11. Privacy, records and legal controls

### 11.1 Privacy impact assessment

Complete and approve a Privacy Impact Assessment before:

- migrating member data
- connecting Wix, Member Jungle, Microsoft 365 or a repo service
- using personal information in an AI tool
- creating member profiling or engagement scoring
- sending data overseas
- introducing a new public form

Update the assessment when purpose, provider, model, fields, integrations or use changes.

### 11.2 Collection notices

Every form must state, in plain language:

- what information is collected
- why it is needed
- whether it is required or optional
- who receives or can access it
- where it is held
- whether it is processed outside New Zealand
- how long it is retained
- how the person can access or correct it
- who to contact about privacy

Indirectly collected personal information must also be assessed against the notification duties that took effect in May 2026.

### 11.3 Data minimisation

Do not collect a field because it may be useful later. Every personal-information field requires a recorded purpose and owner.

### 11.4 Overseas processing

Member Jungle states that primary member databases are hosted in Australia and that selected providers process data for payments, support, analytics and security. INZBC must document this in its Privacy Impact Assessment and assess cross-border disclosure and contractual safeguards.

### 11.5 Retention and deletion

Create a retention schedule for:

- current members
- former members
- applications and rejected applications
- payment and accounting records
- event registrations
- sponsor and trade-service records
- website enquiries
- newsletter records
- SIP evidence and reports
- AI prompts and outputs
- audit and incident records

Where the Incorporated Societies Act 2022 applies, the member register must include required current and former member details, including cessation dates for former members within the required period.

### 11.6 Access and correction

Provide a controlled process for people to request access to and correction of their personal information. Record the request, decision, response date and any correction propagated to connected systems.

### 11.7 Privacy breaches

Maintain a privacy-breach response process that covers:

1. containment
2. assessment
3. evidence preservation
4. executive and privacy escalation
5. notification decision
6. notification to affected people where required
7. notification to the Privacy Commissioner where required
8. remediation and lessons learned

Serious privacy breaches should be notified as soon as practicable. The Privacy Commissioner states that 72 hours is the expected guide after the organisation becomes aware that a breach is notifiable.

---

## 12. Security and resilience controls

### Mandatory controls

- MFA for all administrator, staff and privileged accounts
- single sign-on where practical
- least privilege
- separate development, test and production environments
- no secrets in source code, documents or chat messages
- managed secret storage and rotation
- encrypted data in transit and at rest where supported
- dependency and vulnerability scanning
- protected branches and reviewed pull requests
- logging for login, permission, data export, approval, publication and configuration changes
- alerting for failed jobs, failed backups and unusual access
- approved incident response plan
- quarterly access review
- annual supplier and integration review
- tested backup and restoration
- documented recovery time and recovery point objectives

### Backup standard

Backups must cover all critical data and configuration, not only files.

At minimum:

- automated backups
- failure alerts
- protected backup access
- an off-platform copy for critical controlled records
- regular single-record restoration test
- periodic full restoration exercise
- documented recovery owner

### Recovery objectives

INZBC must define:

- maximum acceptable data loss for each system
- maximum acceptable outage for each system
- priority order for restoration
- manual fallback process
- stakeholder communication owner

---

## 13. AI governance

### Approved use only

Every AI use case must have:

- business owner
- defined purpose
- approved provider and model
- approved data classification
- Privacy Impact Assessment where personal information is involved
- risk assessment
- test set and acceptance threshold
- human reviewer
- output-use rule
- audit and retention rule
- incident and withdrawal process

### Prohibited by default

Unless separately approved, AI must not:

- receive member, sponsor or stakeholder personal information
- receive confidential government or commercial information
- make membership acceptance or rejection decisions
- publish or send externally
- alter a controlled SIP record
- create unsupported FTA claims
- infer sensitive personal attributes
- train on INZBC data
- take autonomous action through connected accounts

### Output controls

- Factual claims must be traceable to sources.
- FTA answers must show source and effective date.
- Draft communications must be labelled as drafts until approved.
- Material output must have a named reviewer.
- Known limitations and common failure modes must be documented.
- Evaluation must include hallucination, bias, privacy, prompt injection and sensitive-data tests.

---

## 14. FTA Centre governance

The FTA Centre must be a sourced information service, not an unsupervised general chatbot.

### Required source order

1. Official New Zealand treaty and government sources.
2. Official Government of India and customs sources.
3. Official tariff, rules-of-origin and implementation material.
4. Approved regulator and standards sources.
5. Approved INZBC analysis that clearly identifies interpretation.

### Every material answer must contain

- answer date
- source date or effective date
- source citation
- jurisdiction
- assumptions
- next practical step
- disclaimer where professional advice may be required

### Content lifecycle

Each content item needs:

- owner
- source
- version
- approval status
- effective date
- review date
- superseded status
- correction history

---

## 15. Membership and CRM controls

### Member register

The member system must support:

- current and former members
- join date
- cessation date
- last known contact details where required
- membership consent evidence
- organisation and individual relationships
- status history
- renewal history
- corrections and audit

### Corporate membership

Define:

- legal or trading organisation name
- primary member contact
- billing contact
- authorised portal users
- number of seats
- seat addition, removal and transfer
- benefit eligibility
- directory listing consent
- continuity when a contact leaves the organisation

### Sponsor records

Store:

- agreement term
- financial and in-kind value
- tier
- promised benefits
- owner
- delivery dates
- evidence of delivery
- renewal date
- relationship notes
- consent and communication rules

### Trade-service and introduction records

Store:

- request purpose
- requesting organisation
- sector and market
- consent to share details
- assigned owner
- actions
- introductions made
- outcome
- confidentiality classification
- closure reason

---

## 16. Acceptance criteria

No phase is complete because a page or feature exists. It is complete only when the required evidence passes.

### Public website

- approved information architecture and page content
- current board, sponsor, membership and contact information
- privacy, terms, accessibility and complaints pages
- mobile, browser and performance tests
- WCAG 2.2 Level AA target assessment
- forms deliver to the correct owner
- spam protection and failure handling
- analytics and Search Console configured
- redirects and SEO metadata verified
- content owners trained

### Membership

- approved business rules implemented
- legal register fields supported
- application, approval, renewal, expiry and cessation tested
- corporate membership tested
- directory consent tested
- payments, invoices, GST, refunds and reconciliation tested
- member export tested
- access and correction workflow tested
- migration reconciled to source totals

### SIP

- state transitions enforced server-side
- role separation tested
- mandatory source outcomes recorded
- source evidence retained
- QA and approval gates enforced
- missed-run and failed-run process tested
- duplicate prevention tested
- audit export tested
- controlled reports match approved templates

### FTA Centre

- source hierarchy implemented
- citations and effective dates visible
- stale content detection tested
- correction and withdrawal tested
- representative sector questions evaluated
- unsupported-answer behaviour tested

### AI Communications Assistant

- approved templates and style rules loaded
- prohibited-data tests passed
- hallucination and prompt-injection tests passed
- all outputs remain drafts
- external send and publish controls blocked by default
- review and audit trail tested

### Security and operations

- MFA and least privilege verified
- no production secrets in repositories
- monitoring and alerts tested
- backup completed and restoration proven
- incident-response exercise completed
- administrator exit and access-removal test completed
- runbooks and support contacts approved

---

## 17. Measures of success

INZBC should approve baseline and target values for:

### Website and membership

- membership application conversion
- application processing time
- renewal rate
- failed-payment recovery rate
- member portal activation
- member directory accuracy
- event registration conversion
- member service response time

### Trade and FTA services

- qualified FTA enquiries
- sector brief usage
- trade-service requests
- introductions completed
- recorded commercial outcomes
- delegation participation

### SIP

- scheduled runs completed
- mandatory source coverage
- QA pass rate
- correction rate
- time from collection to approved brief
- actionable CEO and member items
- unresolved exceptions

### Sponsors and governance

- sponsor benefits delivered on time
- sponsor renewal rate
- board report preparation time
- data-quality exceptions
- access-review completion
- backup and restoration test pass rate
- privacy and security incidents

---

## 18. Key risks and treatments

| Risk | Treatment |
|---|---|
| Rebuilding functions already provided by Member Jungle | Complete the platform decision before build and keep one membership system of record |
| Duplicate member identities | Approve identity map, unique identifier and synchronisation rules |
| Three systems holding conflicting member data | Limit each platform to an approved system-of-record role |
| Payment-provider change disrupts recurring plans | Decide provider before launch and test migration and member communications |
| Power Platform licence cost is underestimated | Confirm connectors, environments and user licences before architecture approval |
| Scheduled GitHub Action is delayed or dropped | Monitor runs, avoid top-of-hour schedules, alert and provide controlled rerun |
| AI exposes personal or confidential data | Approved workspaces, prohibited-input controls, PIA and human review |
| FTA information becomes stale | Effective dates, source hierarchy, review dates and withdrawal process |
| Contractor departure creates loss of access | INZBC-owned accounts, documentation, access expiry and handover tests |
| Public content is inconsistent or outdated | Content inventory, owner, review date and single source of truth |
| Data migration loses consent or status history | Field mapping, reconciliation, exception report and rollback plan |
| Cyber or privacy incident is mishandled | Tested incident and breach response with named owners |
| Scope exceeds three-person placement capacity | Phase gates, prioritised backlog and separate business case for later phases |

---

## 19. Immediate actions, 22 to 31 July 2026

### By 23 July

- Confirm Phase 0 SIP launch roles and substitutes.
- Confirm all SIP launch files are in their approved locations.
- Confirm source access, subscriptions and backup method.
- Name the INZBC Executive Sponsor, Product Owner, Privacy Owner and Security Owner.

### By 24 July

- Export a current Member Jungle data and configuration inventory.
- Record current membership categories, fees, application rules, renewals and payment provider.
- Confirm current legal registration evidence and constitution.
- Create the account and licence register.

### By 25 July

- Approve the Phase 0 incident, exception and communication contacts.
- Complete access checks and MFA checks.
- Test manual fallback and daily evidence capture.
- Freeze unapproved changes to launch-critical SIP configuration.

### By 26 July

- Complete launch rehearsal.
- Complete launch readiness review.
- Record all open conditions and owners.
- Confirm no normal production, automation or external distribution starts without authorised release.

### 27 to 31 July

- Run the five controlled internal production days.
- Complete daily QA and approval.
- Record source outcomes, exceptions, actions and evidence.
- Complete the controlled launch review and decide whether to proceed, remediate or pause.

### After controlled launch

- Start Phase 1 assessment.
- Complete Member Jungle retain, integrate or replace assessment.
- Approve the target architecture and system-of-record map.
- Do not begin member-data migration or payment replacement before the decision gate.

---

## 20. Required document set and locations

### Main INZBC repository

`India-New-Zealand-Business-Council/inzbc`

```text
/apps/site
/apps/sip
/apps/fta
/apps/comms
/services/api
/database
/docs
/docs/governance
/docs/privacy
/docs/security
/docs/data
/docs/membership
/docs/fta
/docs/sip
/docs/testing
/docs/operations
```

### Collection repository

`India-New-Zealand-Business-Council/daily-india-nz-news-agent`

The news-agent repository retains collection code, source configuration, scheduled workflow code and SIP launch evidence that belongs with the collection engine.

### Required controlled documents

```text
/docs/inzbc-ai-operating-system.md
/docs/governance/decision-register.md
/docs/governance/raci.md
/docs/governance/licence-and-account-register.md
/docs/data/system-of-record-map.md
/docs/data/data-inventory.md
/docs/data/retention-schedule.md
/docs/data/migration-plan.md
/docs/privacy/privacy-impact-assessment.md
/docs/privacy/privacy-notices.md
/docs/security/threat-and-risk-assessment.md
/docs/security/incident-response-plan.md
/docs/security/backup-and-recovery-plan.md
/docs/membership/platform-options-assessment.md
/docs/membership/business-rules.md
/docs/membership/member-data-map.md
/docs/fta/source-corpus.md
/docs/fta/content-governance.md
/docs/sip/build-plan.md
/docs/testing/master-test-plan.md
/docs/testing/acceptance-register.md
/docs/operations/runbooks.md
/docs/operations/handover-plan.md
```

---

## 21. Final INZBC approval statement

INZBC approval of this document means:

1. INZBC accepts the programme direction and scope boundaries.
2. Phase 0 may proceed under its separately approved controlled launch authority.
3. Phase 1 assessment and foundation may begin.
4. No core membership replacement, production data migration, payment migration, normal SIP automation, public AI release or external automated communication is authorised by this document alone.
5. Each later phase requires its stated gate, evidence and authorised sign-off.

---

## Research basis

The controls and recommendations in this document were checked against the following current primary guidance and product documentation on 22 July 2026:

- New Zealand Office of the Privacy Commissioner, Privacy Act principles and AI guidance: https://www.privacy.org.nz/privacy-principles/
- Privacy Principle 3A, indirect collection notification: https://www.privacy.org.nz/privacy-principles/3a/
- Privacy Principle 12, disclosure outside New Zealand: https://www.privacy.org.nz/privacy-principles/12/
- Privacy breach notification: https://www.privacy.org.nz/responsibilities/privacy-breaches/notify-us/
- AI and the Information Privacy Principles: https://www.privacy.org.nz/resources-and-learning/a-z-topics/ai/
- New Zealand Government Web Accessibility Standard 1.2: https://www.digital.govt.nz/standards-and-guidance/nz-government-web-standards/web-accessibility-standard-1-2
- New Zealand Responsible AI Guidance: https://www.digital.govt.nz/standards-and-guidance/technology-and-architecture/artificial-intelligence/responsible-ai-guidance-for-the-public-service-genai
- NCSC multi-factor authentication guidance: https://www.ncsc.govt.nz/protect-your-organisation/multi-factor-authentication/
- NCSC backup guidance: https://www.ncsc.govt.nz/protect-your-organisation/implement-and-test-backups/
- NCSC response planning: https://www.ncsc.govt.nz/protect-your-organisation/response-planning/
- Incorporated Societies records guidance: https://www.is-register.companiesoffice.govt.nz/help-centre/running-your-incorporated-society/records-you-should-keep/
- GitHub Actions scheduled workflow guidance: https://docs.github.com/en/actions/how-tos/troubleshoot-workflows
- Wix Pricing Plans payment guidance: https://support.wix.com/en/article/pricing-plans-setting-up-payments
- Wix recurring payment guidance: https://support.wix.com/en/article/accepting-recurring-payments
- Wix member roles: https://support.wix.com/en/article/site-members-creating-member-roles
- Microsoft Power Platform licensing: https://learn.microsoft.com/en-us/power-platform/admin/managed-environment-licensing
- Microsoft audit logging: https://learn.microsoft.com/en-us/purview/audit-log-enable-disable
- Member Jungle membership, payments and exports: https://www.memberjungle.com/membership-software/member-database
- Member Jungle association functions: https://www.memberjungle.com/solutions/association-management-software
- Member Jungle privacy and hosting disclosures: https://www.memberjungle.com/privacy
- Member Jungle audit reporting: https://support.memberjungle.com/system-report

