import { BundleReader } from "./bundle-reader";
import type {
  Manifest,
  ObjectEntry,
  GuiStateEntry,
  ParametricFeature,
  SketchData,
  DrawingData,
} from "./types";
import * as zlib from "zlib";

/**
 * Parsed OBJ mesh data ready for iModel geometry insertion.
 */
export interface ParsedMesh {
  vertices: [number, number, number][];
  faces: [number, number, number][];
}

/**
 * Represents an element to be inserted into the iModel.
 */
export interface IModelElement {
  /** FreeCAD object UUID — used as federation GUID */
  sourceId: string;
  name: string;
  typeId: string;
  parentSourceId?: string;
  mesh?: ParsedMesh;
  brepData?: Buffer;
  guiStyle?: GuiStateEntry;
  parametricFeatures?: ParametricFeature[];
  sketchData?: SketchData;
  drawingData?: DrawingData;
  drawingSvg?: string;
}

/**
 * FreeCAD Connector — maps .fcitwin bundles to iModel elements.
 *
 * This connector reads .fcitwin bundles and produces a structured
 * representation of iModel elements with all their aspects (BREP,
 * GUI style, parametric definitions, sketches, drawings).
 *
 * In a full iTwin.js integration, this would extend BaseConnector
 * from @itwin/imodel-bridge. This implementation provides the
 * data mapping layer independent of the iTwin.js SDK.
 */
export class FreeCADConnector {
  private reader: BundleReader;
  private guiStateMap: Map<string, GuiStateEntry> = new Map();

  constructor(bundlePath: string) {
    this.reader = new BundleReader(bundlePath);
  }

  get manifest(): Manifest {
    return this.reader.manifest;
  }

  /**
   * Process the bundle and return all elements for iModel insertion.
   */
  processAll(): IModelElement[] {
    // Load GUI state into lookup map
    const guiState = this.reader.readGuiState();
    for (const gs of guiState) {
      this.guiStateMap.set(gs.objectId, gs);
    }

    // Load parametric tree
    const parametricTree = this.reader.readParametricTree();
    const featuresByName = new Map<string, ParametricFeature[]>();
    if (parametricTree) {
      for (const feature of parametricTree) {
        const deps = feature.dependsOn || [];
        // Group features by their parent object if naming convention is used
        const existing = featuresByName.get(feature.name) || [];
        existing.push(feature);
        featuresByName.set(feature.name, existing);
      }
    }

    const elements: IModelElement[] = [];

    for (const obj of this.reader.manifest.objects) {
      const element = this.processObject(obj, featuresByName);
      elements.push(element);
    }

    return elements;
  }

  /**
   * Process a single FreeCAD object into an iModel element.
   */
  private processObject(
    obj: ObjectEntry,
    featuresByName: Map<string, ParametricFeature[]>
  ): IModelElement {
    const element: IModelElement = {
      sourceId: obj.id,
      name: obj.name,
      typeId: obj.type,
      parentSourceId: obj.parentId,
    };

    // Read tessellated mesh for visualization
    if (obj.meshFile) {
      const objData = this.reader.readMesh(obj.meshFile);
      if (objData) {
        element.mesh = this.parseObj(objData);
      }
    }

    // Read BREP for round-trip reconstruction
    if (obj.shapeFile) {
      const brepData = this.reader.readBrep(obj.shapeFile);
      if (brepData) {
        element.brepData = zlib.deflateSync(brepData);
      }
    }

    // Attach GUI style
    const gs = this.guiStateMap.get(obj.id);
    if (gs) {
      element.guiStyle = gs;
    }

    // Attach sketch data
    if (obj.sketchFile) {
      element.sketchData = this.reader.readSketch(obj.sketchFile) ?? undefined;
    }

    // Attach drawing data
    if (obj.drawingFile) {
      element.drawingData = this.reader.readDrawing(obj.drawingFile) ?? undefined;
      // Try to load SVG
      const drawingName = obj.drawingFile
        .replace("drawings/", "")
        .replace(".json", "");
      element.drawingSvg = this.reader.readDrawingSvg(drawingName) ?? undefined;
    }

    // Attach parametric features
    const features = featuresByName.get(obj.name);
    if (features) {
      element.parametricFeatures = features;
    }

    return element;
  }

  /**
   * Parse OBJ mesh data into vertices and faces.
   */
  private parseObj(objData: string): ParsedMesh {
    const vertices: [number, number, number][] = [];
    const faces: [number, number, number][] = [];

    for (const line of objData.split("\n")) {
      const trimmed = line.trim();
      if (trimmed.startsWith("v ")) {
        const parts = trimmed.split(/\s+/);
        vertices.push([
          parseFloat(parts[1]),
          parseFloat(parts[2]),
          parseFloat(parts[3]),
        ]);
      } else if (trimmed.startsWith("f ")) {
        const parts = trimmed.split(/\s+/);
        // OBJ faces are 1-indexed; convert to 0-indexed
        faces.push([
          parseInt(parts[1]) - 1,
          parseInt(parts[2]) - 1,
          parseInt(parts[3]) - 1,
        ]);
      }
    }

    return { vertices, faces };
  }

  /**
   * Get provenance mapping data for incremental sync.
   * Maps FreeCAD UUIDs to a deterministic key for element lookup.
   */
  getProvenanceMap(): Map<string, string> {
    const map = new Map<string, string>();
    for (const obj of this.reader.manifest.objects) {
      // The sourceId (FreeCAD UUID) serves as the federation GUID
      map.set(obj.id, `${this.manifest.source.fileName}:${obj.name}`);
    }
    return map;
  }
}
