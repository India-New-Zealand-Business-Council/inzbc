import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const SKILL_DIR = "C:/Users/brett/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations";
const workspaceDir = "C:/Users/brett/inzbc";
const stagingDir = path.join(workspaceDir, ".codex-presentation-build", "finalizer");
const candidatePath = path.join(workspaceDir, ".codex-presentation-build", "v04-draft", "INZBC_v04.pptx");
const finalPath = path.join(workspaceDir, ".codex-presentation-output", "INZBC_v04_Editorial_Morph.pptx");
const RUNTIME_PYTHON = "C:/Users/brett/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
process.env.RUNTIME_NODE_MODULES = "C:/Users/brett/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules";
process.env.RUNTIME_NODE = "C:/Users/brett/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe";
await fs.mkdir(stagingDir, { recursive: true });
const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
const result = await finalizePresentation({
  explicitTotalSlideCount: 12,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12193200,6858000", "--validate-bullet-geometry", "--validate-heading-fit"],
  fontPolicy: {
    basis: "reference",
    families: ["Aptos", "Aptos Display"],
    referencePath: "C:/Users/brett/Downloads/Ultimate_Morph_Presentation_Template.pptx",
    referenceSha256: "a1a74e092015a82d5f0a5dbca27b122baa47f9898634b7b3f21330986cfc4a25",
  },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "INZBC_v04.validation.json"),
});
process.stdout.write(JSON.stringify(result, null, 2) + "\n");
