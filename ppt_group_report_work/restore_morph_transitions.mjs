import fs from "node:fs";
import JSZip from "jszip";

const sourcePath = "C:\\Users\\brett\\Downloads\\Morph-Motion-Template-20-Slides.pptx";
const targetPath = process.argv[2] ?? "C:\\Users\\brett\\inzbc\\INZBC_Group_Final_Report_Morph.pptx";
const temporaryPath = `${targetPath}.transition-patch.tmp`;

function transitionAlternateContent(xml, slideNumber) {
  const blocks = xml.match(/<mc:AlternateContent\b[\s\S]*?<\/mc:AlternateContent>/g) ?? [];
  const block = blocks.find((candidate) => candidate.includes("<p:transition"));
  if (!block) {
    throw new Error(`Slide ${slideNumber}: transition AlternateContent was not found in the template.`);
  }
  return block;
}

function timingBlock(xml) {
  return xml.match(/<p:timing>[\s\S]*?<\/p:timing>/)?.[0] ?? "";
}

function removeTransitionAndTiming(xml) {
  const withoutTransition = xml.replace(
    /<mc:AlternateContent\b[\s\S]*?<p:transition[\s\S]*?<\/mc:AlternateContent>/g,
    "",
  );
  return withoutTransition.replace(/<p:timing>[\s\S]*?<\/p:timing>/g, "");
}

const sourceZip = await JSZip.loadAsync(fs.readFileSync(sourcePath));
const targetZip = await JSZip.loadAsync(fs.readFileSync(targetPath));

for (let slideNumber = 1; slideNumber <= 20; slideNumber += 1) {
  const slidePath = `ppt/slides/slide${slideNumber}.xml`;
  const sourceXml = await sourceZip.file(slidePath)?.async("string");
  const targetXml = await targetZip.file(slidePath)?.async("string");
  if (!sourceXml || !targetXml) {
    throw new Error(`Slide ${slideNumber}: source or target XML is missing.`);
  }

  const transition = transitionAlternateContent(sourceXml, slideNumber);
  const timing = timingBlock(sourceXml);
  const cleanTargetXml = removeTransitionAndTiming(targetXml);
  const patchedTargetXml = cleanTargetXml.replace(
    "</p:sld>",
    `${transition}${timing}</p:sld>`,
  );
  targetZip.file(slidePath, patchedTargetXml);
}

const themePaths = Object.keys(sourceZip.files).filter((path) =>
  /^ppt\/theme\/theme\d+\.xml$/.test(path),
);
for (const themePath of themePaths) {
  const themeBytes = await sourceZip.file(themePath)?.async("nodebuffer");
  if (!themeBytes) {
    throw new Error(`Theme part is missing: ${themePath}`);
  }
  targetZip.file(themePath, themeBytes);
}

const output = await targetZip.generateAsync({
  type: "nodebuffer",
  compression: "DEFLATE",
  compressionOptions: { level: 6 },
});

const verificationZip = await JSZip.loadAsync(output);
let morphCount = 0;
let fadeOnlyCount = 0;
let timingCount = 0;

for (let slideNumber = 1; slideNumber <= 20; slideNumber += 1) {
  const xml = await verificationZip
    .file(`ppt/slides/slide${slideNumber}.xml`)
    ?.async("string");
  if (!xml) {
    throw new Error(`Slide ${slideNumber}: verification XML is missing.`);
  }
  if (xml.includes("<p159:morph")) morphCount += 1;
  else if (xml.includes("<p:fade")) fadeOnlyCount += 1;
  if (xml.includes("<p:timing>")) timingCount += 1;
}

if (morphCount !== 19 || fadeOnlyCount !== 1 || timingCount !== 2) {
  throw new Error(
    `Transition verification failed: morph=${morphCount}, fadeOnly=${fadeOnlyCount}, timing=${timingCount}.`,
  );
}

fs.writeFileSync(temporaryPath, output);
fs.copyFileSync(temporaryPath, targetPath);
fs.unlinkSync(temporaryPath);

process.stdout.write(
  JSON.stringify(
    {
      targetPath,
      slides: 20,
      morphCount,
      fadeOnlyCount,
      timingCount,
      themeFilesRestored: themePaths.length,
    },
    null,
    2,
  ),
);
