import fs from "node:fs/promises";
import path from "node:path";
import JSZip from "jszip";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const input = "C:/Users/brett/inzbc/.codex-presentation-output/INZBC_Final_Presentation_Morph_Improved_Final.pptx";
const out = "C:/Users/brett/inzbc/.codex-presentation-build/final-render";
await fs.mkdir(out, { recursive:true });
const deck = await PresentationFile.importPptx(await FileBlob.load(input));
if (deck.slides.items.length !== 12) throw new Error("Expected 12 slides");
const montage = await deck.export({ format:"webp", montage:true, scale:0.5 });
await fs.writeFile(path.join(out, "montage.webp"), new Uint8Array(await montage.arrayBuffer()));
for (let i=0;i<12;i++) {
  const png = await deck.slides.getItem(i).export({ format:"png", scale:1 });
  await fs.writeFile(path.join(out, `slide-${String(i+1).padStart(3,"0")}.png`), new Uint8Array(await png.arrayBuffer()));
}
const zip = await JSZip.loadAsync(await fs.readFile(input));
let morphCount=0;
for (let n=2;n<=12;n++) {
  const xml = await zip.file(`ppt/slides/slide${n}.xml`).async("string");
  if (xml.includes("<p159:morph option=\"byObject\"/>")) morphCount++;
}
const notes = Object.keys(zip.files).filter(n => /^ppt\/notesSlides\/notesSlide\d+\.xml$/.test(n)).length;
if (morphCount !== 11 || notes !== 12) throw new Error(`morph=${morphCount}, notes=${notes}`);
process.stdout.write(`slides=12 morph=${morphCount} notes=${notes}\n`);
