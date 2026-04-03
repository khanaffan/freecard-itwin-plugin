#!/usr/bin/env node
/**
 * CLI tool for converting .fcitwin bundles to iModel element data.
 *
 * Usage: node dist/cli.js --input <path.fcitwin> --output <path.json>
 */
import { FreeCADConnector } from "./connector";
import * as fs from "fs";
import * as path from "path";

function main(): void {
  const args = process.argv.slice(2);
  let inputPath: string | undefined;
  let outputPath: string | undefined;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--input" && i + 1 < args.length) {
      inputPath = args[++i];
    } else if (args[i] === "--output" && i + 1 < args.length) {
      outputPath = args[++i];
    }
  }

  if (!inputPath) {
    console.error("Usage: freecad-itwin-connector --input <path.fcitwin> --output <path.json>");
    process.exit(1);
  }

  if (!fs.existsSync(inputPath)) {
    console.error(`Input file not found: ${inputPath}`);
    process.exit(1);
  }

  if (!outputPath) {
    outputPath = inputPath.replace(/\.fcitwin$/, "") + ".elements.json";
  }

  console.log(`Reading bundle: ${inputPath}`);
  const connector = new FreeCADConnector(inputPath);
  const elements = connector.processAll();
  console.log(`Processed ${elements.length} elements from ${connector.manifest.source.fileName}`);

  // Serialize elements (convert Buffers to base64 for JSON output)
  const serializable = elements.map((el) => ({
    ...el,
    brepData: el.brepData ? el.brepData.toString("base64") : undefined,
  }));

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(serializable, null, 2));
  console.log(`Wrote ${elements.length} elements to: ${outputPath}`);
}

main();
