import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const buildDir = "C:/Users/brett/inzbc/.codex-presentation-build";
const decks = [
  {
    name: "template",
    source: "C:/Users/brett/Downloads/Ultimate_Morph_Presentation_Template.pptx",
  },
  {
    name: "inzbc",
    source: "C:/Users/brett/Downloads/New folder/FINAL/INZBC_Final_Presentation.pptx",
  },
];

for (const deck of decks) {
  const presentation = await PresentationFile.importPptx(await FileBlob.load(deck.source));
  const outDir = path.join(buildDir, deck.name);
  await fs.mkdir(path.join(outDir, "slides"), { recursive: true });

  const snapshot = await presentation.inspect({
    kind: "deck,slide,textbox,shape,image,table,chart,notes,layout",
    include: "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit,rows,cols,chartType,alt,isPlaceholder,placeholders",
    maxChars: 500000,
  });
  await fs.writeFile(path.join(outDir, "inspect.ndjson"), snapshot.ndjson, "utf8");

  const summary = {
    source: deck.source,
    slideCount: presentation.slides.items.length,
    slideSize: presentation.slideSize,
    masters: presentation.masters.items.map((master) => ({
      id: master.id,
      name: master.name,
      placeholderSummary: master.placeholders?.summary?.() ?? null,
    })),
    layouts: presentation.layouts.items.map((layout) => ({
      id: layout.id,
      name: layout.name,
      placeholderSummary: layout.placeholders?.summary?.() ?? null,
    })),
  };
  await fs.writeFile(path.join(outDir, "summary.json"), JSON.stringify(summary, null, 2), "utf8");

  const montage = await presentation.export({ format: "webp", montage: true, scale: 0.5 });
  await fs.writeFile(path.join(outDir, "montage.webp"), new Uint8Array(await montage.arrayBuffer()));

  for (let i = 0; i < presentation.slides.items.length; i += 1) {
    const slide = presentation.slides.getItem(i);
    const preview = await slide.export({ format: "png", scale: 1 });
    await fs.writeFile(
      path.join(outDir, "slides", `slide-${String(i + 1).padStart(3, "0")}.png`),
      new Uint8Array(await preview.arrayBuffer()),
    );
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(
      path.join(outDir, "slides", `slide-${String(i + 1).padStart(3, "0")}.layout.json`),
      await layout.text(),
      "utf8",
    );
  }
  process.stdout.write(`${deck.name}: ${summary.slideCount} slides\n`);
}
