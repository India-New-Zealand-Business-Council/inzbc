import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workDir = "C:\\Users\\brett\\inzbc\\ppt_group_report_work";
const starterPath = path.join(workDir, "template-starter.pptx");
const finalPath = "C:\\Users\\brett\\inzbc\\INZBC_Group_Final_Report_Theory_Validation.pptx";
const renderDir = path.join(workDir, "theory-render");
const layoutDir = path.join(workDir, "theory-layout");
const montagePath = path.join(workDir, "theory-montage.webp");
const inspectPath = path.join(workDir, "theory-inspect.ndjson");

const teamReport = "C:\\Users\\brett\\Downloads\\INZBC_Team_Final_Report.docx";
const parasReport = "C:\\Users\\brett\\Downloads\\Evidence_Portfolio_Paras.docx";
const teamImage = "C:\\Users\\brett\\inzbc\\team_report_work\\bhanu-media\\image5.png";
const qualityImage = "C:\\Users\\brett\\inzbc\\team_report_work\\bhanu-media\\image3.png";
const theory = {
  sociotechnical: "Trist, E. L. and Bamforth, K. W. (1951), Some Social and Psychological Consequences of the Longwall Method of Coal-Getting, Human Relations 4(1), https://doi.org/10.1177/001872675100400101.",
  conway: "Conway, M. E. (1968), How Do Committees Invent?, Datamation 14(4), https://www.melconway.com/Home/pdf/committees.pdf.",
  psychologicalSafety: "Edmondson, A. (1999), Psychological Safety and Learning Behavior in Work Teams, Administrative Science Quarterly 44(2), https://doi.org/10.2307/2666999.",
  agile: "Beck, K. et al. (2001), Manifesto for Agile Software Development, https://agilemanifesto.org/.",
  continuousDelivery: "Humble, J. and Farley, D. (2010), Continuous Delivery: Reliable Software Releases through Build, Test, and Deployment Automation, https://martinfowler.com/books/continuousDelivery.html.",
  doubleLoop: "Argyris, C. (1977), Double Loop Learning in Organizations, Harvard Business Review, https://hbr.org/1977/09/double-loop-learning-in-organizations.",
  secureDefaults: "Saltzer, J. H. and Schroeder, M. D. (1975), The Protection of Information in Computer Systems, Proceedings of the IEEE 63(9), https://doi.org/10.1109/PROC.1975.9939.",
  clarkWilson: "Clark, D. D. and Wilson, D. R. (1987), A Comparison of Commercial and Military Computer Security Policies, IEEE Symposium on Security and Privacy, https://doi.org/10.1109/SP.1987.10001.",
  informationHiding: "Parnas, D. L. (1972), On the Criteria To Be Used in Decomposing Systems into Modules, Communications of the ACM 15(12), https://doi.org/10.1145/361598.361623.",
  swissCheese: "Reason, J. (2000), Human Error: Models and Management, BMJ 320(7237), https://doi.org/10.1136/bmj.320.7237.768.",
  dora: "Forsgren, N., Humble, J. and Kim, G. (2018), Accelerate: The Science of Lean Software and DevOps, IT Revolution Press, https://itrevolution.com/product/accelerate/.",
  boehm: "Boehm, B. and Basili, V. R. (2001), Software Defect Reduction Top 10 List, IEEE Computer 34(1), https://doi.org/10.1109/2.962984.",
};

const presentation = await PresentationFile.importPptx(await FileBlob.load(starterPath));
if (presentation.slides.items.length !== 20) {
  throw new Error(`Expected 20 starter slides; found ${presentation.slides.items.length}`);
}

function getShape(slideNumber, shapeId) {
  const slide = presentation.slides.items[slideNumber - 1];
  const target = slide.shapes.items.find((shape) => String(shape.id) === String(shapeId));
  if (!target) throw new Error(`Slide ${slideNumber}: missing shape ${shapeId}`);
  return target;
}

function setText(slideNumber, shapeId, nextText) {
  const shape = getShape(slideNumber, shapeId);
  const current = shape.text.toString();
  if (current.includes("\n")) {
    shape.text.set(nextText);
  } else {
    shape.text.replace(current, nextText);
  }
}

function setWidth(slideNumber, shapeId, width) {
  const shape = getShape(slideNumber, shapeId);
  const position = shape.position;
  shape.position = {
    left: position.left,
    top: position.top,
    width,
    height: position.height,
  };
}

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function replaceImage(slideNumber, imageId, imagePath, alt, fit) {
  const slide = presentation.slides.items[slideNumber - 1];
  const image = slide.images.items.find((item) => String(item.id) === String(imageId));
  if (!image) throw new Error(`Slide ${slideNumber}: missing image ${imageId}`);
  const frame = image.frame;
  const geometry = image.geometry;
  const borderRadius = image.borderRadius;
  const rotation = image.rotation;
  const flipHorizontal = image.flipHorizontal;
  const flipVertical = image.flipVertical;
  const lockAspectRatio = image.lockAspectRatio;
  await image.replace({
    blob: await readImageBlob(imagePath),
    contentType: "image/png",
    alt,
    fit,
  });
  if (frame) image.frame = frame;
  if (geometry) image.geometry = geometry;
  if (borderRadius) image.borderRadius = borderRadius;
  if (rotation !== undefined) image.rotation = rotation;
  if (flipHorizontal !== undefined) image.flipHorizontal = flipHorizontal;
  if (flipVertical !== undefined) image.flipVertical = flipVertical;
  if (lockAspectRatio !== undefined) image.lockAspectRatio = lockAspectRatio;
}

function setNotes(slideNumber, lines, extraSources = []) {
  const notes = [
    ...lines,
    "",
    "[Sources]",
    `- ${teamReport} - consolidated team report and evidence refreshed 20 August 2026.`,
    "- https://github.com/India-New-Zealand-Business-Council - organisation repository history.",
    ...extraSources.map((source) => `- ${source}`),
    "[/Sources]",
  ].join("\n");
  const speakerNotes = presentation.slides.items[slideNumber - 1].speakerNotes;
  speakerNotes.textFrame.setText(notes);
  speakerNotes.setVisible(true);
}

// 01 — Cover
setText(1, "8", "INDIA NEW ZEALAND BUSINESS COUNCIL");
setText(1, "9", "INZBC TEAM\nFINAL REPORT");
setText(1, "10", "Three specialist lanes. One governed delivery. Validation continues.");
setText(1, "11", "BHANU GUPTA   ·   ROSHAN ARYAL   ·   PARAS   ·   20 AUGUST 2026");
setNotes(1, [
  "Open with the final-team framing and make the phase explicit: strong implementation, continuing validation, no immediate handover claim.",
  "Set up the analytical frame the deck uses throughout: designed, built, tested and proven are four different states, and the repository is honest about which state each control is in.",
  "Every theory named in this deck is used as an explanation of evidence we can point at, not as decoration. If a claim has no artefact behind it, it is stated as a gap instead.",
]);

// 02 — Thesis
setText(2, "7", "THE TEAM RESULT");
setText(2, "9", "Three workstreams became one governed platform—now entering validation.");
setText(2, "10", "192 student-authored PRs  ·  184 merged  ·  138 board items");
setNotes(2, [
  "State the thesis before the detail: the evidence supports a controlled validation phase, not a completed handover.",
  "Theory: Accelerate argues throughput and stability rise together when work moves in small batches through automated verification. The merge record is offered as evidence for that relationship, not as a productivity score.",
  "The counter-evidence is kept in view. The requirements traceability matrix maps requirement to issue to pull request to test, and it still shows gaps; the acceptance register still shows rows as Blocked rather than backfilled.",
], [theory.dora]);

// 03 — Contents
setText(3, "8", "What the evidence proves");
setText(3, "10", "Mandate + theory");
setText(3, "11", "Sociotechnical trust and human authority.");
setText(3, "14", "Delivery + evidence");
setText(3, "15", "Agile feedback, quality gates and the live record.");
setText(3, "18", "Team + learning");
setText(3, "19", "Conway, psychological safety and reflection.");
setText(3, "22", "Next phase + readiness");
setText(3, "23", "What must close before any future handover.");
setNotes(3, [
  "Use the four parts as a narrative arc: theory explains the evidence, and readiness gates prevent an early handover claim.",
  "Two families of theory are in play. Organisational theory - Trist, Conway, Edmondson, Argyris - explains how the team produced the system. Engineering theory - Parnas, Saltzer and Schroeder, Clark and Wilson, Reason, Boehm - explains why the system refuses unsafe actions.",
  "The link between the two families is the argument of the whole deck: the controls in the code exist because of decisions the team made about authority, and neither half stands alone.",
], [theory.sociotechnical, theory.conway, theory.psychologicalSafety, theory.agile, theory.doubleLoop, theory.informationHiding, theory.secureDefaults]);

// 04 — Chapter one
setText(4, "9", "Built for trust,\nnot just demos");
setText(4, "10", "Sociotechnical systems theory: dependable outcomes require technical controls and accountable human roles to work together.");
setNotes(4, [
  "Introduce the sociotechnical lens: the system includes people, authority, process and technology - not software alone.",
  "Trist and Bamforth's finding was that optimising the technical subsystem alone degraded the whole result. The design response here was to make human authority a first-class part of the machine rather than a step outside it.",
  "Evidence: three of the eleven run states are human gates, so the pipeline cannot complete without a person acting. The security design states the principle directly - GitHub authenticates, it never authorises - and authorisation is resolved from the platform's own role table.",
  "Clark and Wilson supply the security-theory counterpart: integrity is preserved by well-formed transactions plus separation of duty, which is exactly the analyst-reviewer split enforced in the schema.",
], [theory.sociotechnical, theory.clarkWilson]);

// 05 — Project mandate
await replaceImage(
  5,
  "19",
  teamImage,
  "INZBC public-site concept showing the New Zealand to India opportunity",
  "contain",
);
setText(5, "10", "Four connected outcomes,\none operating standard");
setText(5, "11", "INZBC asked for a SIP review workflow, FTA intelligence, a Communications Assistant and a refreshed public website. Every outcome had to preserve evidence, privacy and human authority.");
setText(5, "13", "Trade Intelligence / SIP review");
setText(5, "15", "FTA + communications services");
setText(5, "17", "Public website + member surfaces");
presentation.slides.items[4].speakerNotes.textFrame.setText([
  "Use the public-site concept as evidence of the design lane, not as a claim that every displayed fact is production-approved.",
  "Requirements method: the four outcomes were captured as MoSCoW-prioritised requirements with eight non-functional requirements attached, and the governing rule was that no requirement is invented to fill a gap. Where the client owed a fact, the document carries a placeholder rather than an estimate.",
  "The safeguards named here are non-functional requirements, not features: model calls stay server-side, controls fail closed, a named human reviews before publication, and distribution stays disabled by default.",
  "Worth stating plainly: the FTA Explainer makes no model call at all. It matches against a curated corpus and returns nothing when there is no match, so it is structurally incapable of inventing a trade fact.",
  "",
  "[Sources]",
  `- ${teamReport} — project mandate and safeguards.`,
  `- ${parasReport} — public-site work and design evidence supplied by Paras.`,
  `- ${teamImage} — INZBC public-site concept included in Bhanu's final evidence portfolio.`,
  "[/Sources]",
].join("\n"));
presentation.slides.items[4].speakerNotes.setVisible(true);

// 06 — Central argument
setText(6, "7", "THE THESIS");
setText(6, "9", "Trust is a chain\nacross every layer.");
setText(6, "10", "Joint optimisation: evidence, controls, interfaces and accountable people form one chain.");
setNotes(6, [
  "Map the project evidence to sociotechnical joint optimisation: a failure in either the technical or human subsystem weakens the result.",
  "A chain is the right metaphor because the controls are ordered and each one can refuse. A request without a session stops at authentication; with a session but no role it stops at authorisation; with the right role but the wrong author it stops at separation of duties; and every accepted write commits its own audit record in the same transaction.",
  "Clark and Wilson call this the pairing of well-formed transactions with separation of duty. The database enforces the second half directly - a run's analyst may not be its reviewer - so the constraint survives even if the application layer is wrong.",
  "State the honest limit: one half of separation of duties is enforced today. Authorship is checked; the role-pair conflict table exists in the schema but is deliberately unseeded, and the contract says so rather than implying full coverage.",
], [theory.sociotechnical, theory.clarkWilson]);

// 07 — Team lanes
setText(7, "6", "CONWAY'S LAW / THREE LANES");
setText(7, "8", "Team boundaries shaped system boundaries");
setText(7, "12", "Bhanu Gupta");
setText(7, "13", "Strong ×6. Shared platform, security, review and integration boundary.");
setText(7, "17", "Roshan Aryal");
setText(7, "18", "Intelligence, sources, FTA, collectors and service boundary.");
setText(7, "22", "Paras");
setText(7, "23", "Product/UX, review interfaces, member surfaces and public-site boundary.");
setNotes(7, [
  "Use Conway's Law as an explanatory lens: explicit communication and ownership boundaries were mirrored in contracts and interfaces.",
  "Conway predicts the mirroring will happen whether or not it is intended, so the team chose the boundaries first and let the architecture follow. Three lanes, three owned surfaces, one shared contract between them.",
  "Parnas explains why that worked in practice. Modules are decomposed around information each hides behind a stable interface, so the lanes shared contracts rather than files. The API contract and the generated OpenAPI schema were the interface; the TypeScript client is generated from that schema and never hand-written.",
  "The mechanism that made it hold is a continuous-integration job that fails the build when the generated types drift from the schema. Without that check the shared contract degrades into a shared assumption.",
], [theory.conway, theory.informationHiding]);

// 08 — Merge quality
setText(8, "6", "MERGE QUALITY");
setText(8, "8", "95.8%");
setText(8, "9", "of student-authored PRs merged");
setText(8, "10", "184 of 192 across Bhanu, Roshan and Paras · live organisation history refreshed 20 August 2026.");
setText(8, "11", "BHANU / 135 PRs");
setText(8, "13", "99.3%");
setText(8, "14", "ROSHAN / 35 PRs");
setText(8, "16", "88.6%");
setText(8, "17", "PARAS / 22 PRs");
setText(8, "19", "86.4%");
setWidth(8, "12", 340.8);
setWidth(8, "15", 304.1);
setWidth(8, "18", 296.4);
setNotes(8, [
  "Calculation: 184 ÷ 192 = 95.8%. Individual rates are 134/135, 31/35 and 19/22.",
  "Read this as a batch-size result rather than an effort result. Accelerate's finding is that small, frequently integrated changes raise throughput and stability together, because each change is small enough to review properly and to revert cleanly.",
  "The mechanism behind the merge rate is that a pull request had to name the issue it delivered and pass the full check suite before a human reviewed it, so most rejections happened before review rather than after.",
  "Do not over-claim. A merge rate measures the review process, not the quality of the running system; the evidence for quality is on the integration and validation slides.",
], [theory.dora, theory.continuousDelivery]);

// 09 — Team metrics
setText(9, "6", "TEAM DELIVERY");
setText(9, "8", "The live record shows sustained delivery");
setText(9, "9", "192");
setText(9, "10", "Student-authored PRs");
setText(9, "11", "Across all four repositories");
setText(9, "12", "184");
setText(9, "13", "Merged");
setText(9, "14", "95.8% of the student set");
setText(9, "15", "138");
setText(9, "16", "ProjectV2 items");
setText(9, "17", "121 unique student-assigned");
setText(9, "18", "01");
setNotes(9, [
  "Keep scopes separate: student-authored PRs, organisation repositories and private-board items are not summed together.",
  "Measurement discipline is itself the point. Three different populations are counted three different ways, and combining them would produce a larger number that means nothing.",
  "The same rule governs the repository's traceability matrix: each requirement is traced to a specific issue, pull request and test count, so a figure can be audited back to its source instead of being asserted.",
], [theory.dora]);

// 10 — Chapter two
setText(10, "9", "Feedback that\nconnects");
setText(10, "10", "Agile iteration and continuous delivery moved defect discovery earlier, where correction is cheapest.");
setNotes(10, [
  "Move from output volume to feedback theory: small changes, working software, review and automated gates shortened the learning cycle.",
  "Boehm and Basili's defect-reduction findings give the economic argument. The cost of correcting a defect rises sharply the later it is found, so the design goal is to move discovery as early as possible rather than to rely on a final inspection.",
  "Evidence: nine independent checks run on every pull request, including static analysis, a secret scan, a workflow linter and a link checker. The database schema is applied to a real Postgres instance on each run and the restore verifier is executed against that fresh schema, so a schema claim is tested rather than trusted.",
  "Continuous delivery is the enabling practice - the pipeline is the thing that makes early feedback automatic rather than dependent on somebody remembering.",
], [theory.agile, theory.continuousDelivery, theory.boehm]);

// 11 — Timeline
setText(11, "8", "Capability grew through iterative increments");
setText(11, "11", "FOUNDATION");
setText(11, "13", "Shared contracts");
setText(11, "14", "Schema, APIs, security");
setText(11, "15", "INTELLIGENCE");
setText(11, "17", "FTA + sources");
setText(11, "18", "Collectors, ranking, audit");
setText(11, "19", "INTERFACES");
setText(11, "21", "SIP + Comms");
setText(11, "22", "Real data, review states");
setText(11, "23", "PUBLIC SITE");
setText(11, "25", "Wix rebuild");
setText(11, "26", "Content, mobile, navigation");
setText(11, "27", "VALIDATE");
setText(11, "29", "UAT + readiness");
setText(11, "30", "Close evidence gaps first");
setNotes(11, [
  "This capability progression reflects iterative delivery. The current point is validation and readiness work; handover remains a later milestone.",
  "The ordering is not accidental. Contracts, schema and security came first because they are the decisions that are most expensive to reverse later; interfaces and content came after, because they are cheap to change once the contract is fixed.",
  "Architectural decisions were recorded as they were taken, with context, consequences and links between them. One decision record even pre-registered the conditions under which it should be superseded, and a later record fired on the first of those conditions - so the platform change was a decision rather than drift.",
  "The validation stage is a stage, not an afterthought. Its work is closing the evidence gaps that the earlier stages made visible.",
], [theory.agile, theory.continuousDelivery, theory.boehm]);

// 12 — Workflow
setText(12, "6", "ITERATIVE CONTROL LOOP");
setText(12, "8", "Continuous feedback keeps trust intact");
setText(12, "10", "Source evidence");
setText(12, "11", "Dated sources, collectors and approved facts.");
setText(12, "13", "Encode in contracts");
setText(12, "14", "FTA services, scoring and generated APIs.");
setText(12, "16", "Review by a human");
setText(12, "17", "Named approval, QA and refusal paths.");
setText(12, "19", "Authorised release");
setText(12, "20", "Default is off. UAT and approval open it.");
setNotes(12, [
  "Describe this as a feedback loop rather than a claim of production release. Each iteration produces evidence for the next decision.",
  "Saltzer and Schroeder's fail-safe defaults principle is the design rule for the last step: the default must be denial, and access is granted only by explicit positive action. A missing configuration must read as a refusal, never as permission.",
  "Evidence, four times over: distribution is disabled by default and the flag is server-only, so a client cannot request its own release. A missing redaction policy path refuses the model call. An unset cross-origin setting allows no origins rather than all. An unconfigured model gateway raises rather than proceeding.",
  "Their least-privilege principle appears in the audit trail too - the application's database login may insert and select on the audit log and nothing else, so the append-only property is a permission boundary, not a convention.",
], [theory.agile, theory.continuousDelivery, theory.secureDefaults]);

// 13 — Before / after
setText(13, "6", "BEFORE AND AFTER");
setText(13, "8", "Double-loop learning changed the rules");
setText(13, "10", "STARTING POINT");
setText(13, "12", "Separate specialist lanes");
setText(13, "14", "Hidden approval assumptions");
setText(13, "16", "Board state could drift");
setText(13, "18", "LEARNING RESPONSE");
setText(13, "20", "Shared contracts and APIs");
setText(13, "22", "Named review + audit trail");
setText(13, "24", "Gaps visible before release");
setNotes(13, [
  "Apply Argyris's double-loop learning: the team changed governing assumptions and controls, not only isolated defects. The board gap remains visible rather than being cosmetically rewritten.",
  "Single-loop learning corrects the error. Double-loop learning corrects the rule that allowed the error. The clearest example in this project: a role-checking function was written, tested and merged, but wired to no route at all - so the platform authenticated users without ever authorising them.",
  "The single-loop fix would have been to wire that one route. The double-loop fix was a conformance test that fails whenever any route carries no role requirement, which converts a class of defect into a build failure.",
  "The method finding is worth quoting from the security review itself: reading the diff found almost nothing, running the attack found everything. Eighteen defects were found that way, each in code that had already been reviewed and merged.",
  "Boehm's cost curve is why that timing matters: all eighteen were corrected before any production run existed, which is the cheapest point on the curve.",
], [theory.doubleLoop, theory.boehm]);

// 14 — Integration evidence
await replaceImage(
  14,
  "23",
  qualityImage,
  "Quality-gate workflow showing issue, pull request, automated gates, human review and merge",
  "contain",
);
setText(14, "6", "INTEGRATION EVIDENCE");
setText(14, "8", "CI made feedback the integration gate");
setText(14, "9", "02");
setText(14, "11", "Issue → PR → CI → human review → merge");
setText(14, "13", "187");
setText(14, "14", "Organisation merges");
setText(14, "15", "of 189 total · stewarded by Bhanu");
setText(14, "17", "60 review events");
setText(14, "18", "Across 45 pull requests and multiple revision rounds.");
setText(14, "20", "Strong ×6");
setText(14, "21", "Bhanu's PDR objectives are fully demonstrated.");
presentation.slides.items[13].speakerNotes.textFrame.setText([
  "Use this slide to connect quantitative activity to the controlled merge process.",
  "Reason's model of defence in depth is the right frame for this pipeline. No single barrier is assumed to be sound; each has holes, and safety comes from the holes not lining up. Automated checks miss intent, human review misses detail, and the contract check misses logic - so all three run.",
  "The same layering protects the data boundary to the external model. Source refusal at the gateway, then field-level minimisation, then policy-driven redaction, then operator procedure. Each layer is documented with what it cannot do, which is what makes it a layer rather than a guarantee.",
  "The redaction policy document is explicit that rule-based redaction cannot reliably catch names, titles and employers written in prose, and cites the published recall limits of the reference implementation. That is why the control moved to refusing the source rather than trying to clean it.",
  "Continuous delivery supplies the last piece: the barriers are worthless unless they run on every change, automatically, with no option to wave one through.",
  "",
  "[Sources]",
  `- ${teamReport} — Bhanu metrics, PDR assessment and integration findings.`,
  `- ${qualityImage} — evidence graphic generated from refreshed GitHub review and merge records.`,
  "- https://github.com/India-New-Zealand-Business-Council — organisation history.",
  `- ${theory.continuousDelivery}`,
  `- ${theory.swissCheese}`,
  "[/Sources]",
].join("\n"));
presentation.slides.items[13].speakerNotes.setVisible(true);

// 15 — Chapter three
setText(15, "9", "Psychological safety made\nteamwork stronger");
setText(15, "10", "Risks, review requests and unknown facts were surfaced instead of hidden, allowing the team to learn safely.");
setNotes(15, [
  "Use psychological safety as the lens for change requests, mutation testing, honest gap reporting and client escalation - not as a claim that the team never disagreed.",
  "Edmondson's construct is the shared belief that the team is safe for interpersonal risk-taking, and her measurable consequence is that people report errors instead of concealing them. The observable proxy in this project is documentary: nearly every controlled document carries a section on what has not been proven.",
  "Concrete instances: the security design ends with a list of known gaps, the restore procedure separates what has actually been proven from what has not, the acceptance register carries a rule against backfilling a result from assumption, and the contract states which half of separation of duties is not yet enforced.",
  "Reporting a gap is the behaviour the theory predicts. A team without safety produces documents that describe only what works, which the security design calls a marketing document rather than a design document.",
  "Peer review was adversarial by design and change requests were normal, including requests raised against merged work. That is the same behaviour seen from the other direction.",
], [theory.psychologicalSafety]);

// 16 — Reflection
setText(16, "6", "TEAM REFLECTION");
setText(16, "10", "Double-loop learning changes the rule that produced an error, not only the error itself.");
setText(16, "12", "Applied reflection");
setText(16, "13", "Team evidence + Argyris (1977)");
setNotes(16, [
  "Connect the theory to the evidence: fail-closed controls, mutation testing and decision records altered the governing system rather than merely patching symptoms.",
  "Three governing rules changed during the project. First, a control is not considered present until an attack against it fails, which is why the security review ran the attacks instead of reading the diff. Second, an append-only guarantee belongs in the database and its permissions, not in application discipline. Third, a decision is not made until it is recorded with its consequences.",
  "Each of those changed how later work was done, which is the test that distinguishes double-loop from single-loop learning.",
  "The honest reading is that most of this was learned by being wrong first. The eighteen findings, the audit-log permission grant and the decision-record practice all followed a defect rather than preceding it.",
], [theory.doubleLoop, theory.boehm]);

// 17 — Communication practices
setText(17, "6", "HOW THE TEAM WORKED");
setText(17, "8", "Communication created a learning system");
setText(17, "10", "Focused PRs");
setText(17, "11", "Fast feedback");
setText(17, "13", "Clear ownership");
setText(17, "14", "Lower coordination cost");
setText(17, "16", "Safe challenge");
setText(17, "17", "Review + mutation tests");
setText(17, "19", "Real systems");
setText(17, "20", "Evidence over assumptions");
setText(17, "22", "Client escalation");
setText(17, "23", "Unknowns made visible");
setText(17, "25", "Readiness");
setText(17, "26", "UAT + runbooks");
setText(17, "27", "Conway explains the boundary design; psychological safety explains how risks and mistakes became visible and correctable.");
setNotes(17, [
  "Bhanu's communication evidence remains particularly strong: 141 authored issues, 60 review events, client-decision framing and broad readiness documentation.",
  "Conway explains the boundaries and Parnas explains why they held: the lanes met at a generated contract, so coordination cost stayed low without anyone needing to know the inside of another lane's code.",
  "Edmondson explains the other half. Safe challenge is listed here as a practice, and the evidence for it is that reviews rejected merged work and that documents record their own gaps.",
  "Client escalation belongs on this slide for the same reason. Where a fact was owed by the client, the repository rule was to record a placeholder rather than an estimate, so an unknown stayed visible instead of quietly becoming an assumption.",
], [theory.conway, theory.psychologicalSafety, theory.informationHiding]);

// 18 — Decisions
setText(18, "6", "NEXT PHASE");
setText(18, "8", "Three dependencies before production readiness");
setText(18, "10", "DEPENDENCY 01");
setText(18, "11", "Identity boundary");
setText(18, "12", "Confirm login ownership and the Member Jungle boundary.");
setText(18, "13", "CLIENT · BEFORE UAT");
setText(18, "15", "DEPENDENCY 02");
setText(18, "16", "Reviewer + secrets");
setText(18, "17", "Name the reviewer; provide OAuth secrets and a rotation policy.");
setText(18, "18", "CLIENT · BEFORE UAT");
setText(18, "20", "DEPENDENCY 03");
setText(18, "21", "Operating model");
setText(18, "22", "Define UAT ownership, deployment support and board reconciliation.");
setText(18, "23", "TEAM + INZBC · VALIDATE");
setText(18, "24", "These are readiness conditions—not a declaration of handover.");
setNotes(18, [
  "Correct the phase explicitly: these dependencies must be resolved and validated before production readiness or any later handover is claimed.",
  "Use the four-state framing: designed, built, tested, proven. These three dependencies are the boundary between tested and proven, and none of them can be closed by writing more code.",
  "Two of the three need a decision from the client rather than work from the team - who owns the identity boundary, and who is named as reviewer. Separation of duties is unenforceable until a second named person exists, so this is a control dependency, not an administrative one.",
  "The continuity controls are in the same state. The restore procedure is written and verified against the schema on every build, but no production database has ever been restored, so recovery time is unknown and is recorded as unknown.",
], [theory.clarkWilson, theory.secureDefaults]);

// 19 — Closing
setText(19, "9", "Continue validation");
setText(19, "10", "The implementation is strong; UAT, client decisions, board reconciliation and operating-model definition come before any handover.");
setText(19, "11", "INDIA NEW ZEALAND BUSINESS COUNCIL");
setNotes(19, [
  "Close on the evidence-based phase statement: strong implementation, continued validation, future handover only after readiness gates close.",
  "The theoretical claim of the whole deck in one sentence: a governed system is the joint optimisation of technical controls and human authority, and this project can show the artefacts for both halves.",
  "The evidential claim is narrower and should be said in the same breath. What is proven is what has been executed - the checks, the schema guards, the refusals. What is designed but not proven is listed rather than implied.",
  "Argyris is the right note to end on: the lasting output is not the code, it is the changed rules about what counts as done.",
], [theory.sociotechnical, theory.doubleLoop]);

// 20 — Evidence trail
setText(20, "7", "EVIDENCE TRAIL");
setText(20, "9", "Evidence guides the next phase");
setText(20, "10", "Bhanu · Roshan · Paras");
setText(20, "11", "Studio 5 delivery team · INZBC");
setText(20, "12", "GITHUB");
setText(20, "13", "India-New-Zealand-Business-Council");
setText(20, "14", "BOARD");
setText(20, "15", "INZBC SIP Platform · ProjectV2 #1");
setText(20, "16", "REPORT");
setText(20, "17", "Refreshed 20 August 2026");
setText(20, "19", "Validate in UAT.\nClose client decisions.");
setText(20, "20", "Next: UAT, client decisions and board reconciliation—then plan handover.");
presentation.slides.items[19].speakerNotes.textFrame.setText([
  "Close on the validation work required before any future handover and leave the audience with the evidence locations.",
  "Point the audience at where each theoretical claim can be checked. Architecture and contracts sit in the schemas directory; decision records in the decisions directory; the security design and the eighteen-finding review under security; governance, privacy, incident response and restore procedures in the docs root.",
  "The security, privacy and continuity register is the single best place to start, because it lists fifteen required controls with an owner and an honest status against each - including the ones marked not done.",
  "Invite verification rather than trust. Every figure in this deck traces to the organisation's own repository history and to the consolidated team report.",
  "",
  "[Sources]",
  `- ${teamReport} — final report and evidence index.`,
  "- https://github.com/India-New-Zealand-Business-Council",
  "- https://github.com/India-New-Zealand-Business-Council/inzbc",
  "- https://github.com/India-New-Zealand-Business-Council/inzview",
  "- https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent",
  "[/Sources]",
].join("\n"));
presentation.slides.items[19].speakerNotes.setVisible(true);

await fs.rm(renderDir, { recursive: true, force: true });
await fs.rm(layoutDir, { recursive: true, force: true });
await fs.mkdir(renderDir, { recursive: true });
await fs.mkdir(layoutDir, { recursive: true });

for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.items[index];
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await presentation.export({ slide, format: "png", scale: 1.5 });
  await fs.writeFile(path.join(renderDir, `${stem}.png`), new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(layoutDir, `${stem}.layout.json`), await layout.text(), "utf8");
}

const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(montagePath, new Uint8Array(await montage.arrayBuffer()));

const inspected = await presentation.inspect({
  kind: "slide,textbox,shape,image,notes,layout",
  maxChars: 1000000,
});
await fs.writeFile(inspectPath, inspected.ndjson || "", "utf8");

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(finalPath);

console.log(JSON.stringify({ finalPath, slides: presentation.slides.items.length, renderDir, layoutDir, montagePath, inspectPath }, null, 2));
