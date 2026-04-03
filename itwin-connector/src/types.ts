/** Manifest for a .fcitwin bundle */
export interface Manifest {
  version: string;
  generator: string;
  source: {
    fileName: string;
    fileHash: string;
    freecadVersion: string;
  };
  objects: ObjectEntry[];
  parametricTreeFile?: string;
}

/** An object entry in the manifest */
export interface ObjectEntry {
  id: string;
  name: string;
  type: string;
  parentId?: string;
  shapeFile?: string;
  meshFile?: string;
  sketchFile?: string;
  drawingFile?: string;
}

/** Visual properties for a single object */
export interface GuiStateEntry {
  objectId: string;
  shapeColor?: string;
  lineColor?: string;
  lineWidth?: number;
  transparency?: number;
  visibility: boolean;
  displayMode?: string;
}

/** A parametric feature in the feature tree */
export interface ParametricFeature {
  name: string;
  type: string;
  index: number;
  parameters: Record<string, unknown>;
  dependsOn: string[];
}

/** Sketch geometry and constraints */
export interface SketchData {
  geometry: SketchGeometry[];
  constraints: SketchConstraint[];
  plane: {
    origin: [number, number, number];
    normal: [number, number, number];
  };
}

export interface SketchGeometry {
  id: number;
  type: string; // "Line", "Arc", "Circle", "BSpline", "Point"
  data: Record<string, unknown>;
}

export interface SketchConstraint {
  type: string; // "Coincident", "Tangent", "Parallel", "Distance", etc.
  geometryRefs: number[];
  value?: number;
  name?: string;
}

/** TechDraw page data */
export interface DrawingData {
  pageName: string;
  template: string;
  scale: number;
  views: DrawingView[];
  dimensions: DrawingDimension[];
  annotations: DrawingAnnotation[];
}

export interface DrawingView {
  name: string;
  type: string;
  sourceObject: string;
  direction: [number, number, number];
  position: [number, number];
  scale: number;
}

export interface DrawingDimension {
  type: string; // "DistanceX", "DistanceY", "Distance", "Angle", "Radius"
  references: string[];
  value: number;
  position: [number, number];
  formatSpec?: string;
}

export interface DrawingAnnotation {
  type: string; // "Text", "Balloon", "Leader"
  text: string;
  position: [number, number];
}
