import AdmZip from "adm-zip";
import type {
  Manifest,
  GuiStateEntry,
  ParametricFeature,
  SketchData,
  DrawingData,
} from "./types";

/**
 * Reads a .fcitwin ZIP bundle and provides access to its contents.
 */
export class BundleReader {
  private zip: AdmZip;
  public readonly manifest: Manifest;

  constructor(bundlePath: string) {
    this.zip = new AdmZip(bundlePath);
    const manifestEntry = this.zip.getEntry("manifest.json");
    if (!manifestEntry) {
      throw new Error(`Invalid .fcitwin bundle: missing manifest.json`);
    }
    this.manifest = JSON.parse(manifestEntry.getData().toString("utf-8"));
  }

  /** Read GUI state entries */
  readGuiState(): GuiStateEntry[] {
    const entry = this.zip.getEntry("gui-state.json");
    if (!entry) return [];
    return JSON.parse(entry.getData().toString("utf-8"));
  }

  /** Read raw BREP data for an object */
  readBrep(shapePath: string): Buffer | null {
    const entry = this.zip.getEntry(shapePath);
    return entry ? entry.getData() : null;
  }

  /** Read tessellated mesh (OBJ format) for an object */
  readMesh(meshPath: string): string | null {
    const entry = this.zip.getEntry(meshPath);
    return entry ? entry.getData().toString("utf-8") : null;
  }

  /** Read the parametric feature tree */
  readParametricTree(): ParametricFeature[] | null {
    if (!this.manifest.parametricTreeFile) return null;
    const entry = this.zip.getEntry(this.manifest.parametricTreeFile);
    if (!entry) return null;
    const data = JSON.parse(entry.getData().toString("utf-8"));
    return data.features || data;
  }

  /** Read sketch data */
  readSketch(sketchPath: string): SketchData | null {
    const entry = this.zip.getEntry(sketchPath);
    if (!entry) return null;
    return JSON.parse(entry.getData().toString("utf-8"));
  }

  /** Read drawing data */
  readDrawing(drawingPath: string): DrawingData | null {
    const entry = this.zip.getEntry(drawingPath);
    if (!entry) return null;
    return JSON.parse(entry.getData().toString("utf-8"));
  }

  /** Read drawing SVG */
  readDrawingSvg(name: string): string | null {
    const entry = this.zip.getEntry(`drawings/${name}.svg`);
    return entry ? entry.getData().toString("utf-8") : null;
  }

  /** Read any file as a buffer */
  readFile(path: string): Buffer | null {
    const entry = this.zip.getEntry(path);
    return entry ? entry.getData() : null;
  }

  /** Read any JSON file */
  readJson<T = unknown>(path: string): T | null {
    const buf = this.readFile(path);
    return buf ? JSON.parse(buf.toString("utf-8")) : null;
  }

  /** List all files in the bundle */
  listFiles(): string[] {
    return this.zip.getEntries().map((e) => e.entryName);
  }
}
