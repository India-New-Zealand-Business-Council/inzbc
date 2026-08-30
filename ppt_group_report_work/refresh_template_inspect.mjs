import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "C:\\Users\\brett\\Downloads\\Morph-Motion-Template-20-Slides.pptx";
const output = "C:\\Users\\brett\\inzbc\\ppt_group_report_work\\template-inspect\\template-inspect.ndjson";
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const inspected = await presentation.inspect({
  kind: "slide,textbox,shape,image,table,chart",
  maxChars: 1000000,
});
await fs.writeFile(output, inspected.ndjson || "", "utf8");
console.log(JSON.stringify({ output, truncated: Boolean(inspected.truncated), characters: (inspected.ndjson || "").length }));
