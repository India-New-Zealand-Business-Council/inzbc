# Consolidated engineering and workflow answers — 16 October 2026

The tech lead records these answers here so one question does not become several process
tickets or new recurring obligations. Closed tickets remain as history; they are removed from
the active project board. This record does not assign new work or change the team contract.

| Topics / former tickets | Answer |
|---|---|
| PR review rota and backlog snapshot (#320) | Required review and merging remain with the tech lead. The old snapshot is stale; consult current PR checks and reviews. No review rota is adopted. |
| Process proposal / ADR-0008 (#385, #408) | Not adopted. Preserve the comparison as analysis; do not implement proposed process or permission changes. |
| GitHub daily check-ins (#405) | No additional issue-based attendance/update requirement. Follow the existing agreed communication and meeting arrangements. A missing GitHub comment is not evidence of absence or inactivity. |
| Reassigning platform AI tickets (#407) | No transfer is approved. The tech lead sets ownership and priorities; ask in the existing work discussion before changing them. |
| Extra retrospective, measurement and review obligations (#409, #410, #411, #414) | No additional issue-based obligations or causal claims about an unapproved rota. Existing documented sprint review/retrospective cadence remains. |
| Pairing and knowledge-sharing invitations (#412, #413) | Arrange by conversation with the participants; an invitation is not an assignment or mandatory ceremony. |
| Recurring board-maintenance issue (#415) | Keep actual delivery status accurate as part of normal work; no new recurring issue or reporting requirement. |
| Cross-run source-health persistence (#388) | Keep per-run reporting now. Do not enable stale-counter claims, grant the workflow write access to main, or rely on an evictable cache for durable counters. Defer durable counters to the existing backend integration work (#55); no additional persistence build is authorized now. |
| Uncovered-product FTA queries (#404) | Tech lead selects the general answer with an explicit missing-product-coverage warning and an INZBC follow-up. On 16 October the tech lead also confirmed INZBC agrees. This preserves useful general guidance while making the missing product-specific evidence explicit. Close the implementation ticket once the tested change lands. |
| FTA API depth (#392) | This is a real runtime integration gap, not a discussion-only ticket. Keep it open with its authorization/schema requirements. |
| Independent answer checking (#406), held-out evaluation (#390) | Valid quality checks; do not invent a human checker or call questions held-out after tuning against them. Keep these concrete deliverables separate from process invitations. |
| Literature/evaluation work (#387, #393, #402) | Preserve agreed research and measurable technical work. No new production ranker is authorized by a comparison result alone. |

Use the existing PR/issue conversation for a clarification tied to that work. Otherwise ask in
the agreed team channel. Only the tech lead authorizes a new issue for scope, assignments,
process, reporting, ceremonies or review arrangements, as already required by
[CONTRIBUTING.md](../CONTRIBUTING.md). Reproducible defects and approved deliverables remain
appropriate issues. Do not create another ticket merely to repeat or track one of the answers above.
