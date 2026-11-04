import fs from "node:fs/promises";
import path from "node:path";
import JSZip from "jszip";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "C:/Users/brett/Downloads/New folder/FINAL/INZBC_Final_Presentation.pptx";
const buildDir = "C:/Users/brett/inzbc/.codex-presentation-build/v04-draft";
const candidate = path.join(buildDir, "candidate.pptx");
const output = "C:/Users/brett/inzbc/.codex-presentation-build/v04-draft/INZBC_v04.pptx";
await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(path.dirname(output), { recursive: true });

const deck = await PresentationFile.importPptx(await FileBlob.load(source));
if (deck.slides.items.length !== 12) throw new Error(`Expected 12 slides, found ${deck.slides.items.length}`);

const ids = [
  { title:"sh/547294r6", body:"sh/k3yl0zql" },
  { kicker:"sh/9072xkry", title:"sh/ozy1ofad", body:"sh/b29kza94" },
  { kicker:"sh/cza94vmx", title:"sh/d0jax03i", body:"sh/298ryl4v", metrics:["sh/3ah8rqlg","sh/obq90bml","sh/pcjqtg36","sh/m5cra54z"] },
  { kicker:"sh/1cj2d8b6", title:"sh/0ba143al", body:"sh/rm1k7yt4" },
  { kicker:"sh/dgbulwnm", title:"sh/cf2tcr61", visual:"im/ulsbm18f" },
  { kicker:"sh/yhg7epsj", title:"sh/zi98nu94", body:"sh/98rqt4r6", visual:"im/nyp4fmls" },
  { kicker:"sh/cb2tkvap", title:"sh/dcbud0ra", body:"sh/zedcfa9g", visual:"im/5s3mtk7e" },
  { kicker:"sh/18byd4zy", title:"sh/g72x4zyd", body:"sh/ri9g7uhw" },
  { kicker:"sh/1cfmhgne", title:"sh/0b65obm9", body:"sh/nex4jq5k" },
  { kicker:"sh/xc3mho32", title:"sh/cbu58j2h", body:"sh/zelojyl8", metrics:["sh/ydcnatkn","sh/l036l83y","sh/kzu5c32t","sh/725onyl4"] },
  { kicker:"sh/xcryxg7y", title:"sh/wbih4b6d", body:"sh/n69grmpw" },
  { kicker:"sh/1gbm9s3a", title:"sh/0f2lgnmp", body:"sh/ra943il8" },
];

const notes = [
  "We’re Bhanu Gupta, Roshan Aryal and Paras. Over ten weeks, we worked with Sunil Kaushal and the India New Zealand Business Council to turn a recurring operational problem into a governed software platform. Today we’ll show the problem, the controls, what failed during development, and the working system.",
  "INZBC is volunteer-run, so valuable staff time disappears into repetitive daily work: scanning sources, answering tariff questions, and drafting member updates. The risk is inconsistency. The brief was therefore not ‘let AI write’; it was to automate the middle while refusing any unchecked claim at the member boundary.",
  "We built one application with four connected modules. SIP creates an approved intelligence brief; the FTA Explainer answers from a cited corpus; the Communications Assistant drafts only for named human approval; and the Member Portal is the member-facing shell. They share one backend, database, and React interface.",
  "The central design choice was refusal. Workflow state, recorded actions, database constraints, audit triggers, and deployment switches are intended to block unsafe paths before output reaches a member. That includes separation of duties, critical QA gates, redaction rules, and production distribution being disabled by default.",
  "This is the Strategic Intelligence Platform flow. Public sources are collected and normalized, candidates are scored and reviewed, a brief is drafted, QA is recorded, and only then can a CEO decision and distribution occur. Each step writes state and evidence back to the governed backend.",
  "The FTA Explainer deliberately keeps a language model out of the answer path. A user’s tariff question is matched against a curated corpus, and the response carries the relevant chapter and article citation. If the system cannot resolve a match, it escalates to a person instead of inventing an answer.",
  "For communications, the boundary is enforced before prompting. Member records, CRM notes, board papers, and private messages are rejected before a prompt is assembled. The model can help draft public-source material, but it never receives content that the policy classifies as private or restricted.",
  "We chose PostgreSQL because our requirements were constraint-shaped: legal workflow transitions, time ordering, audit immutability, and role-limited writes. That choice paid off when the database exposed a real clock mismatch between application and host. The refusal was inconvenient, but it proved the control was active.",
  "The most useful lessons came from quiet failures. Some controls existed in code and tests but were not reachable from routes; a content hash looked valid while covering the wrong material; and a flaky test attracted two plausible but incorrect diagnoses. Our response was to add stronger conformance checks and trace enforcement end to end.",
  "Version one is released, with five of six objectives achieved. Production deployment remains intentionally unattempted because that decision belongs to INZBC, and production remains disabled. The system is reproducible and documented, but our honest limitation is that it has been tested extensively rather than used through a real working week.",
  "Our next steps are deliberately practical: close the four client decisions, run one genuine brief with staff, add a second reviewer account, commission an accessibility audit before public launch, and keep the decision records current. The first real operating week should happen before any production switch is enabled.",
  "In the live demonstration, watch the backend state rather than the interface polish. We select a real run, load only that run’s candidates and coverage, then attempt a CEO decision too early. The system refuses because QA has not passed. That refusal is the project’s core claim made visible.",
];

const darkSlides = new Set([0,3,7,8,11]);
const DARK = "#080A0F", LIGHT = "#F4F0E8", INK = "#232A35", WHITE = "#F7F8FC";
const MUTED_DARK = "#C8CEDA", MUTED_LIGHT = "#434B59", BLUE = "#285CFF", CORAL = "#FF6B5F";

function setText(id, name, style, position) {
  const shape = deck.resolve(id);
  shape.name = name;
  if (position) shape.position = position;
  shape.text.style = { ...style, autoFit: "shrinkText" };
  return shape;
}

for (let i = 0; i < 12; i += 1) {
  const slide = deck.slides.getItem(i);
  const spec = ids[i];
  const dark = darkSlides.has(i);
  slide.background.fill = dark ? DARK : LIGHT;
  if (spec.kicker) setText(spec.kicker, "!!actor-kicker", { typeface:"Aptos", fontSize:15, bold:true, color:dark ? CORAL : BLUE, letterSpacing:1.4 }, null);
  setText(spec.title, "!!actor-title", { typeface:"Aptos Display", fontSize:i===0 ? 62 : (i===11 ? 56 : 42), bold:true, color:dark ? WHITE : INK, lineSpacing:0.94 }, null);
  if (spec.body) setText(spec.body, "!!actor-body", { typeface:"Aptos", color:dark ? MUTED_DARK : MUTED_LIGHT, lineSpacing:1.12 }, null);
  if (spec.visual) deck.resolve(spec.visual).name = "!!actor-visual";
  if (spec.metrics) spec.metrics.forEach((id, j) => setText(id, `!!actor-metric-${j+1}`, { typeface:"Aptos Display", bold:true, color:j % 2 ? CORAL : BLUE }, null));
  slide.speakerNotes.textFrame.setText(notes[i]);
  slide.speakerNotes.setVisible(true);
}

deck.resolve(ids[0].title).position = { left:72, top:185, width:1100, height:135 };
deck.resolve(ids[0].body).position = { left:76, top:350, width:910, height:185 };
deck.resolve(ids[1].title).position = { left:400, top:92, width:810, height:130 };
deck.resolve(ids[1].body).position = { left:400, top:232, width:790, height:390 };
deck.resolve(ids[8].title).position = { left:360, top:75, width:850, height:80 };
deck.resolve(ids[8].body).position = { left:360, top:170, width:830, height:465 };
deck.resolve(ids[10].title).position = { left:250, top:72, width:960, height:78 };
deck.resolve(ids[10].body).position = { left:250, top:172, width:940, height:460 };
deck.resolve(ids[11].title).position = { left:72, top:92, width:1100, height:110 };
deck.resolve(ids[11].body).position = { left:360, top:225, width:830, height:390 };

// Reset inherited run sizes so the new hierarchy is visible in PowerPoint.
for (let i=0;i<12;i++) {
  const layout=JSON.parse(await fs.readFile(`C:/Users/brett/inzbc/.codex-presentation-build/inzbc/slides/slide-${String(i+1).padStart(3,'0')}.layout.json`,'utf8'));
  const dark=darkSlides.has(i);
  for (const role of ['title','body']) {
    if (!ids[i][role]) continue;
    const shape=deck.resolve(ids[i][role]);
    shape.text=layout.elements.find(e=>e.aid===ids[i][role]).text;
    shape.text.style={typeface:role==='title'?'Aptos Display':'Aptos',fontSize:role==='title'?(i===0?78:48):(i===0?25:24),bold:role==='title',color:dark?'#F7F8FC':'#232A35',autoFit:'shrinkText',wrap:'square'};
    if(i>0 && ![4,5,6].includes(i)) shape.position=role==='title'?{left:72,top:82,width:1100,height:110}:{left:72,top:210,width:1100,height:ids[i].metrics?280:430};
  }
}
deck.resolve(ids[0].title).position={left:72,top:140,width:780,height:210};
deck.resolve(ids[0].body).position={left:72,top:390,width:760,height:200};
deck.resolve(ids[5].body).position={left:72,top:590,width:1100,height:90};
deck.resolve(ids[6].body).position={left:72,top:605,width:1100,height:70};
// Give the two results slides an unmistakable number / caption hierarchy.
for (const i of [2,9]) {
  const layout=JSON.parse(await fs.readFile(`C:/Users/brett/inzbc/.codex-presentation-build/inzbc/slides/slide-${String(i+1).padStart(3,'0')}.layout.json`,'utf8'));
  for (let j=0;j<4;j++) {
    const shape=deck.resolve(ids[i].metrics[j]);
    const text=layout.elements.find(e=>e.aid===ids[i].metrics[j]).text;
    const [number,...caption]=text.split('\n');
    shape.text=number;
    shape.position={left:72+j*280,top:510,width:260,height:92};
    shape.text.style={typeface:'Aptos Display',fontSize:76,bold:true,color:j%2?'#D7463D':'#285CFF',autoFit:'none'};
    const label=deck.slides.getItem(i).shapes.add({geometry:'textbox',name:`!!metric-caption-${j}`,position:{left:72+j*280,top:610,width:255,height:48},fill:'none',line:{fill:'none',width:0}});
    label.text=caption.join('\n');
    label.text.style={typeface:'Aptos',fontSize:20,color:'#434B59',autoFit:'shrinkText'};
  }
}
// Reflow recommendations into a readable sequence of five evenly spaced lines.
{
  const i=10;
  const layout=JSON.parse(await fs.readFile('C:/Users/brett/inzbc/.codex-presentation-build/inzbc/slides/slide-011.layout.json','utf8'));
  const paragraphs=layout.elements.find(e=>e.aid===ids[i].body).text.split('\n').filter(Boolean);
  deck.resolve(ids[i].body).text='';
  paragraphs.forEach((text,j)=>{
    const line=deck.slides.getItem(i).shapes.add({geometry:'textbox',name:`recommendation-${j+1}`,position:{left:72,top:205+j*86,width:1080,height:78},fill:'none',line:{fill:'none',width:0}});
    line.text=text;
    line.text.style={typeface:'Aptos',fontSize:26,color:j===0?'#285CFF':'#232A35',bold:j===0,autoFit:'shrinkText'};
  });
}
// Editorial split layouts: a large headline anchors the explanation alongside it.
for (const i of [1,8,11]) {
  const title=deck.resolve(ids[i].title);
  title.position={left:72,top:160,width:390,height:390};
  title.text.style={typeface:'Aptos Display',fontSize:i===11?66:62,bold:true,color:darkSlides.has(i)?'#F7F8FC':'#232A35',autoFit:'shrinkText',wrap:'square'};
  const body=deck.resolve(ids[i].body);
  body.position={left:520,top:170,width:660,height:490};
  body.text.style={typeface:'Aptos',fontSize:24,color:darkSlides.has(i)?'#DCE1ED':'#232A35',autoFit:'shrinkText',wrap:'square'};
}
await (await PresentationFile.exportPptx(deck)).save(candidate);

const zip = await JSZip.loadAsync(await fs.readFile(candidate));
const morph = '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main"><mc:Choice Requires="p159"><p:transition spd="slow" p14:dur="900"><p159:morph option="byObject"/></p:transition></mc:Choice><mc:Fallback><p:transition spd="slow"><p:fade/></p:transition></mc:Fallback></mc:AlternateContent>';
const templateXml=await fs.readFile('C:/Users/brett/inzbc/.codex-presentation-build/template-xml/ppt/slides/slide2.xml','utf8');
const scene=[...templateXml.matchAll(/<p:sp>[\s\S]*?<\/p:sp>/g)].map(m=>m[0]);
function actor(name,id,x,y,w,h) {
  let s=scene.find(s=>s.includes(`name="${name}"`));
  s=s.replace(/<p:cNvPr id="\d+"/,`<p:cNvPr id="${id}"`);
  return s.replace(/<a:off x="[^"]+" y="[^"]+"\s*\/>/,`<a:off x="${Math.round(x*9525)}" y="${Math.round(y*9525)}"/>`).replace(/<a:ext cx="[^"]+" cy="[^"]+"\s*\/>/,`<a:ext cx="${Math.round(w*9525)}" cy="${Math.round(h*9525)}"/>`);
}
for (let n = 1; n <= 12; n += 1) {
  const name = `ppt/slides/slide${n}.xml`;
  const entry = zip.file(name);
  if (!entry) throw new Error(`Missing ${name}`);
  let xml = await entry.async("string");
  xml = xml.replace(/<mc:AlternateContent[^>]*>[\s\S]*?<p159:morph[\s\S]*?<\/mc:AlternateContent>/g, "");
  if (!xml.includes("</p:spTree>")) throw new Error(`No spTree in ${name}`);
  const hero=n===1;
  const art=actor('!!scene-blue',101,hero?900:1160,hero?190:65,hero?290:60,hero?290:60)+actor('!!scene-coral',102,hero?1040:1140,hero?420:600,hero?130:45,hero?130:45)+actor('!!scene-progress',103,72,695,1130*n/12,4);
  xml=xml.replace(/(<p:spTree>[\s\S]*?<\/p:grpSpPr>)/,`$1${art}`);
  // Transition belongs to the slide root, after cSld, not inside cSld.
  if(n>1) xml=xml.replace('</p:cSld>',`</p:cSld>${morph}`);
  zip.file(name, xml);
}
await fs.writeFile(output, await zip.generateAsync({ type:"nodebuffer", compression:"DEFLATE" }));

const checked = await PresentationFile.importPptx(await FileBlob.load(output));
if (checked.slides.items.length !== 12) throw new Error("Output slide count changed");
const montage = await checked.export({ format:"webp", montage:true, scale:0.5 });
await fs.writeFile(path.join(buildDir, "montage.webp"), new Uint8Array(await montage.arrayBuffer()));
for (let i = 0; i < 12; i += 1) {
  const png = await checked.slides.getItem(i).export({ format:"png", scale:1 });
  await fs.writeFile(path.join(buildDir, `slide-${String(i+1).padStart(3,"0")}.png`), new Uint8Array(await png.arrayBuffer()));
}
const snapshot = await checked.inspect({ kind:"deck,slide,textbox,image,notes,layout", include:"id,slide,name,text,textPreview,textChars,bbox", maxChars:500000 });
await fs.writeFile(path.join(buildDir, "inspect.ndjson"), snapshot.ndjson, "utf8");
process.stdout.write(`${output}\n`);
